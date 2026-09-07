"""
enemdu_gold_builder.py
======================
Objetivo 3 del pipeline: construir la capa **Gold** con métricas de
empleabilidad de graduados universitarios y sobrecalificación, lista para
Power BI.

Definiciones operativas
-----------------------
* **Graduado superior** (= "educación superior"): nivel de instrucción
  "Superior no universitaria", "Superior universitaria" o "Post-grado"
  (código `p10a` >= 8, o `nnivins` == 5 en 2023), sin restricción de edad.
  Se define por código numérico en Silver, no por texto de etiqueta — ver
  `NIVEL_INSTRUCCION_GRADUADO_RULE` en `enemdu_mappings.py`.
* **PEA**: ocupados + desempleados de 15 años y más.
* **Tasa de desempleo** = desempleados / PEA.
* **Tasa de empleo adecuado** = empleo adecuado/pleno / PEA.
* **Sobrecalificación**: graduado superior ocupado en una ocupación cuyo gran
  grupo CIUO-08 es 4-9 (nivel de competencia 1-2, no requiere título
  universitario). Criterio normativo ILO/CIUO-08. Sólo tiene sentido para
  graduados: no existe versión "general" de esta tabla.
* Todos los indicadores se calculan **ponderados por el factor de expansión**
  (`fexp`); se reporta además el `n` muestral para control de precisión.

Segmentación `segmento` (general vs. educación superior)
----------------------------------------------------------
`kpi_anual`, `empleabilidad_provincia`, `empleabilidad_sexo_edad` y
`por_rama` traen una columna `segmento` con dos valores:

* `"general"` — toda la PEA/PET, cualquier nivel de instrucción.
* `"educacion_superior"` — sólo graduados superiores (subconjunto del anterior).

**Los segmentos están anidados, no son una partición**: "educacion_superior"
⊂ "general". Nunca sumar/promediar filas de ambos segmentos juntas (duplicaría
población); un consumidor (Power BI, `generate_dashboard_data.py`) debe
filtrar por `segmento` antes de agregar o graficar.

Salidas
-------
* `data/gold/enemdu/empleabilidad_graduados.parquet` — tabla de hechos (graduados).
* `reports/powerbi/*.csv` — tablas planas listas para importar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .io_utils import ENEMDUPaths, get_logger, save_json

log = get_logger(__name__)

#: Tamaño muestral mínimo para publicar un indicador (control de precisión).
N_MINIMO = 30


@dataclass
class GoldResult:
    """Colección de tablas de la capa Gold."""
    hechos: pd.DataFrame
    kpi_anual: pd.DataFrame
    por_provincia: pd.DataFrame
    por_sexo_edad: pd.DataFrame
    sobrecalificacion_ocupacion: pd.DataFrame
    por_rama: pd.DataFrame
    comparativo_nivel: pd.DataFrame
    paths: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, pd.DataFrame]:
        return {
            "empleabilidad_graduados": self.hechos,
            "kpi_anual": self.kpi_anual,
            "empleabilidad_provincia": self.por_provincia,
            "empleabilidad_sexo_edad": self.por_sexo_edad,
            "sobrecalificacion_ocupacion": self.sobrecalificacion_ocupacion,
            "graduados_rama_actividad": self.por_rama,
            "comparativo_nivel_instruccion": self.comparativo_nivel,
        }


class ENEMDUGoldBuilder:
    """Genera los agregados de empleabilidad a partir de la Silver."""

    def __init__(self, silver: pd.DataFrame,
                 paths: Optional[ENEMDUPaths] = None,
                 edad_minima: int = 15) -> None:
        self.paths = (paths or ENEMDUPaths.build()).ensure()
        self.edad_minima = edad_minima
        self.df = self._prepare(silver)

    # ------------------------------------------------------------------ #
    # Preparación
    # ------------------------------------------------------------------ #
    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filtra población en edad de trabajar y normaliza el ponderador."""
        out = df.copy()
        if "factor_expansion" not in out.columns:
            log.warning("Sin columna factor_expansion en Silver: se usará peso = 1 "
                        "(resultados no expandidos).")
            out["factor_expansion"] = 1.0
        else:
            # Un año ENTERO sin fexp resuelto (alias no encontrado ese año) es
            # distinto de nulos sueltos: aquí NO se debe caer a fillna(0)
            # global, porque eso pondría a peso 0 a TODA la población de ese
            # año (la haría desaparecer de Gold) en vez de dejarla sin
            # expandir. Se detecta por año y se usa peso = 1 sólo ahí.
            nulo_total_por_anio = out.groupby("anio")["factor_expansion"].apply(
                lambda s: s.isna().all())
            anios_sin_fexp = nulo_total_por_anio[nulo_total_por_anio].index.tolist()
            if anios_sin_fexp:
                log.warning(
                    "Años sin factor de expansión resuelto: %s → se usará peso = 1 "
                    "sólo para esas filas (resultados NO expandidos ni comparables "
                    "con el resto de los años; revisa mapping_report de Silver).",
                    anios_sin_fexp)
                mask = out["anio"].isin(anios_sin_fexp)
                out.loc[mask, "factor_expansion"] = out.loc[mask, "factor_expansion"].fillna(1.0)

            pct_nulo_restante = out["factor_expansion"].isna().mean()
            if pct_nulo_restante > 0:
                log.warning(
                    "%.2f%% de filas con factor de expansión nulo (no son años completos "
                    "sin resolver): quedan con peso = 0, es decir, se excluyen de todos los "
                    "indicadores ponderados. Revisar antes de publicar Gold.",
                    pct_nulo_restante * 100)
        out["factor_expansion"] = out["factor_expansion"].fillna(0)

        antes = len(out)
        out = out[out["edad"].ge(self.edad_minima).fillna(False)]
        log.info("PET (>= %s años): %s de %s filas", self.edad_minima, len(out), antes)

        # "Graduado superior" se define únicamente por nivel_instruccion (igual
        # que en Silver): NO se recorta además por edad. Antes se exigía edad
        # >= 24, lo que subestimaba la población de graduados al excluir a
        # quienes obtuvieron el título antes de esa edad.
        out["es_graduado_superior"] = out["es_graduado_superior"].fillna(False)
        return out

    # ------------------------------------------------------------------ #
    # Núcleo de agregación
    # ------------------------------------------------------------------ #
    @staticmethod
    def _aggregate(df: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
        """Suma ponderada de los indicadores base para las dimensiones `by`."""
        w = df["factor_expansion"]
        tmp = pd.DataFrame({
            **{c: df[c] for c in by},
            "n_muestral": 1,
            "poblacion": w,
            "pea": w.where(df["es_pea"].fillna(False), 0),
            "ocupados": w.where(df["es_ocupado"].fillna(False), 0),
            "desempleados": w.where(df["es_desempleado"].fillna(False), 0),
            "empleo_adecuado": w.where(df["es_empleo_adecuado"].fillna(False), 0),
            "subempleados": w.where(df["es_subempleado"].fillna(False), 0),
            "sobrecalificados": w.where(df["es_sobrecalificado"].fillna(False), 0),
            "ocupados_con_ciuo": w.where(
                df["es_ocupado"].fillna(False) & df["ciuo_gran_grupo"].notna(), 0),
            "ingreso_pond": (df["ingreso_laboral"] * w).where(df["es_ocupado"].fillna(False), np.nan),
            "peso_ingreso": w.where(df["es_ocupado"].fillna(False) & df["ingreso_laboral"].notna(), 0),
        })
        agg = tmp.groupby(list(by), dropna=False, observed=True).agg(
            n_muestral=("n_muestral", "sum"),
            poblacion=("poblacion", "sum"),
            pea=("pea", "sum"),
            ocupados=("ocupados", "sum"),
            desempleados=("desempleados", "sum"),
            empleo_adecuado=("empleo_adecuado", "sum"),
            subempleados=("subempleados", "sum"),
            sobrecalificados=("sobrecalificados", "sum"),
            ocupados_con_ciuo=("ocupados_con_ciuo", "sum"),
            ingreso_pond=("ingreso_pond", "sum"),
            peso_ingreso=("peso_ingreso", "sum"),
        ).reset_index()
        return agg

    @staticmethod
    def _rates(agg: pd.DataFrame) -> pd.DataFrame:
        """Deriva tasas (%) a partir de los agregados ponderados."""
        def pct(num: pd.Series, den: pd.Series) -> pd.Series:
            return (100 * num / den.replace(0, np.nan)).round(2)

        out = agg.copy()
        out["tasa_participacion"] = pct(out["pea"], out["poblacion"])
        out["tasa_empleo"] = pct(out["ocupados"], out["pea"])
        out["tasa_desempleo"] = pct(out["desempleados"], out["pea"])
        out["tasa_empleo_adecuado"] = pct(out["empleo_adecuado"], out["pea"])
        out["tasa_subempleo"] = pct(out["subempleados"], out["pea"])
        out["tasa_sobrecalificacion"] = pct(out["sobrecalificados"], out["ocupados_con_ciuo"])
        out["ingreso_laboral_medio"] = (
            out["ingreso_pond"] / out["peso_ingreso"].replace(0, np.nan)).round(2)
        out["confiable"] = out["n_muestral"] >= N_MINIMO
        for col in ("poblacion", "pea", "ocupados", "desempleados", "empleo_adecuado",
                    "subempleados", "sobrecalificados", "ocupados_con_ciuo"):
            out[col] = out[col].round(0)
        return out.drop(columns=["ingreso_pond", "peso_ingreso"])

    def _metric_table(self, by: Sequence[str], solo_graduados: bool = True) -> pd.DataFrame:
        base = self.df[self.df["es_graduado_superior"]] if solo_graduados else self.df
        return self._rates(self._aggregate(base, by))

    def _segmented_metric_table(self, by: Sequence[str]) -> pd.DataFrame:
        """La misma tabla de métricas para dos poblaciones anidadas (no una
        partición): `general` (toda la PEA/PET) y `educacion_superior`
        (subconjunto graduados). Ver nota de módulo sobre `segmento`."""
        general = self._metric_table(by, solo_graduados=False)
        general.insert(0, "segmento", "general")
        superior = self._metric_table(by, solo_graduados=True)
        superior.insert(0, "segmento", "educacion_superior")
        return pd.concat([general, superior], ignore_index=True)

    # ------------------------------------------------------------------ #
    # Tablas de la capa Gold
    # ------------------------------------------------------------------ #
    def build(self) -> GoldResult:
        """Construye todas las tablas agregadas de Gold."""
        log.info("Construyendo Gold sobre %s filas de Silver...", len(self.df))

        dims = [d for d in ("anio", "provincia", "area", "sexo", "grupo_edad",
                            "nivel_instruccion") if d in self.df.columns]
        hechos = self._metric_table(dims)

        kpi_anual = self._segmented_metric_table(["anio"])

        por_provincia = self._segmented_metric_table(["anio", "provincia"])

        por_sexo_edad = self._segmented_metric_table(["anio", "sexo", "grupo_edad"])
        # Brecha de género en puntos porcentuales (mujeres - hombres), por segmento
        pivot = por_sexo_edad.pivot_table(index=["segmento", "anio", "grupo_edad"],
                                          columns="sexo", values="tasa_desempleo", observed=True)
        if {"Hombre", "Mujer"}.issubset(pivot.columns):
            brecha = (pivot["Mujer"] - pivot["Hombre"]).rename(
                "brecha_desempleo_pp").reset_index()
            por_sexo_edad = por_sexo_edad.merge(
                brecha, on=["segmento", "anio", "grupo_edad"], how="left")

        graduados_ocupados = self.df[
            self.df["es_graduado_superior"] & self.df["es_ocupado"].fillna(False)
            & self.df["ciuo_gran_grupo"].notna()
        ]
        sobre_ocup = self._aggregate(graduados_ocupados,
                                     ["anio", "ciuo_gran_grupo", "ciuo_gran_grupo_desc"])
        sobre_ocup["participacion_ocupados_pct"] = sobre_ocup.groupby("anio")["ocupados"].transform(
            lambda s: (100 * s / s.sum()).round(2))
        sobre_ocup["requiere_titulo_superior"] = sobre_ocup["ciuo_gran_grupo"].isin([1, 2, 3])
        sobre_ocup["ingreso_laboral_medio"] = (
            sobre_ocup["ingreso_pond"] / sobre_ocup["peso_ingreso"].replace(0, np.nan)).round(2)
        sobre_ocup["ocupados"] = sobre_ocup["ocupados"].round(0)
        sobre_ocup = sobre_ocup[["anio", "ciuo_gran_grupo", "ciuo_gran_grupo_desc",
                                 "requiere_titulo_superior", "n_muestral", "ocupados",
                                 "participacion_ocupados_pct", "ingreso_laboral_medio"]]

        def _rama_table(base: pd.DataFrame, segmento: str) -> pd.DataFrame:
            tabla = self._aggregate(base, ["anio", "rama_actividad"])
            tabla["participacion_pct"] = tabla.groupby("anio")["ocupados"].transform(
                lambda s: (100 * s / s.sum()).round(2))
            tabla["tasa_sobrecalificacion"] = (
                100 * tabla["sobrecalificados"] / tabla["ocupados"].replace(0, np.nan)).round(2)
            tabla["ingreso_laboral_medio"] = (
                tabla["ingreso_pond"] / tabla["peso_ingreso"].replace(0, np.nan)).round(2)
            tabla[["ocupados", "sobrecalificados"]] = tabla[["ocupados", "sobrecalificados"]].round(0)
            tabla.insert(0, "segmento", segmento)
            return tabla[["segmento", "anio", "rama_actividad", "n_muestral", "ocupados",
                          "participacion_pct", "sobrecalificados",
                          "tasa_sobrecalificacion", "ingreso_laboral_medio"]]

        ocupados_general = self.df[
            self.df["es_ocupado"].fillna(False) & self.df["ciuo_gran_grupo"].notna()]
        por_rama = pd.concat([
            _rama_table(ocupados_general, "general"),
            _rama_table(graduados_ocupados, "educacion_superior"),
        ], ignore_index=True)

        comparativo = self._metric_table(["anio", "nivel_instruccion"], solo_graduados=False)
        # La sobrecalificación sólo está definida para niveles superiores
        from .enemdu_mappings import NIVELES_SUPERIOR
        comparativo.loc[~comparativo["nivel_instruccion"].isin(NIVELES_SUPERIOR),
                        "tasa_sobrecalificacion"] = np.nan

        result = GoldResult(
            hechos=hechos,
            kpi_anual=kpi_anual,
            por_provincia=por_provincia,
            por_sexo_edad=por_sexo_edad,
            sobrecalificacion_ocupacion=sobre_ocup,
            por_rama=por_rama,
            comparativo_nivel=comparativo,
        )
        return result

    # ------------------------------------------------------------------ #
    # Persistencia
    # ------------------------------------------------------------------ #
    def save(self, result: GoldResult, export_csv: bool = True) -> Dict[str, str]:
        """Guarda Gold en Parquet y (opcional) CSV para Power BI."""
        self.paths.gold.mkdir(parents=True, exist_ok=True)
        outputs: Dict[str, str] = {}

        for name, table in result.as_dict().items():
            pq = self.paths.gold / f"{name}.parquet"
            table.to_parquet(pq, index=False, compression="snappy")
            outputs[name] = str(pq)
            if export_csv:
                csv_dir = self.paths.reports / "powerbi"
                csv_dir.mkdir(parents=True, exist_ok=True)
                table.to_csv(csv_dir / f"{name}.csv", index=False,
                             encoding="utf-8-sig", sep=";", decimal=",")

        save_json({
            "generado": datetime.now().isoformat(timespec="seconds"),
            "definiciones": {
                "graduado_superior": (
                    "Nivel 'Superior no universitaria', 'Superior universitaria' o "
                    "'Post-grado' — código p10a >= 8, o nnivins == 5 en 2023 "
                    "(sin filtro de edad)."
                ),
                "sobrecalificacion": "Graduado ocupado en CIUO-08 grandes grupos 4-9",
                "ponderador": "factor de expansión (fexp)",
                "n_minimo_publicable": N_MINIMO,
                "segmento": (
                    "kpi_anual/empleabilidad_provincia/empleabilidad_sexo_edad/"
                    "graduados_rama_actividad traen columna 'segmento': "
                    "'general' (toda la PEA/PET) vs 'educacion_superior' (subconjunto "
                    "graduados). Anidados, NO sumar entre segmentos: filtrar antes de "
                    "agregar. sobrecalificacion_ocupacion es siempre sólo graduados."
                ),
            },
            "tablas": outputs,
        }, self.paths.reports / "schemas" / f"gold_manifest_{datetime.now():%Y%m%d}.json")

        result.paths = outputs
        log.info("Gold guardada: %s tablas en %s", len(outputs), self.paths.gold)
        return outputs


if __name__ == "__main__":  # pragma: no cover
    from .enemdu_silver_builder import load_silver

    gold = ENEMDUGoldBuilder(load_silver())
    res = gold.build()
    print(res.kpi_anual.to_string(index=False))
    gold.save(res)
