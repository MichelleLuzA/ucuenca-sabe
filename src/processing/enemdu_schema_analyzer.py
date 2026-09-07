"""
enemdu_schema_analyzer.py
=========================
Objetivo 1 del pipeline: **auditar y analizar los esquemas** de ENEMDU
(2021-2025) antes de construir la capa Silver.

Qué hace
--------
1. Inventaría la capa Bronze (CSV de microdatos + XLSX de diccionarios).
2. Lee automáticamente los diccionarios y extrae variables, descripciones y
   etiquetas de valores (código → significado).
3. Compara el esquema declarado (diccionario) contra el esquema real (CSV).
4. Detecta columnas comunes a todos los años vs. específicas por año.
5. Audita calidad básica sobre una muestra: nulos, duplicados de llave,
   rangos, cardinalidades y presencia de variables críticas.
6. Exporta un reporte reproducible en `reports/schemas/schema_analysis_*.json`.

Uso
---
>>> analyzer = ENEMDUSchemaAnalyzer()
>>> schemas = analyzer.analyze_all()
>>> analyzer.common_columns
>>> analyzer.year_specific
>>> analyzer.save_report()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import pandas as pd

from .io_utils import (
    ENEMDUPaths,
    count_csv_rows,
    get_logger,
    normalize_name,
    parse_value_labels,
    read_csv_header,
    read_csv_smart,
    read_dictionary_xlsx,
    save_json,
    sniff_csv,
    year_from_filename,
)

log = get_logger(__name__)

#: Variables mínimas necesarias para el caso de uso de empleabilidad.
#: Se expresan como alias porque el INEC cambia nomenclatura entre años.
CRITICAL_ALIASES: Dict[str, List[str]] = {
    "anio": ["anio", "ano", "year", "periodo"],
    "mes": ["mes", "month"],
    "provincia": ["provincia", "prov", "codigo_provincia"],
    "ciudad": ["ciudad", "canton", "codigo_ciudad"],
    "area": ["area", "area_geografica", "dominio"],
    "sexo": ["p02", "sexo", "p2"],
    "edad": ["p03", "edad", "p3"],
    "nivel_instruccion": ["p10a", "nivel_instruccion", "nivelins", "p10a1"],
    "anios_aprobados": ["p10b", "anio_aprobado", "grado_aprobado"],
    "condicion_actividad": ["condact", "condicion_actividad", "condactn"],
    "ocupacion_ciuo": ["p41", "grupo1", "ciuo", "ocupacion", "gruocu"],
    "rama_ciiu": ["p42", "rama1", "ciiu", "rama_actividad"],
    "horas_trabajadas": ["p51a", "p24", "horas", "totalhoras", "horastrab"],
    "ingreso_laboral": ["ingrl", "ingreso_laboral", "p66", "ingreso"],
    "sector_empleo": ["secemp", "sector", "formal_informal"],
    "categoria_ocupacion": ["p42", "categ_ocup", "p41b", "categoria"],
    "factor_expansion": ["fexp", "factor_expansion", "fexp_anual", "peso"],
}


@dataclass
class YearSchema:
    """Esquema y metadatos de un año de ENEMDU."""

    year: int
    csv_path: Optional[Path] = None
    dict_path: Optional[Path] = None
    csv_columns: List[str] = field(default_factory=list)
    dict_columns: List[str] = field(default_factory=list)
    descriptions: Dict[str, str] = field(default_factory=dict)
    value_labels: Dict[str, Dict[str, str]] = field(default_factory=dict)
    dialect: Dict[str, Any] = field(default_factory=dict)
    n_rows: Optional[int] = None
    size_mb: Optional[float] = None

    # -- derivados ---------------------------------------------------------- #
    @property
    def only_in_dict(self) -> List[str]:
        """Declaradas en el diccionario pero ausentes en el CSV."""
        return sorted(set(self.dict_columns) - set(self.csv_columns))

    @property
    def only_in_csv(self) -> List[str]:
        """Presentes en el CSV pero no documentadas en el diccionario."""
        return sorted(set(self.csv_columns) - set(self.dict_columns))

    @property
    def coverage(self) -> float:
        """% de columnas del CSV documentadas en el diccionario.

        OJO: esto sólo mide si el NOMBRE de la columna está documentado, no si
        el diccionario trae las etiquetas de valor (código → significado).
        Un diccionario puede tener 100% de cobertura de nombres y 0 etiquetas
        de valor (p. ej. si sólo documenta "nombre de campo" + "descripción").
        Usa `n_variables_con_etiquetas` para lo segundo.
        """
        if not self.csv_columns:
            return 0.0
        return round(100 * len(set(self.csv_columns) & set(self.dict_columns))
                     / len(self.csv_columns), 2)

    @property
    def n_variables_con_etiquetas(self) -> int:
        """Cuántas variables tienen etiquetas código→significado extraídas."""
        return sum(1 for labels in self.value_labels.values() if labels)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "csv_path": str(self.csv_path) if self.csv_path else None,
            "dict_path": str(self.dict_path) if self.dict_path else None,
            "n_cols_csv": len(self.csv_columns),
            "n_cols_dict": len(self.dict_columns),
            "n_rows": self.n_rows,
            "size_mb": self.size_mb,
            "dialect": self.dialect,
            "cobertura_diccionario_pct": self.coverage,
            "csv_columns": self.csv_columns,
            "only_in_dict": self.only_in_dict,
            "only_in_csv": self.only_in_csv,
            "value_labels": self.value_labels,
        }


class ENEMDUSchemaAnalyzer:
    """Analiza automáticamente los esquemas de ENEMDU en la capa Bronze."""

    def __init__(
        self,
        paths: Optional[ENEMDUPaths] = None,
        years: Optional[Sequence[int]] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.paths = (paths or ENEMDUPaths.build(project_root)).ensure()
        self.years = list(years) if years else list(range(2021, 2026))
        self.schemas: Dict[int, YearSchema] = {}
        self._audit: Optional[pd.DataFrame] = None
        log.info("Bronze ENEMDU: %s", self.paths.bronze)

    # ------------------------------------------------------------------ #
    # Inventario
    # ------------------------------------------------------------------ #
    def inventory(self) -> pd.DataFrame:
        """Lista los archivos disponibles en Bronze y su año detectado."""
        rows: List[Dict[str, Any]] = []
        for kind, folder, pattern in (
            ("microdato", self.paths.microdatos, "*.csv"),
            ("diccionario", self.paths.diccionarios, "*.xls*"),
        ):
            if not folder.exists():
                log.warning("No existe la carpeta %s", folder)
                continue
            for f in sorted(folder.glob(pattern)):
                if f.name.startswith("~$"):  # temporales de Excel
                    continue
                rows.append({
                    "tipo": kind,
                    "archivo": f.name,
                    "anio": year_from_filename(f),
                    "peso_mb": round(f.stat().st_size / 1e6, 2),
                    "ruta": str(f),
                })
        df = pd.DataFrame(rows)
        if df.empty:
            log.error("Bronze vacío: ejecuta primero la ingesta desde Kaggle.")
        return df

    # ------------------------------------------------------------------ #
    # Análisis de esquemas
    # ------------------------------------------------------------------ #
    def analyze_year(self, year: int) -> YearSchema:
        """Analiza un año: cruza diccionario XLSX contra CSV real."""
        schema = YearSchema(year=year)

        csvs = [f for f in self.paths.microdatos.glob("*.csv")
                if year_from_filename(f) == year]
        if csvs:
            schema.csv_path = csvs[0]
            schema.dialect = sniff_csv(schema.csv_path)
            schema.csv_columns = read_csv_header(schema.csv_path)
            schema.size_mb = round(schema.csv_path.stat().st_size / 1e6, 2)
            try:
                schema.n_rows = count_csv_rows(schema.csv_path)
            except Exception as exc:  # noqa: BLE001
                log.warning("No se pudieron contar filas de %s: %s", schema.csv_path.name, exc)
        else:
            log.warning("Sin microdato CSV para %s", year)

        dicts = [f for f in self.paths.diccionarios.glob("*.xls*")
                 if year_from_filename(f) == year and not f.name.startswith("~$")]
        if dicts:
            schema.dict_path = dicts[0]
            try:
                ddf = read_dictionary_xlsx(schema.dict_path)
                schema.dict_columns = ddf["variable"].tolist()
                schema.descriptions = {
                    r.variable: str(r.descripcion)
                    for r in ddf.itertuples() if pd.notna(r.descripcion)
                }
                schema.value_labels = {
                    r.variable: labels
                    for r in ddf.itertuples()
                    if (labels := parse_value_labels(r.valores))
                }
            except Exception as exc:  # noqa: BLE001
                log.error("Error leyendo diccionario %s: %s", schema.dict_path.name, exc)
            else:
                if schema.dict_columns and schema.n_variables_con_etiquetas == 0:
                    log.error(
                        "Año %s: el diccionario '%s' se leyó (%s variables documentadas) pero "
                        "NINGUNA trae etiquetas de valor (código→significado) — probablemente "
                        "sólo documenta nombre + descripción de campo, no categorías. TODO el "
                        "mapeo semántico de sexo/condición de actividad/nivel de instrucción/etc. "
                        "para este año depende ciegamente de los FALLBACK_* de enemdu_mappings.py, "
                        "sin poder validarse contra un codebook real. Busca un 'Manual de usuario' "
                        "o la versión .sav/.dta del microdato (trae las etiquetas embebidas) antes "
                        "de confiar en las tasas derivadas de condicion_actividad.",
                        year, schema.dict_path.name, len(schema.dict_columns))
        else:
            log.warning("Sin diccionario XLSX para %s", year)

        self.schemas[year] = schema
        log.info("Año %s → %s cols CSV | %s cols diccionario | cobertura %.1f%%",
                 year, len(schema.csv_columns), len(schema.dict_columns), schema.coverage)
        return schema

    def analyze_all(self) -> Dict[int, YearSchema]:
        """Analiza todos los años configurados."""
        for year in self.years:
            self.analyze_year(year)
        return self.schemas

    # ------------------------------------------------------------------ #
    # Propiedades de comparación entre años
    # ------------------------------------------------------------------ #
    @property
    def _sets(self) -> Dict[int, Set[str]]:
        return {y: set(s.csv_columns) for y, s in self.schemas.items() if s.csv_columns}

    @property
    def common_columns(self) -> List[str]:
        """Columnas presentes en **todos** los años disponibles."""
        sets = self._sets
        if not sets:
            return []
        return sorted(set.intersection(*sets.values()))

    @property
    def all_columns(self) -> List[str]:
        """Unión de columnas de todos los años."""
        sets = self._sets
        return sorted(set.union(*sets.values())) if sets else []

    @property
    def year_specific(self) -> Dict[int, List[str]]:
        """Columnas exclusivas de cada año (no presentes en el resto)."""
        sets = self._sets
        out: Dict[int, List[str]] = {}
        for year, cols in sets.items():
            others = set.union(*[c for y, c in sets.items() if y != year]) if len(sets) > 1 else set()
            out[year] = sorted(cols - others)
        return out

    def presence_matrix(self) -> pd.DataFrame:
        """Matriz columna × año (True/False) para inspección visual."""
        sets = self._sets
        if not sets:
            return pd.DataFrame()
        data = {y: [c in cols for c in self.all_columns] for y, cols in sorted(sets.items())}
        df = pd.DataFrame(data, index=self.all_columns)
        df["n_anios"] = df.sum(axis=1)
        df["estado"] = df["n_anios"].map(
            lambda n: "común" if n == len(sets) else ("parcial" if n > 1 else "exclusiva"))
        return df.sort_values(["n_anios", "estado"], ascending=[False, True])

    # ------------------------------------------------------------------ #
    # Resolución de variables críticas
    # ------------------------------------------------------------------ #
    def resolve_critical(self, aliases: Optional[Dict[str, List[str]]] = None) -> pd.DataFrame:
        """Resuelve, por año, qué alias real corresponde a cada variable crítica.

        Es el puente entre el nombre técnico del INEC (que cambia entre años)
        y el nombre legible que usará Silver.
        """
        aliases = aliases or CRITICAL_ALIASES
        rows: List[Dict[str, Any]] = []
        for canon, options in aliases.items():
            row: Dict[str, Any] = {"variable_silver": canon}
            for year, schema in sorted(self.schemas.items()):
                cols = set(schema.csv_columns)
                match = next((normalize_name(o) for o in options
                              if normalize_name(o) in cols), None)
                row[year] = match
            row["disponible_en"] = sum(1 for y in self.schemas if row.get(y))
            rows.append(row)
        df = pd.DataFrame(rows)
        df["estado"] = df["disponible_en"].map(
            lambda n: "✅ completa" if n == len(self.schemas)
            else ("⚠️ parcial" if n else "❌ ausente"))
        return df

    def labels_for(self, variable: str, year: Optional[int] = None) -> Dict[str, str]:
        """Etiquetas código→valor de una variable, según el diccionario."""
        variable = normalize_name(variable)
        years = [year] if year else sorted(self.schemas, reverse=True)
        for y in years:
            labels = self.schemas.get(y, YearSchema(y)).value_labels.get(variable)
            if labels:
                return labels
        return {}

    # ------------------------------------------------------------------ #
    # Auditoría de calidad (muestra)
    # ------------------------------------------------------------------ #
    def audit(self, sample_rows: int = 50_000,
              key_candidates: Sequence[str] = ("id_persona", "id_hogar", "conglomerado",
                                               "vivienda", "hogar", "p01", "periodo")) -> pd.DataFrame:
        """Auditoría de calidad por año sobre una muestra de filas.

        Reporta: filas, columnas, % nulos medio, duplicados de llave,
        rango de edad, suma de factor de expansión y variables críticas ausentes.
        """
        crit = self.resolve_critical().set_index("variable_silver")
        rows: List[Dict[str, Any]] = []

        for year, schema in sorted(self.schemas.items()):
            if not schema.csv_path:
                continue
            df = read_csv_smart(schema.csv_path, nrows=sample_rows)
            key = [c for c in key_candidates if c in df.columns]
            edad_col = crit.at["edad", year] if year in crit.columns else None
            fexp_col = crit.at["factor_expansion", year] if year in crit.columns else None
            faltantes = [v for v in crit.index if not crit.at[v, year]] if year in crit.columns else []

            rows.append({
                "anio": year,
                "filas_totales": schema.n_rows,
                "filas_muestra": len(df),
                "columnas": len(df.columns),
                "peso_mb": schema.size_mb,
                "encoding": schema.dialect.get("encoding"),
                "sep": schema.dialect.get("sep"),
                "pct_nulos_medio": round(df.isna().mean().mean() * 100, 2),
                "cols_100pct_nulas": int((df.isna().mean() == 1).sum()),
                "llave_detectada": " + ".join(key) if key else "—",
                "dups_llave": int(df.duplicated(subset=key).sum()) if key else None,
                "edad_min": float(pd.to_numeric(df[edad_col], errors="coerce").min())
                            if edad_col in df.columns else None,
                "edad_max": float(pd.to_numeric(df[edad_col], errors="coerce").max())
                            if edad_col in df.columns else None,
                "fexp_presente": bool(fexp_col in df.columns) if fexp_col else False,
                "criticas_faltantes": ", ".join(faltantes) if faltantes else "—",
            })

        self._audit = pd.DataFrame(rows)
        return self._audit

    # ------------------------------------------------------------------ #
    # Reporte
    # ------------------------------------------------------------------ #
    def summary(self) -> pd.DataFrame:
        """Resumen tabular del análisis de esquemas."""
        return pd.DataFrame([{
            "anio": y,
            "csv": s.csv_path.name if s.csv_path else "—",
            "diccionario": s.dict_path.name if s.dict_path else "—",
            "filas": s.n_rows,
            "cols_csv": len(s.csv_columns),
            "cols_dicc": len(s.dict_columns),
            "cobertura_%": s.coverage,
            "solo_en_csv": len(s.only_in_csv),
            "solo_en_dicc": len(s.only_in_dict),
            "cols_exclusivas": len(self.year_specific.get(y, [])),
            "variables_con_etiquetas_valor": s.n_variables_con_etiquetas,
            "mapeo_semantico_validable": s.n_variables_con_etiquetas > 0,
        } for y, s in sorted(self.schemas.items())])

    def save_report(self, path: Optional[Path] = None) -> Path:
        """Persiste el análisis completo en JSON (trazabilidad)."""
        stamp = datetime.now().strftime("%Y%m%d")
        path = Path(path) if path else self.paths.reports / "schemas" / f"schema_analysis_{stamp}.json"
        payload = {
            "generado": datetime.now().isoformat(timespec="seconds"),
            "bronze_dir": str(self.paths.bronze),
            "anios": sorted(self.schemas),
            "n_columnas_comunes": len(self.common_columns),
            "columnas_comunes": self.common_columns,
            "columnas_por_anio_exclusivas": self.year_specific,
            "variables_criticas": self.resolve_critical().to_dict(orient="records"),
            "auditoria": (self._audit.to_dict(orient="records")
                          if self._audit is not None else None),
            "esquemas": {y: s.to_dict() for y, s in sorted(self.schemas.items())},
        }
        save_json(payload, path)
        log.info("Reporte de esquemas guardado en %s", path)
        return path


if __name__ == "__main__":  # pragma: no cover
    an = ENEMDUSchemaAnalyzer()
    an.analyze_all()
    print(an.summary().to_string(index=False))
    print(an.audit().to_string(index=False))
    an.save_report()
