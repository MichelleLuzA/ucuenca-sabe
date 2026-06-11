import sys
from pathlib import Path

# Agregar src al path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import json
from datetime import datetime

# ============================================
# USAR CONFIGURACIÓN CENTRALIZADA
# ============================================
config = Config()
config.ensure_directories()

print("="*60)
print("SCRAPER UCUENCA - MODO MANUAL")
print("="*60)
print("\n⚠️  IMPORTANTE:")
print("1. El navegador se abrirá y tendrás que resolver el CAPTCHA manualmente")
print("2. Tendrás 60 segundos para hacerlo en la PRIMERA página")
print("3. Para las siguientes páginas, espera 10 segundos y si hay 403, resuelve")
print("4. NO cierres el navegador, espera que termine\n")
input("👉 Presiona ENTER para comenzar...")

# Configurar opciones
options = Options()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

data = []
timestamp = datetime.now().isoformat()

# ============================================
# PÁGINA 1 (URL especial)
# ============================================
for page_num in range(1, 9):
    # Construir URL correctamente
    if page_num == 1:
        url = "https://investigacion.ucuenca.edu.ec/es/persons/"
    else:
        url = f"https://investigacion.ucuenca.edu.ec/es/persons/?page={page_num - 1}"
    
    print(f"\n{'='*50}")
    print(f"📄 PÁGINA {page_num} DE 8")
    print(f"   URL: {url}")
    print(f"{'='*50}")
    
    driver.get(url)
    
    # Espera según la página
    if page_num == 1:
        print("\n⏳ ESPERA MANUAL DE 60 SEGUNDOS")
        print("👉 Resuelve el CAPTCHA visualmente si aparece")
        for i in range(60, 0, -10):
            print(f"   ... {i} segundos restantes")
            time.sleep(10)
    else:
        print("⏳ Esperando 10 segundos...")
        time.sleep(10)
    
    # Verificar error 403
    page_text = driver.page_source
    if "403" in page_text or "Forbidden" in page_text:
        print("  ⚠️ Error 403 detectado")
        print("  👉 Recarga manualmente la página y resuelve el CAPTCHA")
        input("  Presiona ENTER después de resolver el CAPTCHA...")
        # Recargar después del CAPTCHA
        driver.refresh()
        time.sleep(5)
    
    # Extraer investigadores
    items = driver.find_elements(By.CSS_SELECTOR, "li.grid-result-item")
    print(f"  📊 Encontrados {len(items)} elementos")
    
    for item in items:
        try:
            nombre_elem = item.find_element(By.CSS_SELECTOR, "h3.title a")
            nombre = nombre_elem.text.strip()
            
            org_links = item.find_elements(By.CSS_SELECTOR, ".relations.organisations li a")
            
            facultad = ""
            departamento = ""
            grupos = []
            
            for org in org_links:
                texto = org.text.strip()
                if "Facultad de" in texto:
                    facultad = texto
                elif "Departamento de" in texto:
                    departamento = texto
                elif "Grupo de Investigación:" in texto:
                    grupo = texto.replace("Grupo de Investigación:", "").strip()
                    grupos.append(grupo)
            
            data.append({
                "investigador": nombre,           # ← minúscula para consistencia
                "facultad": facultad,
                "departamento": departamento,
                "grupos_investigacion": " | ".join(grupos),
                "pagina": page_num,
                "url_perfil": nombre_elem.get_attribute("href"),
                "fecha_extraccion": timestamp
            })
            
        except Exception as e:
            print(f"     Error en un registro: {e}")
            continue
    
    print(f"  ✅ Extraídos en esta página: {len([d for d in data if d['pagina'] == page_num])}")
    print(f"  ✅ Total acumulado: {len(data)}")

print("\n" + "="*60)
print("FINALIZANDO...")
print("="*60)

driver.quit()

# ============================================
# GUARDAR USANDO LAS RUTAS DE CONFIG
# ============================================
df = pd.DataFrame(data)

# CORREGIDO: usar el nombre correcto de la columna
if len(df) > 0:
    df = df.drop_duplicates(subset=['investigador'])
else:
    print("⚠️ No se extrajeron datos")
    sys.exit(1)

# Guardar en BRONZE (raw data)
bronze_csv = config.BRONZE_INVESTIGACION / "investigadores_raw.csv"
bronze_json = config.BRONZE_INVESTIGACION / "investigadores_raw.json"
bronze_excel = config.BRONZE_INVESTIGACION / "investigadores_raw.xlsx"

df.to_csv(bronze_csv, index=False, encoding='utf-8-sig')
df.to_json(bronze_json, orient='records', force_ascii=False, indent=2)
df.to_excel(bronze_excel, index=False)

# Guardar en SILVER (datos procesados)
silver_parquet = config.SILVER_DIR / "investigadores.parquet"
silver_csv = config.SILVER_DIR / "investigadores.csv"

df.to_parquet(silver_parquet, index=False)
df.to_csv(silver_csv, index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print("RESULTADOS FINALES")
print("="*60)
print(f"\n✅ TOTAL: {len(df)} investigadores únicos")

print(f"\n📁 Archivos guardados en BRONZE:")
print(f"   📄 CSV:   {bronze_csv}")
print(f"   📊 Excel: {bronze_excel}")
print(f"   📋 JSON:  {bronze_json}")

print(f"\n📁 Archivos guardados en SILVER:")
print(f"   🗄️ Parquet: {silver_parquet}")
print(f"   📄 CSV:     {silver_csv}")

if len(df) > 0:
    print("\n📊 TOP 5 FACULTADES:")
    print(df['facultad'].value_counts().head(10))
    
    print("\n📊 TOP 5 DEPARTAMENTOS:")
    # Filtrar departamentos no vacíos
    dept_counts = df[df['departamento'] != '']['departamento'].value_counts().head(10)
    if len(dept_counts) > 0:
        print(dept_counts)
    else:
        print("   (No se encontraron departamentos)")
    
    print(f"\n📊 Investigadores por página:")
    for page in range(1, 9):
        count = len(df[df['pagina'] == page])
        if count > 0:
            print(f"   Página {page}: {count} investigadores")
    
    print(f"\n📊 Ejemplo de grupos de investigación:")
    grupos_con_datos = df[df['grupos_investigacion'] != '']['grupos_investigacion'].head(10)
    for g in grupos_con_datos:
        print(f"   • {g[:80]}...")