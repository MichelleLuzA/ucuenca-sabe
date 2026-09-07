"""
enemdu_silver_builder.py
========================
Objetivo 2 del pipeline: construir la capa **Silver** (limpia y unificada)
a partir de la capa Bronze de ENEMDU 2021-2025.

Transformaciones aplicadas
--------------------------
1. **Resolución de esquema por año**: se mapea cada variable canónica a su
   alias real en el CSV del año (los nombres cambian entre publicaciones).
2. **Selección de columnas**: sólo se leen las necesarias (`usecols`), lo que
   mantiene el consumo de memoria acotado.
3. **Unificación 2021-2025**: las columnas ausentes en un año se añaden como
   NULL (NaN) para conservar un esquema estable.
4. **Estandarización de nombres**: nombres legibles y consistentes.
5. **Tipado y limpieza**: coerción numérica, rangos válidos, códigos de
   no-respuesta (9/99/999...) convertidos a NaN, deduplicación por llave.
6. **Decodificación semántica**: código → etiqueta usando el diccionario del
   año (con fallback documentado) para sexo, área, nivel de instrucción,
   condición de actividad, provincia, CIUO-08 y CIIU-4.
7. **Derivadas analíticas**: PEA, ocupado, desempleado, graduado superior,
   grupo etario y marca de **sobrecalificación** (graduado en ocupación
   CIUO-08 de grandes grupos 4-9).
8. **Persistencia**: Parquet único `enemdu_unificado.parquet` (+ opcional
   particionado por año) y reporte de calidad JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .enemdu_mappings import (
    CATEGORIAS_DESEMPLEADO,
    CATEGORIAS_OCUPADO,
    CATEGORIAS_SUBEMPLEO,
    CIIU4_SECCIONES,
    CIUO08_GRUPOS,
    CIUO08_SKILL_LEVEL,
    COLUMN_ALIASES,
    CONDACT_PATTERNS,
    EDU_PATTERNS,
    FALLBACK_AREA,
    FALLBACK_CONDACT,
    FALLBACK_NIVEL_INSTRUCCION,
    FALLBACK_NNIVINS,
    FALLBACK_SEXO,
    GRUPOS_REQUIEREN_SUPERIOR,
    NIVEL_INSTRUCCION_GRADUADO_RULE,
    NIVEL_INSTRUCCION_GRADUADO_RULE_DEFAULT,
    PROVINCIAS_EC,
    REQUIRED_FOR_GOLD,
    ciuo_major_group,
    resolve_map,
)
from .enemdu_schema_analyzer import ENEMDUSchemaAnalyzer
from .io_utils import ENEMDUPaths, get_logger, normalize_name, read_csv_smart, save_json

log = get_logger(__name__)

#: Reglas de rango válido: columna → (mínimo, máximo)
VALID_RANGES: Dict[str, tuple] = {
    "edad": (0, 110),
    "horas_trabajadas": (0, 126),
    "ingreso_laboral": (0, 100_000),
    "anios_aprobados": (0, 12),
    "factor_expansion": (0, 100_000),
}

#: Códigos de no-respuesta habituales en ENEMDU para variables continuas.
MISSING_CODES: Dict[str, Sequence[float]] = {
    "ingreso_laboral": (999_999, 99_999, -1, -99),
    "horas_trabajadas": (999, 99, -1),
    "edad": (999, -1),
}

GRUPOS_EDAD = [(15, 24, "15-24"), (25, 34, "25-34"), (35, 44, "35-44"),
               (45, 54, "45-54"), (55, 64, "55-64"), (65, 120, "65+")]

#: % de nulos en `factor_expansion` a partir del cual se considera un problema
#: de mapeo de esa columna (no un vacío legítimo: INEC siempre publica peso).
UMBRAL_NULOS_FEXP_PCT = 1.0


@dataclass
class SilverResult:
    """Resultado de la construcción de Silver."""
    df: pd.DataFrame
    parquet_path: Optional[Path] = None
    quality: pd.DataFrame = field(default_factory=pd.DataFrame)
    mapping_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    provenance: Dict[str, Any] = field(default_factory=dict)
    dedup_report: Dict[int, Any] = field(default_factory=dict)


class ENEMDUSilverBuilder:
    """Construye la capa Silver unificada de ENEMDU."""

    def __init__(
        self,
        analyzer: Optional[ENEMDUSchemaAnalyzer] = None,
        paths: Optional[ENEMDUPaths] = None,
        years: Optional[Sequence[int]] = None,
        aliases: Optional[Dict[str, List[str]]] = None,
        extra_columns: Optional[Sequence[str]] = None,
    ) -> None:
        self.analyzer = analyzer or ENEMDUSchemaAnalyzer(paths=paths, years=years)
        if not self.analyzer.schemas:
            self.analyzer.analyze_all()
        self.paths = self.analyzer.paths.ensure()
        self.years = list(years) if years else sorted(self.analyzer.schemas)
        self.aliases = aliases or COLUMN_ALIASES
        self.extra_columns = [normalize_name(c) for c in (extra_columns or [])]
        self._mapping_rows: List[Dict[str, Any]] = []
        self._provenance: Dict[str, Any] = {}
        self._dedup_report: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Resolución de columnas
    # ------------------------------------------------------------------ #
    def _resolve_columns(self, year: int) -> Dict[str, str]:
        """canónico → nombre real en el CSV del año (sólo los encontrados)."""
        available = set(self.analyzer.schemas[year].csv_columns)
        resolved: Dict[str, str] = {}
        for canon, options in self.aliases.items():
            for opt in options:
                col = normalize_name(opt)
                if col in available and col not in resolved.values():
                    resolved[canon] = col
                    break
        for extra in self.extra_columns:
            if extra in available:
                resolved[extra] = extra
        self._mapping_rows.append({"anio": year, **{k: v for k, v in resolved.items()}})
        return resolved

    # ------------------------------------------------------------------ #
    # Limpieza
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_numeric(df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ".", regex=False).str.strip(),
                    errors="coerce",
                )
        return df

    def _clean_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Coerción numérica, códigos de no-respuesta y rangos válidos."""
        numeric_cols = [c for c in df.columns
                        if c.endswith("_cod") or c in VALID_RANGES or c in
                        ("factor_expansion", "codigo_ciudad", "codigo_provincia",
                         "ocupacion_cod")]
        df = self._to_numeric(df, numeric_cols)

        # `id_persona` es un IDENTIFICADOR (código INEC de 22 dígitos: provincia+
        # cantón+parroquia+zona+sector+vivienda+hogar+persona), NO una cantidad.
        # Convertirlo a numérico (antes incluido arriba) lo pasaba por float64,
        # que sólo tiene ~15-17 dígitos significativos: un id de 22 dígitos pierde
        # precisión y distintas personas colapsan al mismo valor redondeado. Eso
        # rompía la deduplicación (ver `_deduplicate_per_year`): en 2021 borraba
        # 258,302 de 361,790 filas como "duplicados" que en realidad eran personas
        # distintas (361,790 id_persona únicos de verdad → sólo 44,900 tras
        # redondear a float64), dejando la población expandida en ~4.7M en vez de
        # los ~17.8M reales de Ecuador. Se mantiene como texto exacto.
        if "id_persona" in df.columns:
            df["id_persona"] = df["id_persona"].astype(str).str.strip()
            df.loc[df["id_persona"].isin(["", "nan", "None", "<NA>"]), "id_persona"] = np.nan

        for col, codes in MISSING_CODES.items():
            if col in df.columns:
                df.loc[df[col].isin(list(codes)), col] = np.nan

        for col, (lo, hi) in VALID_RANGES.items():
            if col in df.columns:
                df.loc[(df[col] < lo) | (df[col] > hi), col] = np.nan

        # Códigos categóricos como enteros nullable (evita 1.0 en Power BI)
        for col in [c for c in df.columns if c.endswith("_cod")]:
            df[col] = df[col].astype("Int64")
        return df

    # ------------------------------------------------------------------ #
    # Decodificación semántica
    # ------------------------------------------------------------------ #
    def _decode(self, df: pd.DataFrame, year: int, resolved: Dict[str, str]) -> pd.DataFrame:
        """Traduce códigos a etiquetas usando el diccionario del año."""
        schema = self.analyzer.schemas[year]
        prov: Dict[str, str] = {}

        def labels_of(canon: str) -> Dict[str, str]:
            src = resolved.get(canon)
            return schema.value_labels.get(src, {}) if src else {}

        # `nivel_instruccion_cod` no es una sola variable: según el año resuelve a
        # `p10a` (10 categorías) o a `nnivins` (2023 SOLO, 5 categorías, estructura
        # distinta e incompatible). Usar el fallback de p10a para nnivins clasificaba
        # mal sus códigos (p. ej. nnivins=5 "Superior" terminaba etiquetado como
        # "Educación Básica"). Ver CORRECCIONES_NIVEL_INSTRUCCION.md.
        educ_source = resolved.get("nivel_instruccion_cod", "")
        if educ_source == "nnivins":
            educ_map = resolve_map(labels_of("nivel_instruccion_cod"), None, FALLBACK_NNIVINS)
        else:
            educ_map = resolve_map(labels_of("nivel_instruccion_cod"),
                                   EDU_PATTERNS, FALLBACK_NIVEL_INSTRUCCION)

        maps = {
            "sexo": resolve_map(labels_of("sexo_cod"), None, FALLBACK_SEXO),
            "area": resolve_map(labels_of("area_cod"), None, FALLBACK_AREA),
            "nivel_instruccion": educ_map,
            "condicion_actividad": resolve_map(labels_of("condicion_actividad_cod"),
                                               CONDACT_PATTERNS, FALLBACK_CONDACT),
            "rama_actividad": resolve_map(labels_of("rama_agrupada_cod"), None, CIIU4_SECCIONES),
        }
        for name, (mapping, origin) in maps.items():
            cod_col = {"sexo": "sexo_cod", "area": "area_cod",
                       "nivel_instruccion": "nivel_instruccion_cod",
                       "condicion_actividad": "condicion_actividad_cod",
                       "rama_actividad": "rama_agrupada_cod"}[name]
            prov[name] = origin
            df[name] = (df[cod_col].map(mapping) if cod_col in df.columns else pd.NA)

        prov["nivel_instruccion_variable"] = educ_source or None
        self._provenance[year] = prov

        # "Graduado superior" se deriva del CÓDIGO numérico (no del texto de
        # `nivel_instruccion`) aplicando la regla correspondiente a la variable
        # fuente de este año: p10a >= 8, nnivins == 5. Es más robusto que
        # depender de que el diccionario del año redacte la etiqueta con una
        # palabra que EDU_PATTERNS reconozca (p. ej. "Superior" a secas en
        # nnivins no matchea "superior universitar").
        umbral, operador = NIVEL_INSTRUCCION_GRADUADO_RULE.get(
            educ_source, NIVEL_INSTRUCCION_GRADUADO_RULE_DEFAULT)
        if "nivel_instruccion_cod" in df.columns:
            codigo = df["nivel_instruccion_cod"]
            df["es_graduado_superior"] = (codigo.eq(umbral) if operador == "eq"
                                          else codigo.ge(umbral)).fillna(False)
        else:
            df["es_graduado_superior"] = False

        # Provincia: variable propia o primeros 2 dígitos del código de ciudad
        if "codigo_provincia" in df.columns and df["codigo_provincia"].notna().any():
            prov_code = df["codigo_provincia"]
        elif "codigo_ciudad" in df.columns:
            prov_code = (df["codigo_ciudad"].astype("Float64")
                         .astype("Int64").astype(str).str.zfill(6).str[:2]
                         .replace("na", pd.NA).astype("Int64"))
        else:
            prov_code = pd.Series(pd.NA, index=df.index, dtype="Int64")
        df["codigo_provincia"] = prov_code
        df["provincia"] = prov_code.map(PROVINCIAS_EC)

        # CIUO-08: gran grupo desde la ocupación detallada o el grupo agregado
        source = None
        for candidate in ("ocupacion_cod", "grupo_ocupacion_cod"):
            if candidate in df.columns and df[candidate].notna().any():
                source = candidate
                break
        if source:
            major = df[source].map(ciuo_major_group).astype("Int64")
        else:
            major = pd.Series(pd.NA, index=df.index, dtype="Int64")
        df["ciuo_gran_grupo"] = major
        df["ciuo_gran_grupo_desc"] = major.map(CIUO08_GRUPOS)
        df["ciuo_nivel_competencia"] = major.map(CIUO08_SKILL_LEVEL).astype("Int64")
        return df

    # ------------------------------------------------------------------ #
    # Variables derivadas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _derive(df: pd.DataFrame) -> pd.DataFrame:
        """Genera flags analíticos para las capas Gold / Power BI."""
        cond = df["condicion_actividad"]

        df["es_ocupado"] = cond.isin(CATEGORIAS_OCUPADO)
        df["es_desempleado"] = cond.isin(CATEGORIAS_DESEMPLEADO)
        df["es_subempleado"] = cond.isin(CATEGORIAS_SUBEMPLEO)
        df["es_empleo_adecuado"] = cond.eq("Empleo adecuado/pleno")
        df["es_pea"] = df["es_ocupado"] | df["es_desempleado"]
        df["es_edad_trabajar"] = df["edad"].ge(15)

        # `es_graduado_superior` ya viene calculado desde `_decode` (por código,
        # no por texto de etiqueta — ver NIVEL_INSTRUCCION_GRADUADO_RULE).
        # `es_posgrado` sí depende del texto: sólo distinguible en años con p10a;
        # en 2023 (nnivins) el posgrado queda dentro de "Superior" sin desagregar.
        df["es_posgrado"] = df["nivel_instruccion"].eq("Post-grado")

        # Sobrecalificación: graduado superior ocupado en CIUO-08 grupos 4-9
        requiere_superior = df["ciuo_gran_grupo"].isin(GRUPOS_REQUIEREN_SUPERIOR)
        df["ocupacion_requiere_superior"] = requiere_superior
        df["es_sobrecalificado"] = (
            df["es_graduado_superior"] & df["es_ocupado"]
            & df["ciuo_gran_grupo"].notna() & ~requiere_superior
        )

        # Grupo etario
        edad = df["edad"]
        grupo = pd.Series(pd.NA, index=df.index, dtype="object")
        for lo, hi, label in GRUPOS_EDAD:
            grupo = grupo.mask(edad.between(lo, hi), label)
        df["grupo_edad"] = grupo

        # Ingreso por hora (aprox. 4.33 semanas/mes)
        if {"ingreso_laboral", "horas_trabajadas"}.issubset(df.columns):
            horas_mes = df["horas_trabajadas"] * 4.33
            df["ingreso_por_hora"] = (df["ingreso_laboral"] / horas_mes).replace(
                [np.inf, -np.inf], np.nan)
        return df

    # ------------------------------------------------------------------ #
    # Construcción por año
    # ------------------------------------------------------------------ #
    def build_year(self, year: int, sample_rows: Optional[int] = None) -> pd.DataFrame:
        """Lee, limpia y estandariza un año de ENEMDU."""
        schema = self.analyzer.schemas.get(year)
        if not schema or not schema.csv_path:
            log.warning("Año %s sin CSV en Bronze; se omite.", year)
            return pd.DataFrame()

        resolved = self._resolve_columns(year)
        log.info("Año %s → %s/%s variables canónicas resueltas",
                 year, len(resolved), len(self.aliases))

        df = read_csv_smart(schema.csv_path, nrows=sample_rows,
                            usecols=list(resolved.values()))
        df = df.rename(columns={v: k for k, v in resolved.items()})

        # Esquema estable: columnas ausentes → NULL
        for canon in self.aliases:
            if canon not in df.columns:
                df[canon] = np.nan

        df["anio"] = year
        df["fuente"] = f"ENEMDU {year} (INEC)"
        df = self._clean_types(df)
        df = self._decode(df, year, resolved)
        df = self._derive(df)
        return df

    # ------------------------------------------------------------------ #
    # Deduplicación
    # ------------------------------------------------------------------ #
    def _deduplicate_per_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """Deduplica año por año (nunca cruzando años), sólo cuando hay una
        llave que identifica realmente a la persona.

        Dos riesgos, no uno:
        1. `pandas.DataFrame.duplicated` trata `NaN == NaN` como coincidencia,
           así que si `id_persona` se resuelve en unos años pero en otro queda
           completamente vacía, incluirla igual en la llave de ese año
           colapsaría TODAS las personas de un mismo hogar en una sola fila.
        2. `mes/conglomerado/vivienda/hogar` identifican al **hogar**, no a la
           persona: varios integrantes reales de un mismo hogar comparten
           exactamente esos valores. Deduplicar SOLO con esas columnas (sin
           `id_persona`) es igual de destructivo que el caso (1) — colapsaría
           el hogar completo a una fila.
        Por eso, si `id_persona` no está resuelta y no-nula (>95%) para el
        año, se omite la deduplicación de ese año por completo (igual que
        hacía el pipeline original cuando no había id_persona en absoluto),
        en vez de deduplicar por una llave a nivel de hogar.
        """
        base_key = [c for c in ("mes", "conglomerado", "vivienda", "hogar") if c in df.columns]
        partes: List[pd.DataFrame] = []
        self._dedup_report = {}

        for year, part in df.groupby("anio", sort=True):
            year = int(year)
            id_utilizable = False
            pct_valido = (part["id_persona"].notna().mean()
                          if "id_persona" in part.columns else 0.0)
            if pct_valido > 0.95:
                id_utilizable = True

            antes = len(part)
            if id_utilizable:
                key = [c for c in base_key if part[c].notna().any()] + ["id_persona"]
                part = part.drop_duplicates(subset=key, keep="first")
            else:
                key = []
                if pct_valido > 0:
                    log.warning(
                        "Año %s: id_persona sólo %.1f%% no-nula; se omite la deduplicación "
                        "de este año (deduplicar sólo por hogar colapsaría a sus integrantes "
                        "reales, que comparten conglomerado/vivienda/hogar).",
                        year, pct_valido * 100)
                else:
                    log.warning(
                        "Año %s: sin id_persona resuelta; se omite la deduplicación de este "
                        "año (revisa la llave real en el diccionario del año).", year)
            eliminadas = antes - len(part)
            if eliminadas:
                log.info("Año %s: deduplicación por %s: -%s filas", year, key, eliminadas)

            self._dedup_report[year] = {
                "llave": key,
                "id_persona_utilizable": id_utilizable,
                "filas_antes": antes,
                "filas_eliminadas": int(eliminadas),
            }
            partes.append(part)

        return pd.concat(partes, ignore_index=True)

    def build(self, sample_rows: Optional[int] = None,
              deduplicate: bool = True) -> SilverResult:
        """Construye la Silver unificada 2021-2025."""
        frames = []
        for year in self.years:
            part = self.build_year(year, sample_rows=sample_rows)
            if not part.empty:
                frames.append(part)

        if not frames:
            raise RuntimeError("No se pudo construir Silver: Bronze sin microdatos legibles.")

        df = pd.concat(frames, ignore_index=True, sort=False)

        if deduplicate:
            df = self._deduplicate_per_year(df)

        # Orden lógico de columnas
        front = ["anio", "mes", "provincia", "area", "sexo", "edad", "grupo_edad",
                 "nivel_instruccion", "es_graduado_superior", "condicion_actividad",
                 "es_ocupado", "es_desempleado", "es_sobrecalificado",
                 "ciuo_gran_grupo_desc", "rama_actividad", "ingreso_laboral",
                 "horas_trabajadas", "factor_expansion"]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

        result = SilverResult(df=df, quality=self.validate(df),
                              mapping_report=pd.DataFrame(self._mapping_rows),
                              provenance=self._provenance,
                              dedup_report=self._dedup_report)
        return result

    # ------------------------------------------------------------------ #
    # Validación y persistencia
    # ------------------------------------------------------------------ #
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reporte de calidad por año de la Silver construida."""
        rows: List[Dict[str, Any]] = []
        for year, part in df.groupby("anio"):
            year = int(year)
            fexp = part["factor_expansion"] if "factor_expansion" in part else pd.Series(dtype=float)
            pct_nulos_fexp = round(fexp.isna().mean() * 100, 2) if not fexp.empty else 100.0
            dedup = self._dedup_report.get(year, {})
            rows.append({
                "anio": year,
                "filas": len(part),
                "poblacion_expandida": round(float(fexp.sum()), 0) if not fexp.empty else None,
                "edad_media": round(float(part["edad"].mean()), 1),
                "%_nulos_nivel_instruccion": round(part["nivel_instruccion"].isna().mean() * 100, 2),
                "%_nulos_condicion_actividad": round(part["condicion_actividad"].isna().mean() * 100, 2),
                "%_nulos_ciuo": round(part["ciuo_gran_grupo"].isna().mean() * 100, 2),
                "%_nulos_ingreso": round(part["ingreso_laboral"].isna().mean() * 100, 2),
                "%_nulos_fexp": pct_nulos_fexp,
                "fexp_media": round(float(fexp.mean()), 1) if not fexp.empty else None,
                "fexp_mediana": round(float(fexp.median()), 1) if not fexp.empty else None,
                "fexp_max": round(float(fexp.max()), 1) if not fexp.empty else None,
                "graduados_superior": int(part["es_graduado_superior"].sum()),
                "ocupados": int(part["es_ocupado"].sum()),
                "desempleados": int(part["es_desempleado"].sum()),
                "mapeo_educacion": self._provenance.get(year, {}).get("nivel_instruccion"),
                "mapeo_educacion_variable": self._provenance.get(year, {}).get("nivel_instruccion_variable"),
                "mapeo_condact": self._provenance.get(year, {}).get("condicion_actividad"),
                "dedup_llave": dedup.get("llave"),
                "dedup_id_persona_utilizable": dedup.get("id_persona_utilizable"),
                "dedup_filas_eliminadas": dedup.get("filas_eliminadas"),
            })
        report = pd.DataFrame(rows)

        faltantes = [c for c in REQUIRED_FOR_GOLD if c not in df.columns or df[c].isna().all()]
        if faltantes:
            log.error("Variables críticas ausentes o vacías: %s", faltantes)

        alerta_fexp = report[report["%_nulos_fexp"] > UMBRAL_NULOS_FEXP_PCT]
        if not alerta_fexp.empty:
            log.error(
                "Factor de expansión con nulos por encima del umbral (%s%%) en los años %s: "
                "esas filas quedarán con peso 0 en Gold (población subestimada). Revisa el "
                "alias resuelto en mapping_report para esos años.",
                UMBRAL_NULOS_FEXP_PCT, alerta_fexp["anio"].tolist())
        return report

    def save(self, result: SilverResult, filename: str = "enemdu_unificado.parquet",
             partition_by_year: bool = False) -> Path:
        """Persiste la Silver en Parquet y el reporte de calidad en JSON."""
        self.paths.silver.mkdir(parents=True, exist_ok=True)
        out = self.paths.silver / filename
        result.df.to_parquet(out, index=False, compression="snappy")
        result.parquet_path = out
        log.info("Silver guardada: %s (%s filas, %s cols, %.1f MB)",
                 out, len(result.df), result.df.shape[1], out.stat().st_size / 1e6)

        if partition_by_year:
            for year, part in result.df.groupby("anio"):
                sub = self.paths.silver / "por_anio"
                sub.mkdir(exist_ok=True)
                part.to_parquet(sub / f"enemdu_{int(year)}.parquet", index=False)

        save_json({
            "generado": datetime.now().isoformat(timespec="seconds"),
            "parquet": str(out),
            "filas": len(result.df),
            "columnas": list(result.df.columns),
            "anios": sorted(result.df["anio"].unique().tolist()),
            "procedencia_mapeos": result.provenance,
            "deduplicacion": result.dedup_report,
            "calidad": result.quality.to_dict(orient="records"),
        }, self.paths.reports / "schemas" /
            f"silver_quality_{datetime.now():%Y%m%d}.json")
        return out


def load_silver(paths: Optional[ENEMDUPaths] = None,
                filename: str = "enemdu_unificado.parquet") -> pd.DataFrame:
    """Carga la Silver existente (atajo para notebooks)."""
    paths = paths or ENEMDUPaths.build()
    return pd.read_parquet(paths.silver / filename)


if __name__ == "__main__":  # pragma: no cover
    builder = ENEMDUSilverBuilder()
    res = builder.build()
    print(res.quality.to_string(index=False))
    builder.save(res)
