# Pipeline ENEMDU 2021-2025 — Bronze → Silver → Gold

Entregable para el MVP de empleabilidad (UCUENCA-SABE). Todo el código fue ejecutado
end-to-end contra un Bronze sintético que replica las trampas reales de ENEMDU
(separador `;` vs `,`, Latin-1 vs UTF-8, decimal con coma, variables renombradas
entre años, variables documentadas pero ausentes del CSV, códigos de no respuesta).

## 1. Dónde va cada archivo

```
UCUENCA-SABE/
├── notebooks/
│   └── 01_download_kaggle_enemdu.ipynb   ← reemplazar por el entregado
├── src/
│   └── processing/
│       ├── __init__.py
│       ├── io_utils.py                   ← rutas + lectura robusta CSV/XLSX
│       ├── enemdu_mappings.py            ← alias, códigos CIUO-08/CIIU-4, provincias
│       ├── enemdu_schema_analyzer.py     ← Objetivo 1 (auditoría + esquemas)
│       ├── enemdu_silver_builder.py      ← Objetivo 2 (Silver)
│       └── enemdu_gold_builder.py        ← Objetivo 3 (Gold)
└── scripts/
    └── run_enemdu_pipeline.py            ← orquestador CLI
```

Salidas generadas automáticamente:

```
data/silver/enemdu/enemdu_unificado.parquet
data/gold/enemdu/{empleabilidad_graduados, kpi_anual, empleabilidad_provincia,
                  empleabilidad_sexo_edad, sobrecalificacion_ocupacion,
                  graduados_rama_actividad, comparativo_nivel_instruccion}.parquet
reports/schemas/{schema_analysis_*, silver_quality_*, gold_manifest_*}.json
reports/powerbi/*.csv        (UTF-8-BOM, sep=";", decimal=",")
```

## 2. Requisitos

```bash
pip install pandas numpy pyarrow openpyxl matplotlib
```

## 3. config/config.yaml

No es obligatorio (hay convención de rutas por defecto), pero si lo declaras se respeta:

```yaml
sources:
  enemdu:
    bronze_dir: data/bronze/externas/enemdu
    anios: [2021, 2022, 2023, 2024, 2025]
    kaggle_dataset: kmichelle/enemdu-ecuador-microdatos-anuales-personas
    silver_file: enemdu_unificado.parquet
    gold_file: empleabilidad_graduados.parquet
```

`ENEMDUPaths.build()` lee `sources.enemdu.bronze_dir` de `src.config.CONFIG` y, si no
existe, cae a la convención `data/bronze/externas/enemdu`.

## 4. Ejecución

```bash
python scripts/run_enemdu_pipeline.py --all          # auditoría + Silver + Gold
python scripts/run_enemdu_pipeline.py --audit        # sólo Objetivo 1
python scripts/run_enemdu_pipeline.py --silver --gold --years 2024 2025
python scripts/run_enemdu_pipeline.py --all --sample 50000   # iteración rápida
```

O paso a paso, con explicación y gráficos, en el notebook.

## 5. Decisiones técnicas relevantes

| Tema | Decisión | Por qué |
|---|---|---|
| Dialecto de los CSV | Detección automática de encoding, separador y decimal | El INEC cambia el formato entre publicaciones; hardcodear `sep=";"` rompe años concretos |
| Nombres de variables | `COLUMN_ALIASES`: canónico → lista de alias, resuelto **por año** contra la cabecera real | `p51a`→`totalhoras`, `ingrl`→`ingreso_laboral`… la Silver mantiene un esquema estable |
| Códigos → etiquetas | Se leen del diccionario XLSX del año y se clasifican por regex; sólo si falla se usa el mapeo fallback documentado | Evita asumir que "9 = Superior universitaria" en todos los años; la procedencia (`diccionario`/`fallback`) queda en el reporte de calidad |
| Columnas ausentes en un año | Se añaden como `NaN`, nunca como 0 | Distinguir "no medido" de "cero" |
| No respuesta | `999999`, `99`, `-1` → `NaN`; rangos válidos por variable | Un `ingrl = 999999` promediado destruye cualquier indicador de ingresos |
| Deduplicación | Sólo si hay identificador de persona real; si no, advertencia y no se borra nada | En ENEMDU `p01` es *parentesco*, no id de persona: usarlo como llave elimina personas válidas |
| Filtros analíticos | PET (≥15) y graduados se aplican en **Gold**, no en Silver | Silver debe servir a otros casos de uso del dashboard |
| Ponderación | Todos los indicadores usan `fexp`; se reporta `n_muestral` y `confiable` (n ≥ 30) | Sin expandir, las tasas no son comparables con el INEC |
| Sobrecalificación | Graduado ocupado en CIUO-08 grandes grupos 4-9 (niveles de competencia 1-2) | Criterio normativo CIUO-08/OIT, reproducible y auditable |
| Power BI | Tabla de hechos con numeradores y denominadores, no sólo tasas | Las tasas **no se promedian**: en DAX debe ser `SUM(num)/SUM(den)` |

## 6. Qué revisar cuando corras con los datos reales

1. **`analyzer.resolve_critical()`** — cualquier fila `⚠️ parcial` o `❌ ausente` indica que
   hay que añadir el alias correcto en `COLUMN_ALIASES` (sección 2.4 del notebook).
2. **`mapeo_educacion` / `mapeo_condact` = `fallback`** en el reporte de calidad de Silver:
   significa que el diccionario de ese año no fue interpretable; revisar `EDU_PATTERNS`
   y `CONDACT_PATTERNS` en `enemdu_mappings.py`.
3. **`%_nulos_ciuo`** alto: si el año trae `grupo1` en lugar de `p41`, confirmar que el
   gran grupo se está derivando del primer dígito correcto.
4. **`TASAS_OFICIALES_INEC`** en la sección 5.2: completar con el boletín anual para
   validar la tasa de desempleo nacional calculada.
