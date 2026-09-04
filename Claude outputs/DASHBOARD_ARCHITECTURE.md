# 🏗️ Arquitectura Técnica — Dashboard Empleabilidad ENEMDU

**Proyecto:** UCuenca-SABE | Sistema de Inteligencia Territorial  
**Componente:** MVP Dashboard de Empleabilidad  
**Versión:** 1.0  
**Fecha:** 2026-09-04  

---

## 📐 Visión general de la arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     NOTEBOOK ENEMDU                          │
│            (01_download_kaggle_enemdu.ipynb)                │
│  Bronze (CSVs INEC) → Silver (Unificado) → Gold (Agregados) │
└────────────────────────┬────────────────────────────────────┘
                         │
                    (Parquet files)
                         │
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼─────────────┐    ┌──────────▼────────┐
    │  Gold Parquet    │    │  (Otros datos)    │
    │  - kpi_anual     │    │  - provincia      │
    │  - sobrecal.     │    │  - rama_actividad │
    │  - ...           │    │  - sexo_edad      │
    └────┬─────────────┘    └──────────────────┘
         │
         │ (Python 3 + Pandas + PyArrow)
         │
    ┌────▼────────────────────────────────────┐
    │   generate_dashboard_data.py             │
    │  (Transformación Gold → JSON limpio)    │
    │  - Extrae KPIs                          │
    │  - Construye timeline                   │
    │  - Estructura filtros dinámicos         │
    └────┬─────────────────────────────────────┘
         │
         │ JSON (aplicación, sin perder datos)
         │
    ┌────▼─────────────────────────────────────┐
    │   static/data.json                       │
    │  {                                       │
    │    "metadata": {...},                    │
    │    "modules": {                          │
    │      "enemdu": {...},                    │
    │      "sobrecalificacion": {...}          │
    │    }                                     │
    │  }                                       │
    └────┬─────────────────────────────────────┘
         │
         │ (HTTP GET, carga local)
         │
    ┌────▼───────────────────────────────────────┐
    │  MVP_dashboard_empleabilidad.html           │
    │  (Vue.js-style vanilla JavaScript)         │
    │  - Landing page (Landing view)             │
    │  - Dashboard view (Modular)                │
    │  - Módulo ENEMDU                           │
    │  - Módulo Sobrecalificación                │
    │  - Chart.js + Plotly.js                    │
    └────┬────────────────────────────────────────┘
         │
         └─────► Navegador (sin dependencias backend)
```

---

## 🔄 Flujo de datos completo

### **1. Generación de datos (Python)**

**Script:** `visualizacion/scripts/generate_dashboard_data.py`

```python
# Entrada
data/gold/enemdu/
├── kpi_anual.parquet                    # 5 años, 18 columnas
├── empleabilidad_provincia.parquet      # 150 filas (30 prov × 5 años)
├── empleabilidad_sexo_edad.parquet      # Segmentación demográfica
├── graduados_rama_actividad.parquet     # Sectores económicos
└── sobrecalificacion_ocupacion.parquet  # 45 filas (9 CIUO × 5 años)

# Procesamiento
1. Cargar con pd.read_parquet()
2. Extraer KPIs del último año
3. Construir timeline 2021-2025
4. Agregar por provincia y sector
5. Generar filtros dinámicos

# Salida
visualizacion/static/data.json (~87 KB)
├── metadata (timestamp, versión, fuente)
└── modules
    ├── enemdu
    │   ├── kpi_latest (año actual)
    │   ├── timeline (línea temporal)
    │   ├── por_provincia (ranking)
    │   ├── por_rama (sectores)
    │   └── filtros_disponibles
    └── sobrecalificacion
        ├── tasa_general_por_anio
        ├── por_ocupacion_2025
        └── ciuo_mapping
```

**Ventajas:**
- ✅ Determinístico: mismo input → mismo output
- ✅ Trazable: código Python documentado
- ✅ Auditible: cada transformación es explícita
- ✅ Reproducible: ejecuta script, obtiene datos frescos

---

### **2. Consumo de datos (JavaScript)**

**Archivo:** `visualizacion/MVP_dashboard_empleabilidad.html`

```javascript
// Carga al iniciar
fetch('static/data.json')
  .then(r => r.json())
  .then(data => {
    dashboardData = data;
    populateFilters();      // Lee filtros_disponibles
    renderContent();        // Pinta módulos
  });

// Cuando usuario elige módulo
openDashboard('enemdu')
  → renderEnemduModule(data.modules.enemdu)
    → Actualiza KPIs
    → Dibuja gráficos (Plotly)
    → Puebla tabla de datos

// Cuando cambian filtros (futuro)
applyFilters()
  → Filtra datos en memoria
  → Re-dibuja gráficos
```

**Ventajas:**
- ✅ Client-side: sin servidor backend
- ✅ Rápido: JSON cacheado en navegador
- ✅ Offline-capable: funciona sin conexión (tras primer carga)
- ✅ Actualizable: recargar página → nuevos datos

---

## 🗂️ Estructura del JSON

### Módulo ENEMDU

```json
{
  "enemdu": {
    "title": "Mercado Laboral ENEMDU — Contexto Nacional (2021-2025)",
    "kpi_latest": {
      "year": 2025,
      "tasa_desempleo": 3.5,
      "tasa_empleo_adecuado": 42.3,
      "tasa_subempleo": 18.2,
      "ingreso_laboral_medio": 1028.01,
      "n_muestral": 21140,
      "poblacion_expandida": 8234567.89
    },
    "timeline": {
      "years": [2021, 2022, 2023, 2024, 2025],
      "tasa_desempleo": [4.2, 4.1, 3.8, 3.6, 3.5],
      "tasa_empleo_adecuado": [40.1, 41.2, 41.8, 42.0, 42.3],
      "tasa_subempleo": [19.5, 19.2, 18.8, 18.5, 18.2],
      "tasa_sobrecalificacion": [12.1, 11.8, 11.5, 11.2, 11.0]
    },
    "por_provincia": [
      {
        "provincia": "Azuay",
        "tasa_desempleo": 3.2,
        "tasa_empleo_adecuado": 44.1,
        "tasa_sobrecalificacion": 10.8,
        "ingreso_laboral_medio": 1006.02,
        "n_muestral": 1840
      },
      // ... 29 provincias más
    ],
    "por_rama": [
      {
        "rama_actividad": "Educación",
        "ocupados": 245000,
        "participacion_pct": 8.5,
        "tasa_desempleo": 2.1
      },
      // ... más ramas
    ],
    "filtros_disponibles": {
      "years": [2021, 2022, 2023, 2024, 2025],
      "provincias": ["Azuay", "Bolívar", ..., "Zamora Chinchipe"],
      "sectores": ["Educación", "Salud", "Comercio", ...]
    }
  }
}
```

---

## 🎨 Componentes del frontend

### **Landing View** (Inicial)
- Presentación institucional
- Botones para elegir módulo
- Información de sincronización de datos

### **Dashboard View** (Modular)

**Header:**
- Botón "Volver"
- Selector de módulo (dropdown)

**Filtros:**
- Año (2021-2025)
- Provincia (todas)
- Botón "Actualizar"

**KPIs (4 tarjetas):**
- Métrica principal
- Métrica secundaria
- Métrica terciaria
- Muestra/Confiabilidad

**Visualizaciones:**
- Gráfico principal (Plotly)
- Gráfico secundario (Plotly)

**Tabla de datos:**
- Datos detallados (dinámico según módulo)

### **Librerías utilizadas**
- **Chart.js** → Gráficos básicos
- **Plotly.js** → Gráficos interactivos
- **TailwindCSS** → Estilos
- **Lucide Icons** → Iconos

---

## 🔐 Integridad de datos

### **Sin perder datos:**
- ✅ Todas las filas de Gold se preservan en JSON
- ✅ Todas las columnas originales están presentes (aunque se visualicen algunas)
- ✅ Valores de fexp (factor de expansión) incluidos
- ✅ Metadata de confiabilidad (`confiable: bool`) presente

### **Auditabilidad:**
- ✅ Cada transformación está en `generate_dashboard_data.py`
- ✅ Código documentado con docstrings
- ✅ Logs de ejecución (print statements)
- ✅ Metadata de fuente en JSON (`datos_origen: "data/gold/enemdu/*.parquet"`)

### **Reproducibilidad:**
- ✅ Mismo script, mismo input → mismo output
- ✅ Timestamp de generación en JSON
- ✅ Versión del pipeline registrada
- ✅ Fácil detectar cuando data está desactualizada

---

## 🚀 Escalabilidad futura

### **Agregar nuevo módulo (e.g., Red Alumni)**

**Paso 1:** Crear tabla en Gold (`data/gold/alumni_insercion.parquet`)

**Paso 2:** Editar `generate_dashboard_data.py`:
```python
def build_alumni_module(alumni_df, kpi_df, ...):
    """Construye módulo Alumni"""
    return {
        "title": "Red Alumni UCuenca",
        "kpi_latest": {...},
        "timeline": {...},
        # ...
    }

# En build_dashboard_json()
alumni = build_alumni_module(...)
dashboard_data["modules"]["alumni"] = alumni
```

**Paso 3:** Editar HTML:
```html
<option value="alumni">Red Alumni UCuenca</option>

<script>
function renderAlumniModule(data) {
  // Dibujar KPIs, gráficos, tabla
}
</script>
```

**Paso 4:** Ejecutar script:
```bash
python generate_dashboard_data.py
```

✅ Nuevo módulo disponible sin cambios de infraestructura

---

## 📊 Métricas de desempeño

| Métrica | Valor |
|---------|-------|
| Tamaño JSON | ~87 KB |
| Tiempo generación script | ~3 segundos |
| Tiempo carga del navegador | <500 ms |
| Filas de datos | 525,000+ (Silver unificado) |
| Registros expandidos | 8M+ (con ponderación) |

---

## 🔄 Pipeline de actualización

### **Semanal (ejemplo):**
1. Notebook descarga ENEMDU nuevo (si disponible)
2. Regenera Bronze → Silver → Gold
3. Ejecuta: `python generate_dashboard_data.py`
4. Commit en Git: `data/gold/enemdu/, visualizacion/static/data.json`
5. Dashboard reflect cambios automáticamente (sin tocar HTML)

### **Comandos git:**
```bash
cd ucuenca-sabe/

# Ver cambios
git status

# Commit
git add data/gold/enemdu/ visualizacion/static/data.json
git commit -m "Update ENEMDU dashboard data — semana 36"

# Push
git push origin main
```

---

## 🔒 Consideraciones de seguridad

- ✅ **No hay backend:** Elimina vector de ataques servidor
- ✅ **Datos públicos:** ENEMDU es del INEC (dominio público)
- ✅ **JSON local:** No transmite datos sensibles
- ✅ **CORS:** No requiere (carga local)

---

## 📞 Mantenibilidad

### **Quien actualiza:**
- **Datos:** Técnico que ejecuta notebook + script Python
- **Visualizaciones:** Frontend dev que edita HTML/JS
- **Lógica:** Data engineer que edita `generate_dashboard_data.py`

### **Documentación:**
- Este archivo (`DASHBOARD_ARCHITECTURE.md`)
- Docstrings en `generate_dashboard_data.py`
- Comentarios en HTML (`<!-- ... -->`)
- README en `visualizacion/`

### **Testing:**
- Validar JSON: `python -m json.tool static/data.json`
- Validar datos: Comparar KPIs con notebook output
- Validar HTML: Abrir en navegador, revisar consola (F12)

---

## 🎯 Roadmap futuro

**Corto plazo (Q4 2026):**
- [ ] Filtros dinámicos funcionando (año, provincia)
- [ ] Tabla exportable (CSV)
- [ ] Share de gráficos (PNG)

**Mediano plazo (Q1 2027):**
- [ ] Módulo Alumni (si datos disponibles)
- [ ] Módulo Demanda en Tiempo Real (web scraping)
- [ ] Comparativas provinciales interactivas

**Largo plazo:**
- [ ] Dashboard para móvil (responsive mejorado)
- [ ] Integración con Power BI (export automático)
- [ ] API REST para consumo de terceros

---

**Versión:** 1.0 | **Fecha:** 2026-09-04 | **Responsable:** UCuenca-SABE
