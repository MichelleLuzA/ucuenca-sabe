# ✅ CHECKLIST INSTALACIÓN — Dashboard Empleabilidad

**Fecha Inicio:** _______________  
**Responsable:** Michelle  
**Proyecto:** UCuenca-SABE  

---

## 📋 PRE-REQUISITOS

- [ ] Tienes `C:\Users\michu\mis-proyectos\ucuenca-sabe\` accesible
- [ ] Los archivos Gold existen: `data/gold/enemdu/*.parquet`
- [ ] Python 3 instalado: `python --version` (debe ser 3.7+)
- [ ] Pandas instalado: `pip show pandas`
- [ ] PyArrow instalado: `pip show pyarrow` (si no: `pip install pyarrow`)

---

## 🗂️ PASO 1: CREAR CARPETAS

**Ubicación:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\`

```bash
mkdir scripts
mkdir static
```

**Verificación:**
- [ ] `scripts/` folder creado
- [ ] `static/` folder creado

```bash
# Verificar
ls -la
# Debe mostrar: scripts/ y static/
```

---

## 📄 PASO 2: COPIAR SCRIPT PYTHON

**Archivo:** `generate_dashboard_data.py` (de tu descarga)

**Destino:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\`

```bash
# Verificar que se copió
ls scripts/
# Debe mostrar: generate_dashboard_data.py
```

**Checklist:**
- [ ] Archivo copiado en `scripts/generate_dashboard_data.py`
- [ ] No tiene caracteres raros en el path
- [ ] Python puede leerlo: `python scripts/generate_dashboard_data.py --help` (debería ejecutar sin errores)

---

## 🚀 PASO 3: EJECUTAR SCRIPT

**Terminal:**
```bash
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\scripts\
python generate_dashboard_data.py
```

**Salida esperada:**
```
📥 Leyendo datos de Gold...
  ✓ kpi_anual: 5 filas
  ✓ empleabilidad_provincia: 150 filas
  ✓ empleabilidad_sexo_edad: ... filas
  ✓ graduados_rama_actividad: ... filas
  ✓ sobrecalificacion_ocupacion: 45 filas

📊 Generando módulo ENEMDU...
📊 Generando módulo Sobrecalificación...

✅ JSON generado: C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\static\data.json
   Tamaño: 87.5 KB
   Módulos: enemdu, sobrecalificacion
```

**Checklist:**
- [ ] Script ejecutado sin errores
- [ ] Leyó todos los 5 .parquet files
- [ ] Mensaje `✅ JSON generado` apareció

**Si hay error:**
- [ ] Verifica que Gold path es correcto: `../../../data/gold/enemdu/`
- [ ] Verifica que PyArrow está instalado: `pip install pyarrow`
- [ ] Copia el error completo en tu pregunta

---

## 📁 PASO 4: VERIFICAR ARCHIVO JSON

**Ubicación:** `C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\static\data.json`

```bash
# Verificar que existe
ls -lh static/
# Debe mostrar: data.json (~80-90 KB)

# Verificar que es JSON válido
python -m json.tool static/data.json > /dev/null
# Si no hay error, es válido
```

**Checklist:**
- [ ] `data.json` existe en `static/`
- [ ] Tamaño es ~80-90 KB (no 0 bytes, no > 200 KB)
- [ ] Contiene ambos módulos:
  ```bash
  grep -c '"enemdu"' static/data.json  # Debe ser 1
  grep -c '"sobrecalificacion"' static/data.json  # Debe ser 1
  ```

---

## 📝 PASO 5: REEMPLAZAR HTML

**Archivo viejo:** `MVP_dashboard_empleabilidad.html`  
**Archivo nuevo:** `MVP_dashboard_empleabilidad_UPDATED.html` (de tu descarga)

**En terminal:**
```bash
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\visualizacion\

# Opción A: Renombrar viejo como respaldo
mv MVP_dashboard_empleabilidad.html MVP_dashboard_empleabilidad.backup.html

# Opción B: Simplemente reemplazar (si tienes seguridad de que tienes respaldo)
# rm MVP_dashboard_empleabilidad.html
```

**Copiar nuevo:**
```bash
# Copiar el archivo UPDATED
cp MVP_dashboard_empleabilidad_UPDATED.html MVP_dashboard_empleabilidad.html
```

**Verificación:**
- [ ] Archivo `MVP_dashboard_empleabilidad.backup.html` existe (respaldo)
- [ ] Archivo `MVP_dashboard_empleabilidad.html` es el nuevo (contiene "Plotly")
  ```bash
  grep -c "Plotly" MVP_dashboard_empleabilidad.html  # Debe ser >= 1
  ```

---

## 🌐 PASO 6: ABRIR EN NAVEGADOR

**Abre archivo:**
```bash
# Windows
start MVP_dashboard_empleabilidad.html

# O simplemente doble-click en el archivo
```

**Esperado:**
1. Aparece página oscura (UCuenca branding)
2. Dos botones: "Mercado Laboral ENEMDU" y "Sobrecalificación"
3. Última fila: "Datos: [fecha]"

**Checklist:**
- [ ] Página carga sin error (no aparece página blanca)
- [ ] Puedo leer texto "UCUENCA" y "Observatorio Institucional"
- [ ] Hay 2 botones grandes
- [ ] Puedo leer la fecha de sincronización

---

## 🎨 PASO 7: NAVEGAR A MÓDULOS

### **Módulo 1: ENEMDU**

```
Haz click en: "Mercado Laboral ENEMDU"
```

**Esperado:**
- [ ] Página cambia a fondo claro
- [ ] Aparecen 4 KPI cards (números grandes)
- [ ] 2 gráficos se cargan
- [ ] Tabla con provincias
- [ ] Filtros: Año, Provincia

**KPIs que deberías ver (2025):**
- Tasa Desempleo: ~3.5%
- Ingreso Laboral: ~$ 1028
- Empleo Adecuado: ~42%
- Muestra: ~21,140 registros

```bash
# Verificar en Developer Tools (F12):
# No debe haber errores en Console
# Network debe mostrar: static/data.json (200 OK)
```

### **Módulo 2: Sobrecalificación**

```
Vuelve al inicio (click "Volver")
Haz click en: "Sobrecalificación"
```

**Esperado:**
- [ ] Página carga (fondo claro)
- [ ] KPI principal: Tasa sobrecalificación (~11%)
- [ ] Gráfico línea: evolución
- [ ] Gráfico barras: ocupaciones
- [ ] Tabla con detalle

---

## 🐛 TROUBLESHOOTING

### **Problema: Página aparece blanca**

**Checklist:**
- [ ] F12 (Developer Tools) → Console
- [ ] Busca mensajes de error rojo
- [ ] Verifica que `static/data.json` está en el path correcto

**Solución:**
```bash
# Verificar que data.json está donde lo espera el HTML
ls visualizacion/static/data.json
# Debe existir

# Si no existe, vuelve a ejecutar script
python visualizacion/scripts/generate_dashboard_data.py
```

### **Problema: Gráficos no aparecen**

**Checklist:**
- [ ] F12 → Network
- [ ] Busca peticiones a Plotly CDN
- [ ] Verifica que no hay status 404

**Solución:**
```bash
# Verifica conexión a internet (CDN requiere conexión)
# Espera 5 segundos y recarga (F5)
```

### **Problema: "ModuleNotFoundError: No module named 'pyarrow'"**

**Solución:**
```bash
pip install --upgrade pyarrow
# Luego vuelve a ejecutar script
python visualizacion/scripts/generate_dashboard_data.py
```

### **Problema: FileNotFoundError al ejecutar script**

**Checklist:**
- [ ] ¿Estoy en la carpeta correcta? (scripts/)
- [ ] ¿El path relativo `../../../data/gold/enemdu/` es correcto?

**Solución:**
```bash
# Verifica manualmente
ls ../../../../data/gold/enemdu/
# Debe mostrar archivos .parquet

# O edita script y usa ruta absoluta (temporal, solo para debug)
# kpi = pd.read_parquet("C:\\Users\\michu\\...\kpi_anual.parquet")
```

---

## ✅ VALIDACIÓN FINAL

Completa este checklist completo:

- [ ] Carpetas creadas (`scripts/`, `static/`)
- [ ] Script `generate_dashboard_data.py` en `scripts/`
- [ ] Script ejecutado sin errores
- [ ] Archivo `static/data.json` existe (~80-90 KB)
- [ ] HTML reemplazado (backup del viejo existe)
- [ ] Página abre en navegador
- [ ] Módulo ENEMDU carga y muestra datos
- [ ] Módulo Sobrecalificación carga y muestra datos
- [ ] Developer Console (F12) sin errores rojos
- [ ] Filtros son clickeables
- [ ] Tablas muestran datos reales

---

## 📊 DATOS ESPERADOS

### **ENEMDU 2025 (últimas filas del JSON)**
```
Tasa Desempleo: 3.5% (aprox)
Empleo Adecuado: 42% (aprox)
Ingreso Laboral: $1028 (aprox)
Muestra: 21,140 registros
```

### **Sobrecalificación 2025**
```
Tasa General: ~11% (aprox)
Top ocupación: Profesionales (Grupo 2)
Ocupados afectados: Varios miles
```

Si ves números diferentes, **no es error**, es porque los datos de Gold son los reales.

---

## 🎯 SIGUIENTE PASO

Una vez validado todo:

```bash
# Commit en Git (si estás usando Git)
cd C:\Users\michu\mis-proyectos\ucuenca-sabe\
git add visualizacion/
git commit -m "MVP dashboard ENEMDU + Sobrecalificación v1.0"
git push origin main
```

---

## 📞 SOPORTE

Si algo no funciona, conserva:
- [ ] Screenshot del error
- [ ] Mensaje de error completo (copy-paste)
- [ ] Output del script (copy-paste)
- [ ] Archivo `data.json` (valida con: `python -m json.tool static/data.json`)

---

**¡Completaste la instalación? ¡Dale! 🚀**

Fecha finalización: _______________  
Versión instalada: v1.0  
Estado: ✅ PRODUCCIÓN
