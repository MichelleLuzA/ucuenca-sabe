"""
io_utils.py
===========
Utilidades transversales para el pipeline ENEMDU (arquitectura medallón).

Responsabilidad única: resolución de rutas del proyecto y lectura robusta de
archivos heterogéneos (CSV del INEC con separador/encoding variable, XLSX de
diccionarios). Es la única capa que toca el sistema de archivos "en crudo",
de modo que el resto de módulos (analyzer / silver / gold) no repita lógica.

Autor: pipeline UCUENCA-SABE
"""
from __future__ import annotations

import csv
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Devuelve un logger con formato homogéneo (idempotente)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                              datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Rutas del proyecto
# --------------------------------------------------------------------------- #
_ROOT_MARKERS = ("src", "config", ".git", "pyproject.toml", "requirements.txt")


def find_project_root(start: Optional[Path] = None) -> Path:
    """Sube por el árbol de directorios hasta encontrar la raíz del proyecto.

    Se apoya en marcadores conocidos (src/, config/, .git). Si no encuentra
    nada, devuelve el directorio actual (comportamiento seguro en notebooks).
    """
    start = Path(start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        hits = sum((candidate / m).exists() for m in _ROOT_MARKERS)
        if hits >= 2:
            return candidate
    return start.parent if start.name == "notebooks" else start


@dataclass
class ENEMDUPaths:
    """Contenedor central de rutas de la fuente ENEMDU.

    Intenta primero leer `src.config.CONFIG` (fuente de verdad del proyecto) y
    sólo si no está disponible cae a la convención de carpetas del repositorio.
    """

    root: Path
    bronze: Path
    diccionarios: Path
    microdatos: Path
    silver: Path
    gold: Path
    reports: Path

    @classmethod
    def build(cls, root: Optional[Path] = None) -> "ENEMDUPaths":
        root = Path(root) if root else find_project_root()
        bronze = None

        # 1) Intento de integración con el módulo central de configuración
        try:  # pragma: no cover - depende del entorno del proyecto
            import sys

            if str(root) not in sys.path:
                sys.path.append(str(root))
            from src.config import CONFIG  # type: ignore

            src_cfg = (CONFIG.get("sources", {}) or {}).get("enemdu", {}) or {}
            raw = src_cfg.get("bronze_dir") or src_cfg.get("path") or src_cfg.get("dir")
            if raw:
                bronze = Path(raw)
                if not bronze.is_absolute():
                    bronze = root / bronze
        except Exception as exc:  # noqa: BLE001
            log.debug("No se pudo leer src.config (%s); usando convención de rutas.", exc)

        if bronze is None:
            bronze = root / "data" / "bronze" / "externas" / "enemdu"

        return cls(
            root=root,
            bronze=bronze,
            diccionarios=bronze / "diccionarios",
            microdatos=bronze / "microdatos_csv",
            silver=root / "data" / "silver" / "enemdu",
            gold=root / "data" / "gold" / "enemdu",
            reports=root / "reports",
        )

    def ensure(self) -> "ENEMDUPaths":
        """Crea las carpetas de salida si no existen."""
        for p in (self.silver, self.gold, self.reports / "schemas", self.reports / "powerbi"):
            p.mkdir(parents=True, exist_ok=True)
        return self

    def as_dict(self) -> Dict[str, str]:
        return {k: str(v) for k, v in self.__dict__.items()}


# --------------------------------------------------------------------------- #
# Normalización de nombres
# --------------------------------------------------------------------------- #
def normalize_name(value: Any) -> str:
    """Normaliza un nombre de columna: sin tildes, minúsculas, snake_case."""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def year_from_filename(path: Path) -> Optional[int]:
    """Extrae un año 19xx/20xx del nombre del archivo."""
    matches = re.findall(r"(19|20)\d{2}", path.stem)
    if not matches:
        return None
    return int(re.findall(r"(?:19|20)\d{2}", path.stem)[-1])


# --------------------------------------------------------------------------- #
# Lectura robusta de CSV
# --------------------------------------------------------------------------- #
ENCODINGS: Tuple[str, ...] = ("utf-8", "utf-8-sig", "latin-1", "cp1252")
SEPARATORS: Tuple[str, ...] = (";", ",", "\t", "|")


def sniff_csv(path: Path, sample_bytes: int = 64_000) -> Dict[str, Any]:
    """Detecta encoding, separador y decimal de un CSV.

    Los microdatos del INEC alternan entre `;`/`,` y entre UTF-8/Latin-1 según
    el año de publicación, por lo que la detección debe ser automática.
    """
    raw = Path(path).open("rb").read(sample_bytes)

    encoding = "latin-1"
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
            encoding = enc
            break
        except UnicodeDecodeError:
            continue

    sample = raw.decode(encoding, errors="replace")
    first_line = sample.splitlines()[0] if sample.splitlines() else ""

    try:
        sep = csv.Sniffer().sniff(sample, delimiters="".join(SEPARATORS)).delimiter
    except csv.Error:
        sep = max(SEPARATORS, key=first_line.count)
    if first_line.count(sep) == 0:
        sep = max(SEPARATORS, key=first_line.count)

    # Decimal: si hay patrones numéricos con coma y el separador no es coma
    body = "\n".join(sample.splitlines()[1:6])
    decimal = "," if sep != "," and re.search(r"\d,\d", body) else "."

    return {"encoding": encoding, "sep": sep, "decimal": decimal,
            "n_cols_header": first_line.count(sep) + 1}


def read_csv_smart(path: Path, nrows: Optional[int] = None,
                   usecols: Optional[Sequence[str]] = None,
                   dtype: Any = None, **kwargs) -> pd.DataFrame:
    """Lee un CSV detectando dialecto automáticamente y normalizando cabeceras."""
    meta = sniff_csv(path)
    df = pd.read_csv(
        path,
        sep=meta["sep"],
        encoding=meta["encoding"],
        decimal=meta["decimal"],
        nrows=nrows,
        usecols=usecols,
        dtype=dtype,
        low_memory=False,
        on_bad_lines="warn",
        **kwargs,
    )
    df.columns = [normalize_name(c) for c in df.columns]
    return df


def read_csv_header(path: Path) -> List[str]:
    """Lee sólo la cabecera de un CSV (barato, sin cargar datos)."""
    return list(read_csv_smart(path, nrows=0).columns)


def count_csv_rows(path: Path) -> int:
    """Cuenta filas de datos sin cargar el archivo en memoria."""
    meta = sniff_csv(path)
    with Path(path).open("r", encoding=meta["encoding"], errors="replace") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


# --------------------------------------------------------------------------- #
# Lectura de diccionarios XLSX
# --------------------------------------------------------------------------- #
_VAR_HINTS = ("variable", "nombre", "campo", "codigo_variable", "nemonico", "nemonico_variable")
_DESC_HINTS = ("descripcion", "etiqueta", "detalle", "nombre_variable", "concepto", "pregunta")
_VAL_HINTS = ("valor", "valores", "categoria", "categorias", "opciones", "codigos", "respuesta")


def read_dictionary_xlsx(path: Path, max_header_scan: int = 15) -> pd.DataFrame:
    """Lee un diccionario XLSX del INEC detectando la fila de cabecera.

    Devuelve un DataFrame con columnas canónicas: `variable`, `descripcion`,
    `valores` (las que existan). El formato de los diccionarios cambia entre
    años, por eso se busca la cabecera heurísticamente en las primeras filas.
    """
    frames: List[pd.DataFrame] = []
    xls = pd.ExcelFile(path)

    for sheet in xls.sheet_names:
        probe = xls.parse(sheet, header=None, nrows=max_header_scan + 5, dtype=str)
        if probe.empty:
            continue

        header_row = None
        for i in range(min(max_header_scan, len(probe))):
            cells = [normalize_name(c) for c in probe.iloc[i].tolist() if pd.notna(c)]
            if any(any(h == c or h in c for h in _VAR_HINTS) for c in cells) and len(cells) >= 2:
                header_row = i
                break
        if header_row is None:
            continue

        df = xls.parse(sheet, header=header_row, dtype=str)
        df.columns = [normalize_name(c) for c in df.columns]
        df = df.dropna(how="all")

        def _pick(hints: Iterable[str]) -> Optional[str]:
            for col in df.columns:
                if any(h == col or h in col for h in hints):
                    return col
            return None

        col_var, col_desc, col_val = _pick(_VAR_HINTS), _pick(_DESC_HINTS), _pick(_VAL_HINTS)
        if col_var is None:
            continue

        out = pd.DataFrame({"variable": df[col_var].map(
            lambda v: normalize_name(v) if pd.notna(v) else None)})
        out["descripcion"] = df[col_desc].astype(str).str.strip() if col_desc else None
        out["valores"] = df[col_val].astype(str).str.strip() if col_val else None
        out["hoja"] = sheet
        out = out[out["variable"].notna() & (out["variable"] != "") & (out["variable"] != "nan")]
        frames.append(out)

    if not frames:
        log.warning("No se pudo interpretar el diccionario: %s", path.name)
        return pd.DataFrame(columns=["variable", "descripcion", "valores", "hoja"])

    result = pd.concat(frames, ignore_index=True)
    return result.drop_duplicates(subset=["variable"], keep="first").reset_index(drop=True)


_LABEL_RE = re.compile(r"(?P<code>-?\d+)\s*[=:\-\.\)]\s*(?P<label>[^;|\n\r,]+)")


def parse_value_labels(text: Any) -> Dict[str, str]:
    """Extrae pares código→etiqueta de una celda del diccionario.

    Soporta formatos '1=Hombre; 2=Mujer', '1 - Urbano', '1) Sí', multilínea.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return {}
    labels: Dict[str, str] = {}
    for match in _LABEL_RE.finditer(str(text)):
        code = str(int(match.group("code")))
        label = re.sub(r"\s+", " ", match.group("label")).strip(" .;:-")
        if label and code not in labels:
            labels[code] = label
    return labels


# --------------------------------------------------------------------------- #
# Persistencia de reportes
# --------------------------------------------------------------------------- #
def save_json(obj: Any, path: Path) -> Path:
    """Guarda un objeto como JSON legible (UTF-8, tipos numpy convertidos)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def _default(o: Any):
        if hasattr(o, "item"):
            return o.item()
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        if isinstance(o, Path):
            return str(o)
        return str(o)

    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_default),
                    encoding="utf-8")
    return path
