# Guía del proyecto UCuenca-SABE! — como una clase

Esta guía explica, módulo por módulo, **qué hace cada parte del repositorio, con qué librerías, por qué se hizo así y qué hay que saber para modificarla**. Al final hay un glosario y recetas del tipo "para hacer X necesito saber Y".

> Convención: cada módulo sigue la misma estructura: **Qué es → Para qué sirve → Cómo funciona → Librerías → Qué hay que saber → Errores típicos**.

---

## Índice

0. [Mapa general del repositorio](#0-mapa-general-del-repositorio)
1. [Arquitectura medallón (Bronze / Silver / Gold)](#1-arquitectura-medallón-bronze--silver--gold)
2. [Configuración central](#2-configuración-central)
3. [Entorno y librerías](#3-entorno-y-librerías)
4. [Pipeline ENEMDU](#4-pipeline-enemdu)
5. [Pipeline de docentes e investigación](#5-pipeline-de-docentes-e-investigación)
6. [Pipeline de noticias de economía](#6-pipeline-de-noticias-de-economía)
7. [Automatización con GitHub Actions](#7-automatización-con-github-actions)
8. [Visualizadores](#8-visualizadores)
9. [Power BI](#9-power-bi)
10. [Lo que se hizo el 21 de octubre de 2026](#10-lo-que-se-hizo-el-21-de-octubre-de-2026)
11. [Recetas: "para hacer X necesito saber Y"](#11-recetas-para-hacer-x-necesito-saber-y)
12. [Glosario](#12-glosario)
13. [Seguridad, privacidad y buenas prácticas](#13-seguridad-privacidad-y-buenas-prácticas)

---

## 0. Mapa general del repositorio

```
ucuenca-sabe/
├── config/config.yaml            ← rutas base y parámetros (YAML)
├── src/                          ← código reutilizable (paquete Python)
│   ├── config.py                 ← carga el YAML, calcula rutas, clase Config
│   ├── ingestion/                ← descarga de datos (Kaggle)
│   ├── scrapers/                 ← extracción web (noticias, investigadores, organizaciones)
│   ├── processing/               ← transformaciones (ENEMDU, sentimiento de noticias)
│   └── utils/dspace_parser.py    ← parseo de metadatos de DSpace (biblioteca)
├── scripts/run_enemdu_pipeline.py← orquestador por línea de comandos (CLI)
├── notebooks/                    ← exploración y pipelines de docentes (Jupyter)
├── data/                         ← bronze / silver / gold (NO se sube a GitHub)
├── reports/                      ← auditorías JSON y CSV para Power BI
├── visualizacion/                ← sitio web estático (HTML + JSON)
│   ├── index.html                ← portada con enlaces a cada visualizador
│   ├── static/                   ← data.json (ENEMDU) y noticias/ (noticias)
│   └── scripts/                  ← generadores de los JSON del sitio
├── powerbi_ucuenca/ y empleabilidad_mvp.* ← proyectos de Power BI (formato PBIP)
├── .github/workflows/            ← automatización (scraping de noticias cada 6 h)
├── docs/                         ← documentación (esta guía, README del pipeline)
├── environment.yml               ← entorno conda reproducible
├── .env.example                  ← plantilla de secretos (el .env real NO se sube)
└── excel.py, generar_mapa.py     ← utilidades sueltas (plantilla Excel, mapa de investigadores)
```

**Idea central:** el código vive en `src/`; los datos viven en `data/` (que git ignora); lo que se publica en la web vive en `visualizacion/`. Los datos fluyen de izquierda a derecha: fuente externa → Bronze → Silver → Gold → JSON → página web.

---

## 1. Arquitectura medallón (Bronze / Silver / Gold)

### Qué es
Una forma de organizar los datos en **tres capas** según su nivel de limpieza, como las etapas de refinar un mineral.

| Capa | Analogía | Qué contiene | Ejemplo en el proyecto |
|---|---|---|---|
| **Bronze** | Mineral recién sacado de la mina | Datos crudos, tal como llegaron, sin tocar | CSV del INEC, Excel de GTH, CSV del scraper de noticias |
| **Silver** | Mineral lavado y clasificado | Datos limpios, con tipos correctos, unificados, a veces anonimizados | `enemdu_unificado.parquet`, `noticias_economia_silver.parquet` |
| **Gold** | Joya terminada | Datos agregados, listos para mostrar (KPIs, tasas) | `kpi_anual.parquet`, `empleabilidad_provincia.parquet` |

### Para qué sirve
- **Trazabilidad:** si una cifra del dashboard está mal, puedes rastrearla hacia atrás (Gold → Silver → Bronze) hasta el dato original.
- **Reproducibilidad:** borras Silver y Gold, vuelves a correr el código y obtienes lo mismo.
- **Privacidad:** el Bronze contiene datos personales (cédulas, nombres). **Por política del repo, `data/` entero está en `.gitignore`** (cumple LOPDP, la Ley Orgánica de Protección de Datos Personales). Solo se suben los resultados agregados que van a la web.

### Qué hay que saber
- Cada capa se escribe en su carpeta: `data/bronze/...`, `data/silver/...`, `data/gold/...`.
- **Nunca se edita Bronze a mano.** Si hay un error, se corrige en el código que genera Silver.
- Silver debe servir a varios casos de uso; los filtros analíticos específicos (por ejemplo "solo graduados") se aplican en Gold.
- Formato de archivo: **Parquet** (binario, comprimido, conserva tipos de dato) en vez de CSV. Ver glosario.

---

## 2. Configuración central

### Archivos
- [config/config.yaml](../config/config.yaml): define las rutas base (`data/bronze`, `data/silver`, `data/gold`) y datos como el dataset de Kaggle de ENEMDU.
- [src/config.py](../src/config.py): lee ese YAML y expone funciones y constantes.

### Cómo funciona
1. `get_project_root()` sube desde `src/` buscando una carpeta `config` o `.git`. Así el código funciona **sin importar desde dónde lo ejecutes**.
2. `_load_yaml_config()` lee `config/config.yaml` con `yaml.safe_load` y falla con un mensaje claro si no existe.
3. Define constantes (`BRONZE_DIR`, `SILVER_DIR`, `GOLD_DIR`...) y **crea las carpetas base automáticamente al importar** (`ensure_base_directories()`).
4. Funciones útiles:
   - `get_external_bronze_dir("noticias_economia")` → devuelve (y crea) `data/bronze/externas/noticias_economia`.
   - `get_domain_silver_dir("enemdu")` → devuelve (y crea) `data/silver/enemdu`.
5. La clase `Config` existe por compatibilidad con los notebooks de docentes: guarda rutas de archivos concretos (`GTH_FILE`, `CATRASTRO_DOCENTES`, `TESIS_SILVER`...) y constantes de negocio (`FUZZY_THRESHOLD = 85`, `AÑO_CORTE_TESIS = 2020`).

### Librerías
- **PyYAML** (`import yaml`): leer el YAML.
- **python-dotenv** (`from dotenv import load_dotenv`): cargar variables secretas desde el archivo `.env`.
- **pathlib** (estándar): manejar rutas de forma portable (Windows/Linux).

### Qué hay que saber
- **Todo script que haga `from config import ...` necesita `pyyaml` y `python-dotenv` instalados.** Por esto falló el workflow de noticias: no los instalaba (ver sección 7).
- Importar `config` tiene un efecto secundario: crea carpetas. Es intencional.

---

## 3. Entorno y librerías

El entorno se define en [environment.yml](../environment.yml) (conda, Python 3.11.9).

| Librería | Para qué se usa aquí | Dónde |
|---|---|---|
| **pandas** | Tablas (DataFrames): leer, limpiar, agrupar | Todo el procesamiento |
| **numpy** | Cálculo numérico, valores `NaN` | ENEMDU Silver/Gold |
| **pyarrow** | Leer/escribir Parquet (lo usa pandas por debajo) | Silver y Gold |
| **openpyxl** | Leer/escribir Excel `.xlsx` | Docentes, `excel.py` |
| **pyreadstat** | Leer archivos `.sav` (formato SPSS del INEC) | Notebook de revisión de etiquetas |
| **selenium** | Controlar un navegador Chrome para scrapear páginas dinámicas | Scrapers de investigadores y organizaciones |
| **requests** | Pedir páginas web por HTTP (rápido, sin navegador) | Scraper de noticias |
| **beautifulsoup4** | Leer el HTML y extraer elementos con selectores CSS | Scraper de noticias |
| **kaggle** (vía pip, `>=2.2.4`) | Descargar el dataset de ENEMDU | `kaggle_downloader.py` |
| **thefuzz** + **python-levenshtein** | Comparar textos "parecidos" (coincidencia difusa de nombres) | Notebook de fuzzy matching |
| **ipykernel** | Ejecutar notebooks en VS Code | Notebooks |
| **python-dotenv**, **pyyaml** | Configuración y secretos | `src/config.py` |

En el navegador (visualizadores) se usan, por CDN: **Tailwind CSS** (estilos), **Chart.js** y **Plotly.js** (gráficos), **D3.js** (mapa de investigación).

### Cómo recrear el entorno
```bash
conda env create -f environment.yml
conda activate ucuenca-sabe
```

### Error típico en Windows
Si `pip install` instala en un Python y `python` ejecuta otro, aparece `ModuleNotFoundError`. Solución: usa siempre `python -m pip install ...` para instalar en el mismo intérprete que ejecuta tu código.

---

## 4. Pipeline ENEMDU

### Qué es
**ENEMDU** = Encuesta Nacional de Empleo, Desempleo y Subempleo, del **INEC** (Instituto Nacional de Estadística y Censos de Ecuador). Es una encuesta por muestreo; cada fila es una persona. Aquí se usan los años **2021-2025** para calcular indicadores de **empleabilidad** de graduados universitarios y **sobrecalificación**.

### Flujo completo
```
Kaggle ──► Bronze ──► Analizador ──► Silver ──► Gold ──► data.json ──► Dashboard web
 (descarga)  (CSV + XLSX)  (auditoría)  (unificado)  (agregados)   (generador)   (HTML)
                                                       └──► reports/powerbi/*.csv ──► Power BI
```

### 4.1 Ingesta: `src/ingestion/kaggle_downloader.py`
- Descarga el dataset (`kmichelle/enemdu-ecuador-microdatos-anuales-personas`) usando la API de Kaggle y lo organiza en `data/bronze/externas/enemdu`.
- Necesita el token en `.env` (`KAGGLE_API_TOKEN`, ver `.env.example`).
- Notebook asociado: `notebooks/01_download_kaggle_enemdu.ipynb`.

### 4.2 Utilidades de entrada/salida: `src/processing/io_utils.py`
Es **la única capa que toca archivos "en crudo"**, para que el resto no repita lógica.
- `ENEMDUPaths`: resuelve dónde está cada carpeta (lee `config.yaml` y, si no hay, usa la convención por defecto).
- `sniff_csv` / `read_csv_smart`: **detectan automáticamente** codificación (UTF-8 vs Latin-1), separador (`;` vs `,`) y decimal (coma vs punto). El INEC cambia el formato entre publicaciones; fijar `sep=";"` rompería algunos años.
- `read_dictionary_xlsx` y `parse_value_labels`: leen el diccionario de variables (Excel) y convierten textos como `1=Hombre; 2=Mujer` en un diccionario Python.
- `get_logger`, `save_json`: registro de mensajes y guardado de reportes.

### 4.3 Mapeos y reglas: `src/processing/enemdu_mappings.py`
El "cerebro de reglas" del pipeline:
- **`COLUMN_ALIASES`**: cada variable "canónica" (por ejemplo `ingreso_laboral`) tiene una lista de nombres posibles (`ingrl`, ...). Se resuelve **por año** contra la cabecera real del CSV, porque el INEC renombra variables entre años.
- **`FALLBACK_*`**: tablas de respaldo (sexo, área, nivel de instrucción, condición de actividad) que solo se usan si el diccionario del año no es interpretable.
- **`EDU_PATTERNS` / `CONDACT_PATTERNS`**: expresiones regulares para clasificar etiquetas de texto.
- **`PROVINCIAS_EC`**: código → nombre de provincia.
- **`NIVEL_INSTRUCCION_GRADUADO_RULE`**: regla para decir quién es "graduado superior" **por código numérico**, no por texto (el 2023 usa otra variable, `nnivins`).
- **`GRUPOS_REQUIEREN_SUPERIOR = (1,2,3)`**: grandes grupos CIUO-08 que sí exigen título universitario; los grupos 4-9 se consideran "sobrecalificación".

### 4.4 Analizador de esquemas: `enemdu_schema_analyzer.py` (Objetivo 1)
Antes de construir Silver, **audita** lo que llegó:
1. Inventaría los archivos de Bronze.
2. Compara el esquema declarado (diccionario) contra el real (CSV).
3. Detecta columnas comunes a todos los años y columnas específicas de un año.
4. Mide calidad en una muestra (nulos, duplicados).
5. `resolve_critical()`: indica si cada variable crítica está `completa`, `⚠️ parcial` o `❌ ausente`.
6. Guarda un reporte JSON con fecha en `reports/schemas/`.

### 4.5 Silver: `enemdu_silver_builder.py` (Objetivo 2)
Transformaciones, en orden:
1. **Resolver esquema por año** con los alias.
2. **Leer solo las columnas necesarias** (`usecols`) para ahorrar memoria.
3. **Limpiar tipos** y convertir códigos de no respuesta (`999999`, `99`, `-1`) a `NaN`.
4. **Decodificar** códigos a etiquetas leyendo el diccionario del año.
5. **Derivar** variables (por ejemplo grupo de edad).
6. **Unificar 2021-2025** en una sola tabla; las columnas que no existen en un año se agregan como `NaN` (**nunca como 0**: "no medido" ≠ "cero").
7. **Validar** y guardar `data/silver/enemdu/enemdu_unificado.parquet`.

### 4.6 Gold: `enemdu_gold_builder.py` (Objetivo 3)
Aquí se hacen los indicadores. Definiciones:
- **PET** (Población en Edad de Trabajar): 15 años o más.
- **PEA** (Población Económicamente Activa): ocupados + desempleados de 15+.
- **Tasa de desempleo** = desempleados / PEA.
- **Tasa de empleo adecuado** = empleo adecuado/pleno / PEA.
- **Graduado superior**: nivel "Superior no universitaria", "Superior universitaria" o "Post-grado".
- **Sobrecalificación**: graduado superior **ocupado** en una ocupación cuyo gran grupo CIUO-08 es 4-9.
- **Ponderación**: todo se calcula con `fexp` (factor de expansión) y se reporta `n_muestral` y `confiable` (n ≥ 30).

Tablas Gold generadas (en `data/gold/enemdu/`): `kpi_anual`, `empleabilidad_provincia`, `empleabilidad_sexo_edad`, `graduados_rama_actividad`, `sobrecalificacion_ocupacion`, `comparativo_nivel_instruccion`, `empleabilidad_graduados`, `cubo_empleabilidad`, `cubo_ocupacion_graduados`. También exporta CSV a `reports/powerbi/` (UTF-8 con BOM, separador `;`, decimal `,`).

**Regla crítica de `segmento`:** algunas tablas traen la columna `segmento` con `general` y `educacion_superior`. Están **anidadas** (superior ⊂ general), **no** son una partición. **Nunca sumes ni promedies filas de ambos segmentos juntas**; filtra por segmento primero.

### 4.7 Orquestador: `scripts/run_enemdu_pipeline.py`
Línea de comandos (módulo `argparse`):
```bash
python scripts/run_enemdu_pipeline.py --all                 # auditoría + Silver + Gold
python scripts/run_enemdu_pipeline.py --audit               # solo auditoría
python scripts/run_enemdu_pipeline.py --silver --gold --years 2024 2025
python scripts/run_enemdu_pipeline.py --all --sample 50000  # prueba rápida con muestra
```

### 4.8 Del Gold a la web: `visualizacion/scripts/generate_dashboard_data.py`
Lee los parquet de Gold y escribe `visualizacion/static/data.json`, con tres módulos: `enemdu` (toda la PEA), `empleabilidad_superior` (graduados) y `sobrecalificacion`. El dashboard `MVP_dashboard_empleabilidad.html` solo lee ese JSON.
- Se ejecuta **desde la carpeta `visualizacion/scripts`** (usa rutas relativas `../../data/gold/enemdu`).
- En Windows, si falla con `UnicodeEncodeError` por los emojis, corre: `PYTHONIOENCODING=utf-8 python generate_dashboard_data.py`.

### Qué hay que saber (ENEMDU)
| Concepto | Por qué importa |
|---|---|
| Datos de encuesta no se promedian "a ojo" | Cada persona representa a muchas otras (`fexp`); sin ponderar, las tasas no coinciden con el INEC |
| Tasas no se promedian | En Power BI usa `SUM(numerador)/SUM(denominador)`, no `AVERAGE(tasa)` |
| `p01` es parentesco, no ID | No sirve para deduplicar personas |
| Dialecto del CSV cambia por año | Por eso hay detección automática |

---

## 5. Pipeline de docentes e investigación

Esta parte **no está tan formalizada** como ENEMDU: vive en notebooks que escriben directo en `data/silver/` (sin versionado por fecha).

### 5.1 Fuentes (Bronze interno, restringido)
| Archivo | Contenido |
|---|---|
| `MATRIZ_ENVIADA_2.xlsx` | Matriz de GTH (Gestión del Talento Humano) |
| `docentes_titulo_unesco.xlsx` | Analítica: docentes con título y campo UNESCO |
| `BIBLIOTECA_DSPACE.xlsx` | Producción de la biblioteca (hojas: tesis, art_docentes, publicaciones) |
| `investigadores_raw.xlsx` | Resultado del scraper del portal de investigación |

### 5.2 Scrapers con Selenium
- `src/scrapers/investigacion_scraper_final.py`: recorre las páginas de `investigacion.ucuenca.edu.ec/es/persons/`. **Modo manual:** el sitio pide CAPTCHA; el navegador se abre y tú lo resuelves a mano. Guarda en `data/bronze/investigacion/`.
- `src/scrapers/organizaciones_scraper.py`: extrae la jerarquía Facultades → Departamentos → Grupos de Investigación.
- **Selenium vs requests:** Selenium abre un Chrome real (sirve para páginas con JavaScript o CAPTCHA, pero es lento). `requests` solo baja HTML (rápido, pero no ejecuta JavaScript).

### 5.3 Notebook `01_ingesta_gth_pure.ipynb`
Une GTH + Analítica en el **catastro de docentes** (`data/silver/catastro_docentes.parquet`), normalizando la cédula (`CEDULA_NORM`).

### 5.4 Parser de DSpace: `src/utils/dspace_parser.py`
`ejecutar_parseo_dspace()` convierte el texto de metadatos de DSpace (el repositorio de la biblioteca) en columnas: autores (`AUTOR_N`), IDs (`ID_AUTOR_N`, `ID_DIRECTOR_TESIS`), factores de impacto, etc. Usa expresiones regulares (`re`) y balancea pares autor/ID para evitar registros huérfanos.

### 5.5 Notebook `02_fuzzy_matching_dspace.ipynb`: coincidencia en dos etapas
Objetivo: saber **qué docentes produjeron cada tesis/artículo/publicación**.
- **Etapa 1 (exacta):** si el registro trae la cédula del autor/director, se une por cédula exacta. Cubre ~68 % de artículos, ~65 % de publicaciones, casi 0 % de tesis.
- **Etapa 2 (difusa):** compara nombres con `thefuzz.fuzz.token_sort_ratio` (ignora el orden de las palabras: "Pérez, Juan" ≈ "JUAN PEREZ").
  - Se **corrobora** con el campo amplio UNESCO: si el registro y el docente discrepan, el candidato se descarta aunque el nombre sea muy parecido.
  - Umbrales: puntaje ≥ 90 → `fuzzy_nombre` (aceptado); entre 80 y 90 con corroboración → `fuzzy_revisar` (aceptado pero para revisión manual).
- Columnas resultantes: `CEDULA_MATCH`, `METODO_MATCH_DOCENTE`, `FUZZY_SCORE`.
- **Límite real:** el catastro solo tiene docentes **actuales** (1175 personas); un director de tesis que ya se retiró nunca coincidirá. Cobertura de tesis medida: ~27 %. Mejorarla requiere ampliar la fuente de datos, no ajustar los umbrales.

### 5.6 Utilidades sueltas
- `generar_mapa.py`: lee `silver_catastropure.xlsx` y genera `visualizacion/mapa_investigacion.html` (visualización con D3). Tiene **rutas absolutas fijas** en la parte superior; hay que editarlas si cambia la ubicación.
- `excel.py`: construye una plantilla Excel con formato institucional (colores, validaciones de datos desplegables, hoja de instrucciones) usando `openpyxl`.

---

## 6. Pipeline de noticias de economía

### Flujo
```
Primicias + El Universo ──► scraper ──► Bronze CSV ──► sentimiento ──► Silver parquet ──► generador ──► JSON por mes ──► dashboard
```

### 6.1 Scraper: `src/scrapers/noticias_economia_scraper.py`
- Pide la sección Economía de Primicias y El Universo con `requests` y extrae titulares con `BeautifulSoup` mediante **selectores CSS** (`article`, `h2.c-article__title a`, `div.card-content`...).
- `parse_primicias` y `parse_eluniverso` son funciones puras (reciben HTML, devuelven lista de diccionarios), por eso se pueden probar sin internet con `_self_test()` y fragmentos de HTML congelados.
- **Deduplica por URL** (`drop_duplicates(subset="url")`): cada corrida solo agrega noticias nuevas.
- `fecha_publicacion()`: entra a cada artículo nuevo y lee la etiqueta `<meta property="article:published_time">`.
- Guarda en `data/bronze/externas/noticias_economia/noticias_economia.csv`.
- **Fragilidad conocida:** si un sitio cambia su HTML, los selectores dejan de encontrar titulares. Es el primer lugar donde mirar si de pronto llegan 0 noticias.

### 6.2 Sentimiento: `src/processing/noticias_sentimiento.py`
- **Método:** léxico (lista) de palabras positivas y negativas. Se quitan acentos, se cuentan coincidencias por palabra completa y `score = positivas − negativas` → `positivo`, `negativo` o `neutro`.
- **Limitación honesta** (marcada con `ponytail:` en el código): no entiende negaciones ni sarcasmo ("no hubo crecimiento" cuenta como positivo). El upgrade posible es un modelo entrenado (`pysentimiento`), que pesa ~1 GB y hoy no se justifica para ~40 titulares por corrida.
- Escribe `data/silver/noticias_economia/noticias_economia_silver.parquet`.

### 6.3 Generador: `visualizacion/scripts/generate_noticias_data.py`
- Clasifica cada titular en un **sector productivo** por palabras clave (Energía y minería, Finanzas, Agro y comercio exterior, Industria, Turismo, Telecom, Vivienda; el resto "Otros").
- Calcula agregados (`agregados()`): total, por fuente, sentimiento, sector, día.
- Escribe en `visualizacion/static/noticias/`:
  - `resumen.json` (liviano): agregados globales + lista de meses.
  - `noticias_AAAA-MM.json`: titulares y agregados de ese mes (**mes de captura**, no de publicación, para que una nota vieja enlazada en portada no cree un mes suelto).

### 6.4 Dashboard: `visualizacion/noticias_economia_dashboard.html`
- Al abrirse baja `resumen.json` y el mes más reciente; los demás meses se descargan **solo cuando se eligen** en el selector "Periodo".
- La tabla de abajo muestra **solo los titulares del día** (hora de Ecuador, `America/Guayaquil`); si aún no hay de hoy, muestra la última fecha disponible.
- `fetch(..., { cache: 'no-store' })` evita que el navegador sirva una versión vieja.

### Por qué JSON por mes (escalabilidad)
Con ~40 noticias/día, un solo JSON crecería ~10 MB por año y la página lo bajaría completo. Por mes: la carga inicial siempre es pequeña, y cada commit del bot modifica un solo archivo (el del mes actual), con lo que el historial de git crece mucho menos.

---

## 7. Automatización con GitHub Actions

Archivo: [.github/workflows/noticias_economia.yml](../.github/workflows/noticias_economia.yml).

### Conceptos
- **Workflow:** receta en YAML que GitHub ejecuta en un servidor Linux temporal (*runner*).
- **Trigger:** `schedule` con `cron: "0 */6 * * *"` (minuto 0 de cada 6 horas, **en UTC**) y `workflow_dispatch` (botón "Run workflow" manual).
- **Permisos:** `contents: write` para que el bot pueda hacer commit.

### Pasos del job `scrape`
1. `actions/checkout@v4`: baja el repositorio.
2. `actions/setup-python@v5`: instala Python 3.11.
3. `pip install requests beautifulsoup4 pandas pyarrow pyyaml python-dotenv`.
4. **Reconstruir Bronze:** como `data/` no se versiona, el runner nuevo no tiene histórico; se reconstruye desde los JSON mensuales ya publicados.
5. Scraper → Sentimiento → Generador de JSON.
6. **Commit y push** como `github-actions[bot]` solo si cambió algo en `visualizacion/static/noticias`.

### ¿Hay que hacer push para que funcione?
**No.** Corre solo en los servidores de GitHub, aunque tu computador esté apagado. Tú haces push únicamente cuando cambies código.

### Cosas que hay que saber
- **`git pull` antes de tus propios cambios:** el bot sube commits a `main`; si no haces pull, tu push se rechazará.
- **Correo de fallo:** GitHub avisa por correo cada vez que un workflow falla. Para ver el motivo: pestaña **Actions** → ejecución en rojo → paso fallido → log.
- **Inactividad:** en repos públicos, GitHub puede desactivar workflows programados tras 60 días sin actividad.
- **Retrasos:** el cron de GitHub no es exacto; puede demorar varios minutos.
- **Un push del bot con `GITHUB_TOKEN` no dispara otros workflows.** Si GitHub Pages se publica "desde la rama", el commit sí se publica; si usaras un workflow de despliegue aparte, habría que dispararlo explícitamente.
- **Incidente 21/10/2026:** el workflow fallaba (probablemente desde su creación) con `ModuleNotFoundError: No module named 'yaml'` porque `src/config.py` importa `yaml` y `dotenv` y el `pip install` no los incluía. Se agregó `pyyaml python-dotenv`.

---

## 8. Visualizadores

Todos están en `visualizacion/` y son **páginas estáticas** (HTML + JavaScript en el navegador). No hay servidor: GitHub Pages solo entrega archivos.

| Página | Qué muestra | De dónde saca datos |
|---|---|---|
| `index.html` | Portada con enlaces a todo | — |
| `MVP_dashboard_empleabilidad.html` | ENEMDU: mercado laboral, empleabilidad de graduados, sobrecalificación | `static/data.json` |
| `noticias_economia_dashboard.html` | Sentimiento y cobertura de noticias | `static/noticias/*.json` |
| `mapa_investigacion.html` | Mapa de investigadores (D3) | datos incrustados (los genera `generar_mapa.py`) |
| `catastro_docentes.html`, `oferta_posgrados.html` | Tableros de Power BI incrustados con `<iframe>` | Power BI Service |
| `20260611_hoja_de_ruta_...html` | Documento de hoja de ruta | estático |
| `presentaci_n_ejecutiva_arquitecturamedallon.html` | Presentación de la arquitectura | estático |

### Cómo funciona un dashboard (patrón común)
1. La página carga con `<script src="https://cdn...">` las librerías (Tailwind, Chart.js...).
2. `fetch('static/algo.json')` descarga el JSON.
3. Una función `render(data)` construye el HTML con plantillas de texto (`` `...${valor}...` ``) y dibuja los gráficos sobre elementos `<canvas>`.
4. Los filtros (`<select>`) vuelven a llamar a `render` o a la función de dibujo.

### Botón "← Inicio"
Un enlace fijo (`position: fixed`, abajo a la izquierda) en los visualizadores propios que apunta a `index.html`. Catastro y Posgrados ya tienen su propio "← Volver" en la cabecera.

### Probar en tu computador
Los `fetch` no funcionan abriendo el archivo con doble clic (`file://`). Levanta un servidor local:
```bash
cd visualizacion
python -m http.server 8000
# abre http://localhost:8000/index.html
```

### Si ves datos viejos o un 404 en producción
Casi siempre es **caché** del navegador o de Pages: recarga con **Ctrl+F5**. Revisa en Actions que el despliegue de Pages haya terminado.

### Identidad visual
Seguir la **Guía de Estilo DPE-GE-009**: el nombre es siempre `UCuenca-SABE!`; toda cifra pública lleva fuente y año; colores institucionales (azul marino `#0B2341`/`#003156`).

---

## 9. Power BI

- `empleabilidad_mvp.pbip` y `powerbi_ucuenca/` son proyectos en formato **PBIP** (carpetas de texto: modelo semántico en TMDL + definición de informe en JSON), pensados para versionarse en git.
- ENEMDU entra a Power BI desde `reports/powerbi/*.csv` (UTF-8 con BOM, `;` y coma decimal, para que Excel/Power BI en español lo lean bien).
- **Regla DAX:** las tasas se calculan `DIVIDE(SUM(numerador), SUM(denominador))`; promediar tasas por fila da resultados incorrectos.
- El tema de color está en `powerbi_ucuenca/Tema_UCuenca_2026.json.json`.
- Los tableros publicados se incrustan en la web con `<iframe>` (enlace "publicar en la web" de Power BI Service). **Ese enlace es público**: cualquier persona con la URL ve el tablero.

---

## 10. Lo que se hizo el 21 de octubre de 2026

1. **Diagnóstico del correo de GitHub:** workflow de noticias fallando por dependencias faltantes → se agregaron `pyyaml python-dotenv`.
2. **Revisión de todos los visualizadores** con un navegador automatizado (Playwright + Edge): sin errores de JavaScript ni `NaN` en los dashboards ENEMDU; las tres vistas probadas.
3. **Noticias al día:** se corrió el scraper local (83 noticias acumuladas, incluidas las del 21/10).
4. **Tabla del día + filtro por mes** en el dashboard de noticias.
5. **Escalabilidad:** el JSON único se reemplazó por `resumen.json` + un archivo por mes; el workflow y el generador se adaptaron.
6. **Botón "← Inicio"** en los visualizadores propios.
7. **Esta guía.**

---

## 11. Recetas: "para hacer X necesito saber Y"

### Agregar un nuevo medio de noticias
Saber: HTML básico, selectores CSS, `BeautifulSoup`.
1. Inspecciona la página (clic derecho → Inspeccionar) y encuentra el elemento de cada titular.
2. En `noticias_economia_scraper.py` crea `parse_nuevomedio(html)` (devuelve lista de dicts con `fuente`, `titulo`, `resumen`, `url`) y agrégalo a `SOURCES`.
3. Agrega un fragmento de HTML real a `_self_test()`.
4. Corre el scraper local y revisa la cuenta.

### Cambiar las palabras de sentimiento o los sectores
Saber: listas y diccionarios de Python.
Edita `POSITIVE_WORDS`/`NEGATIVE_WORDS` (`noticias_sentimiento.py`) o `SECTORES` (`generate_noticias_data.py`). Los prefijos de sector se buscan sin tildes y en minúscula.

### Cambiar la frecuencia del scraping
Saber: sintaxis **cron** (`min hora día mes díasemana`, en UTC).
Edita `cron:` en el workflow. Ejemplo: `"0 */3 * * *"` = cada 3 horas. Ecuador es UTC−5.

### Agregar un año nuevo de ENEMDU
Saber: estructura del dataset en Kaggle y `COLUMN_ALIASES`.
1. Sube/descarga el año a Bronze.
2. Corre `python scripts/run_enemdu_pipeline.py --audit` y revisa `resolve_critical()`.
3. Agrega los alias nuevos en `enemdu_mappings.py` si hay variables `parcial`/`ausente`.
4. Corre `--silver --gold`, luego `generate_dashboard_data.py`.
5. Actualiza los textos "2021-2025" de los HTML.

### Agregar un nuevo indicador a Gold
Saber: pandas `groupby`, ponderación con `fexp`.
Sigue el patrón de `_metric_table` en `enemdu_gold_builder.py`: agrega numerador y denominador **ponderados**, calcula la tasa al final, reporta `n_muestral`.

### Agregar un nuevo dominio de datos (nuevo pipeline)
Saber: patrón medallón. Usa ENEMDU como plantilla:
`get_external_bronze_dir("mi_fuente")` → scraper/ingesta → `get_domain_silver_dir("mi_fuente")` → builder Silver → builder Gold → generador de JSON → HTML.

### Agregar un visualizador nuevo al sitio
Saber: HTML/JS básico.
1. Crea el HTML en `visualizacion/` (copia la estructura de `noticias_economia_dashboard.html`).
2. Agrega el botón "← Inicio" (enlace a `index.html`).
3. Agrega una fila en `index.html`.

### Mostrar un tablero de Power BI en la web
Saber: Power BI Service.
Publica el informe → Archivo → Insertar informe → "Publicar en la web" → copia la URL → úsala como `src` del `<iframe>` (ver `catastro_docentes.html`).

### Ver por qué falló el workflow
Saber: dónde mirar. GitHub → **Actions** → ejecución fallida → expandir el paso en rojo. Los errores más comunes: módulo faltante (`pip install`), selector que ya no encuentra nada (el medio cambió su HTML), `403` (el medio bloquea la IP), o falla del `git push`.

### Probar algo sin esperar al bot
Saber: ejecutar localmente los tres pasos, desde la raíz:
```bash
python src/scrapers/noticias_economia_scraper.py
python src/processing/noticias_sentimiento.py
cd visualizacion/scripts && python generate_noticias_data.py
```

### Subir cambios a GitHub
Saber: flujo básico de git.
```bash
git pull                      # traer lo que subió el bot
git status                    # ver qué cambió
git add <archivos>
git commit -m "descripción"
git push
```

---

## 12. Glosario

| Término | Definición |
|---|---|
| **API** | Forma programática de pedir datos a un servicio (por ejemplo Kaggle). |
| **Alias (de columna)** | Nombre alternativo de una variable; el INEC la renombra entre años. |
| **Bot (github-actions[bot])** | Usuario automático que hace commits desde un workflow. |
| **Bronze / Silver / Gold** | Capas de datos: crudo / limpio / agregado. |
| **Caché** | Copia guardada por el navegador; puede mostrar una versión vieja de una página. |
| **CDN** | Servidor que entrega librerías (Chart.js, Tailwind) por internet. |
| **CAPTCHA** | Prueba para distinguir humanos de robots; obliga a un scraping manual. |
| **CIUO-08** | Clasificación Internacional Uniforme de Ocupaciones (OIT). Los grandes grupos 1-3 requieren formación superior; 4-9, no. |
| **CIIU-4** | Clasificación Industrial Internacional Uniforme (ramas de actividad). |
| **Commit / Push / Pull** | Guardar un cambio en git / subirlo a GitHub / traer lo que otros subieron. |
| **Cron** | Sintaxis para programar tareas repetitivas. |
| **CSS (selector)** | Patrón para identificar elementos HTML (`h2.titulo a`). |
| **DAX** | Lenguaje de fórmulas de Power BI. |
| **DataFrame** | Tabla de pandas. |
| **DSpace** | Software del repositorio institucional de la biblioteca (tesis, artículos). |
| **ENEMDU** | Encuesta Nacional de Empleo, Desempleo y Subempleo (INEC). |
| **Fexp / factor de expansión** | Cuántas personas de la población representa cada fila de la encuesta. |
| **Fuzzy matching** | Coincidencia aproximada de textos (nombres parecidos). |
| **Gold manifest** | JSON con el detalle de lo generado en Gold (en `reports/schemas/`). |
| **GTH** | Gestión del Talento Humano de la Universidad. |
| **HTTP 403 / 404** | Acceso prohibido / no encontrado. |
| **INEC** | Instituto Nacional de Estadística y Censos. |
| **JSON** | Formato de texto para datos estructurados; lo leen los dashboards. |
| **Léxico (sentimiento)** | Lista de palabras con polaridad usada para clasificar un texto. |
| **LOPDP** | Ley Orgánica de Protección de Datos Personales. |
| **Medallón** | Arquitectura de datos por capas Bronze/Silver/Gold. |
| **n muestral / confiable** | Cantidad de observaciones sin expandir; se marca confiable si n ≥ 30. |
| **NaN** | "No es un número": valor faltante en pandas. |
| **Parquet** | Formato columnar comprimido que conserva tipos; más rápido y ligero que CSV. |
| **PBIP** | Formato de proyecto de Power BI basado en carpetas de texto. |
| **PEA / PET** | Población Económicamente Activa / en Edad de Trabajar (15+). |
| **Pages (GitHub Pages)** | Hosting gratuito de sitios estáticos desde el repositorio. |
| **Runner** | Servidor temporal donde GitHub ejecuta un workflow. |
| **Scraping** | Extraer datos automáticamente de páginas web. |
| **Sobrecalificación** | Graduado superior ocupado en un empleo que no exige título. |
| **Tasa de desempleo** | Desempleados / PEA. |
| **Tasa de empleo adecuado** | Ocupados con empleo adecuado/pleno / PEA. |
| **UNESCO (campo amplio)** | Clasificación de áreas de conocimiento usada para corroborar coincidencias. |
| **UTC** | Hora universal; Ecuador continental es UTC−5. |
| **Workflow** | Receta de automatización en GitHub Actions. |
| **YAML** | Formato de configuración legible (`config.yaml`, workflows). |

---

## 13. Seguridad, privacidad y buenas prácticas

- **Nunca subas** `.env`, cédulas, nombres de docentes con datos personales ni la carpeta `data/`. El `.gitignore` ya bloquea `data/`, `*.csv`, `*.xlsx`, `*.parquet`, `*.sav` y `*.json` (con excepciones explícitas para `config/`, `visualizacion/static/data.json` y `visualizacion/static/noticias/*.json`).
- **Cuidado con los CSV/Excel de la raíz** (`investigadores_ucuenca.csv`, `matriz_contratos_ucuencav1.xlsx`...): están ignorados por patrón, pero conviene mantener los datos personales solo dentro de `data/bronze/`.
- **Secretos** (token de Kaggle): solo en `.env`, que nunca se versiona; `.env.example` es la plantilla sin valores.
- **Enlaces públicos de Power BI** ("publicar en la web"): cualquier persona con la URL ve el tablero; úsalos solo con datos agregados.
- **Antes de publicar** (verificación del README): nombre `UCuenca-SABE!`, sin términos retirados, cifras con fuente y año, afirmaciones proporcionales a la evidencia.
- **Scraping responsable:** respeta los términos de cada sitio, no abuses de la frecuencia y usa un `User-Agent` identificable.
- **Mantén `git pull` como hábito** antes de empezar a trabajar: el bot modifica el repositorio mientras duermes.

---

*Guía elaborada el 21 de octubre de 2026 a partir del contenido del repositorio. Si el código cambia, actualiza la sección correspondiente.*
