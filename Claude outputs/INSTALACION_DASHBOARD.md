# 📋 Instalación Dashboard Empleabilidad — ENEMDU + Sobrecalificación

**Proyecto:** UCuenca-SABE | Inteligencia Territorial  
**Componente:** MVP Dashboard de Empleabilidad  
**Última actualización:** 2026-09-04  
**Estado:** Listo para instalar

---

## 📂 Estructura de archivos

```
ucuenca-sabe/
├── data/
│   └── gold/enemdu/               ← YA EXISTE (salida del notebook)
│       ├── kpi_anual.parquet
│       ├── empleabilidad_provincia.parquet
│       ├── empleabilidad_sexo_edad.parquet
│       ├── graduados_rama_actividad.parquet
│       ├── sobrecalificacion_ocupacion.parquet
│       └── ... (otras tablas)
│
├── visualizacion/
│   ├── scripts/                   ← CREAR CARPETA
│   │   └── generate_dashboard_data.py          ← NUEVO (copiar abajo)
│   │
│   ├── static/                    ← CREAR CARPETA
│   │   └── data.json              ← Generado automáticamente (NO crear manual)
│   │
│   └── MVP_dashboard_empleabilidad.html        ← REEMPLAZAR (copiar versión actualizada)
│
└── docs/
    └── DASHBOARD_ARCHITECTURE.md   ← NUEVO (documentación técnica)
```

---

## 🚀 Instalación paso a paso

### **Paso 1: Crear carpetas necesarias**

```bash
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion

# Crear carpetas si no existen
mkdir scripts
mkdir static
```

### **Paso 2: Copiar script Python**

**Archivo:** `generate_dashboard_data.py`

**Ubicación destino:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\generate_dashboard_data.py`

**Contenido:** [Ver sección 📄 Archivos a copiar abajo]

```bash
# Verificar que fue copiado correctamente
ls -la C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\
```

### **Paso 3: Ejecutar script para generar datos**

```bash
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\

python generate_dashboard_data.py
```

**Esperado:** El script debería:
- ✅ Leer los 5 Parquet de Gold
- ✅ Generar `../static/data.json` (~50-100 KB)
- ✅ Imprimir: `✅ JSON generado: .../static/data.json`

**Ejemplo de salida:**
```
📥 Leyendo datos de Gold...
  ✓ kpi_anual: 5 filas
  ✓ empleabilidad_provincia: 150 filas
  ...
✅ JSON generado: C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\static\data.json
   Tamaño: 87.5 KB
   Módulos: enemdu, sobrecalificacion
```

### **Paso 4: Reemplazar archivo HTML**

**Archivo antiguo:** `MVP_dashboard_empleabilidad.html` (respaldo si necesitas)

**Archivo nuevo:** `MVP_dashboard_empleabilidad_UPDATED.html` (copiar como)

```bash
# OPCIÓN A: Renombrar el viejo como respaldo
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\
mv MVP_dashboard_empleabilidad.html MVP_dashboard_empleabilidad.backup.html

# OPCIÓN B: Reemplazar directamente
# (Copiar MVP_dashboard_empleabilidad_UPDATED.html → MVP_dashboard_empleabilidad.html)
```

**Ubicación final:**
```
C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\MVP_dashboard_empleabilidad.html
```

### **Paso 5: Abrir y probar el dashboard**

```bash
# Abrir en navegador (Windows)
start MVP_dashboard_empleabilidad.html

# O simplemente hacer doble click en el archivo
```

---

## ✅ Checklist de validación

- [ ] Carpeta `visualizacion/scripts/` creada
- [ ] Carpeta `visualizacion/static/` creada
- [ ] Archivo `generate_dashboard_data.py` copiado en `scripts/`
- [ ] Script ejecutado: `python generate_dashboard_data.py`
- [ ] Archivo `static/data.json` creado (verifica tamaño > 50 KB)
- [ ] HTML actualizado en `MVP_dashboard_empleabilidad.html`
- [ ] Dashboard abre en navegador sin errores

---

## 🔄 Flujo de actualización automática

Cada vez que tus datos de Gold cambien (nuevo año, nueva corrida del pipeline):

```bash
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\
python generate_dashboard_data.py
```

Luego abre el HTML → **Verá datos frescos** (sin editar nada)

---

## 🐛 Troubleshooting

### Error: "module 'pandas' has no attribute 'read_parquet'"

**Solución:**
```bash
pip install --upgrade pyarrow
```

### Error: "FileNotFoundError: data/gold/enemdu/kpi_anual.parquet"

**Verificar:**
```bash
ls -R C:\Users\michu\mis-proyectos\ucuenca-sabe\data\gold\enemdu\
```

Debe mostrar `.parquet` files. Si no hay, ejecutar primero el notebook de Gold.

### El JSON no se carga en el dashboard

**Verificar:**
1. Abre el navegador → F12 (Developer Tools)
2. Pestaña "Console" → busca errores
3. Verifica que `static/data.json` existe y es válido

```bash
# Validar JSON
python -m json.tool static/data.json > /dev/null && echo "✅ JSON válido"
```

---

## 📄 Archivos a copiar

### Archivo 1: `generate_dashboard_data.py`

**Destinación:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\generate_dashboard_data.py`

[Contenido completo arriba, en sección "Script Python"]

### Archivo 2: `MVP_dashboard_empleabilidad.html`

**Destinación:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\MVP_dashboard_empleabilidad.html`

[Contenido completo arriba, en sección "HTML Actualizado"]

---

## 📊 Módulos disponibles en el dashboard

### **1. Mercado Laboral ENEMDU**
- **KPIs:** Tasa de desempleo, empleo adecuado, ingreso laboral
- **Visualizaciones:**
  - Línea: Evolución 2021-2025
  - Barras: Top 10 provincias por desempleo
  - Tabla: Detalle por provincia
- **Filtros:** Año, Provincia
- **Fuente:** `data/gold/enemdu/kpi_anual.parquet` + `empleabilidad_provincia.parquet`

### **2. Sobrecalificación**
- **KPIs:** Tasa general de sobrecalificación (% graduados en ocupaciones no acordes)
- **Visualizaciones:**
  - Línea: Evolución tasa sobrecalificación 2021-2025
  - Barras: Top ocupaciones (CIUO-08) con mismatch
  - Tabla: Detalle por ocupación
- **Metodología:** Sobrecalificado = Graduado en ocupaciones CIUO-08 grupos 4-9
- **Fuente:** `data/gold/enemdu/sobrecalificacion_ocupacion.parquet`

---

## 🔧 Configuración avanzada

### Personalizar colores

Edita el archivo HTML, sección `<script>` → `tailwind.config` → `ucuenca` colors:

```javascript
colors: {
  ucuenca: {
    navy: '#0B2341',      // Azul UCuenca
    red: '#D3272C',        // Rojo institucional
    accent: '#1E4C82',     // Azul secundario
    // Personaliza aquí según tu marca
  }
}
```

### Agregar más módulos en el futuro

1. Crear tabla en Gold (e.g., `alumni_insercion.parquet`)
2. Editar `generate_dashboard_data.py` → agregar función `build_alumni_module()`
3. Agregar opción en HTML → `<option value="alumni">Red Alumni UCuenca</option>`
4. Ejecutar script nuevamente

---

## 📞 Soporte

**Si hay errores:**

1. Copia el error completo (de la consola del navegador)
2. Verifica que rutas sean absolutas (`C:\Users\...`)
3. Ejecuta `python generate_dashboard_data.py` manualmente
4. Revisa que `static/data.json` se creó

---

## 📝 Notas importantes

- ✅ **Sin PowerBI:** Sistema reproducible y versionable
- ✅ **Datos reales:** Conecta directo a Gold, sin hardcoding
- ✅ **Filtros dinámicos:** Lee automáticamente años/provincias de datos
- ✅ **Sostenible:** Documentado y escalable para agregar más módulos
- ✅ **Auditabilidad:** Toda transformación está en Python, visible y reproducible

---

**Versión:** 1.0 | **Fecha:** 2026-09-04 | **Estado:** Producción
