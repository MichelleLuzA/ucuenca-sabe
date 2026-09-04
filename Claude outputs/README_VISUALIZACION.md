# 📊 Visualizacion — MVP Dashboard de Empleabilidad

**Módulo:** Sistema de Inteligencia Territorial | UCuenca-SABE  
**Componente:** Dashboard interactivo ENEMDU + Sobrecalificación  
**Versión:** 1.0  
**Última actualización:** 2026-09-04  

---

## 📂 Estructura de carpeta

```
visualizacion/
├── scripts/
│   ├── generate_dashboard_data.py   # Script que extrae Gold → JSON
│   └── README.md                     # (Futuro: otros scripts)
│
├── static/
│   ├── data.json                     # JSON generado (NO editar manual)
│   └── style.css                     # (Futuro: si quieres separar CSS)
│
├── MVP_dashboard_empleabilidad.html  # Dashboard principal
└── README.md                          # Este archivo

```

---

## 🚀 Quick Start

### **Prerequisitos**
- Python 3.7+
- Pandas + PyArrow (`pip install pyarrow`)
- Gold data en: `../data/gold/enemdu/*.parquet`

### **Ejecutar**

```bash
cd scripts/
python generate_dashboard_data.py
cd ..
# Abre MVP_dashboard_empleabilidad.html en navegador
```

---

## 📊 Módulos del Dashboard

### **1. Mercado Laboral ENEMDU**
- Fuente: ENEMDU INEC 2021-2025
- Datos: `data/gold/enemdu/kpi_anual.parquet` + provincia
- KPIs: Desempleo, Empleo Adecuado, Ingreso, Muestra
- Visualizaciones: Línea + Barras + Tabla
- Filtros: Año, Provincia

### **2. Sobrecalificación**
- Fuente: `sobrecalificacion_ocupacion.parquet`
- KPI: % Graduados en ocupaciones no acordes (CIUO-08 grupos 4-9)
- Visualizaciones: Línea + Barras + Tabla
- Granularidad: Por ocupación (CIUO-08), por año

---

## 🔄 Flujo de datos

```
data/gold/enemdu/
├── kpi_anual.parquet
├── empleabilidad_provincia.parquet
├── empleabilidad_sexo_edad.parquet
├── graduados_rama_actividad.parquet
└── sobrecalificacion_ocupacion.parquet
            ↓ (Python + Pandas)
    generate_dashboard_data.py
            ↓
    static/data.json (~87 KB)
            ↓ (fetch JSON)
    MVP_dashboard_empleabilidad.html
            ↓
    Navegador (Plotly + Chart.js)
```

---

## 📝 Actualizar datos

Cuando haya nuevos datos ENEMDU (mensual o cuando corra el notebook):

```bash
python scripts/generate_dashboard_data.py
```

El archivo `static/data.json` se regenera automáticamente.  
**No es necesario tocar el HTML.** Al recargar la página, verá datos frescos.

---

## 🛠️ Customización

### **Cambiar colores**
Edita `MVP_dashboard_empleabilidad.html` → `<script>` → `tailwind.config` → `ucuenca` colors

### **Agregar nuevos gráficos**
1. Agregar función en `generate_dashboard_data.py`
2. Extender JSON output
3. Editar HTML: función `render*Module()` para dibujar nuevos gráficos

### **Agregar nuevo módulo**
1. Crear tabla en Gold (e.g., `alumni_insercion.parquet`)
2. Agregar función `build_alumni_module()` en script Python
3. Generar script nuevamente
4. Agregar opción en HTML (dropdown + función render)

---

## 📊 Especificaciones técnicas

### **Frontend**
- **Framework:** Vanilla JavaScript (sin dependencias)
- **Estilos:** TailwindCSS (CDN)
- **Gráficos:** Plotly.js + Chart.js (CDN)
- **Iconos:** Lucide Icons (CDN)

### **Backend (generación)**
- **Lenguaje:** Python 3
- **Librerías:** Pandas, PyArrow, JSON
- **Input:** Parquet (Gold tables)
- **Output:** JSON estático

### **Rendimiento**
- JSON size: ~87 KB
- Generación: ~3 segundos
- Carga navegador: <500 ms
- Compatibilidad: Chrome, Firefox, Safari, Edge

---

## ✅ Integridad de datos

- ✅ Todas las filas de Gold preservadas
- ✅ Todas las columnas presentes (aunque visualicen seleccionadas)
- ✅ Factor de expansión (fexp) incluido
- ✅ Metadata de confiabilidad presente
- ✅ Auditabilidad: cada transformación en código Python

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| "JSON no se carga en navegador" | F12 Console → verifica path relativo `static/data.json` |
| "Gráficos no aparecen" | Verifica conexión a CDN (Plotly.js). F12 Network. |
| "Script da error pyarrow" | `pip install --upgrade pyarrow` |
| "No encuentra archivos .parquet" | Verifica que Gold está en `../data/gold/enemdu/` |
| "Filtros no funcionan" | Feature en construcción. V2 planificado. |

---

## 📞 Responsables

- **Data Engineering:** Notebook ENEMDU
- **Backend Scripts:** `generate_dashboard_data.py`
- **Frontend:** `MVP_dashboard_empleabilidad.html`
- **Arquitectura:** Ver `DASHBOARD_ARCHITECTURE.md`

---

## 🎯 Roadmap

**v1.0 (Current):** ENEMDU + Sobrecalificación  
**v1.1:** Filtros dinámicos funcionales  
**v1.2:** Exportación CSV/PNG  
**v2.0:** Módulo Alumni (si datos disponibles)  
**v2.1:** Módulo Demanda en Tiempo Real (scraping)  

---

## 📖 Documentación

- `INSTALACION_DASHBOARD.md` — Guía paso a paso
- `DASHBOARD_ARCHITECTURE.md` — Arquitectura técnica
- Docstrings en `generate_dashboard_data.py`

---

**Versión:** 1.0  
**Estado:** Production  
**Mantenimiento:** Trimestral  
**Última revisión:** 2026-09-04
