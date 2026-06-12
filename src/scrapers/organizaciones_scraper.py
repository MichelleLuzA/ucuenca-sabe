# src/scrapers/organizaciones_scraper.py
"""
Scraper para extraer la jerarquía completa de organizaciones:
Facultades → Departamentos → Grupos de Investigación
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
from datetime import datetime

config = Config()
config.ensure_directories()

print("="*60)
print("SCRAPER DE JERARQUÍA UCUENCA")
print("Facultades → Departamentos → Grupos de Investigación")
print("="*60)
print("\n⚠️  Abrirá el navegador. Resuelve CAPTCHA si aparece.\n")
input("👉 Presiona ENTER para comenzar...")

options = Options()
options.add_argument('--disable-blink-features=AutomationControlled')
driver = webdriver.Chrome(options=options)

# ============================================
# 1. OBTENER TODAS LAS ORGANIZACIONES
# ============================================
url = "https://investigacion.ucuenca.edu.ec/es/organisations/"
driver.get(url)
time.sleep(10)

# Buscar todas las organizaciones
org_items = driver.find_elements(By.CSS_SELECTOR, ".list-result-item, .search-result-item")

organizaciones = []

for item in org_items:
    try:
        nombre_elem = item.find_element(By.CSS_SELECTOR, "h3 a")
        nombre = nombre_elem.text.strip()
        url_org = nombre_elem.get_attribute("href")
        
        # Determinar tipo por el texto o URL
        if "facultad" in nombre.lower():
            tipo = "Facultad"
        elif "departamento" in nombre.lower():
            tipo = "Departamento"
        elif "grupo de investigación" in nombre.lower():
            tipo = "Grupo"
        else:
            tipo = "Organización"
        
        organizaciones.append({
            "nombre": nombre,
            "url": url_org,
            "tipo": tipo,
            "fecha_extraccion": datetime.now().isoformat()
        })
    except:
        continue

print(f"\n📊 Total organizaciones encontradas: {len(organizaciones)}")

# ============================================
# 2. CLASIFICAR POR TIPO
# ============================================
df_org = pd.DataFrame(organizaciones)

facultades = df_org[df_org['tipo'] == 'Facultad']['nombre'].tolist()
departamentos = df_org[df_org['tipo'] == 'Departamento']['nombre'].tolist()
grupos = df_org[df_org['tipo'] == 'Grupo']['nombre'].tolist()

print(f"\n📚 Facultades: {len(facultades)}")
print(f"📁 Departamentos: {len(departamentos)}")
print(f"🔬 Grupos de investigación: {len(grupos)}")

# ============================================
# 3. GUARDAR RESULTADOS
# ============================================
# Guardar en bronze
bronze_path = config.BRONZE_INVESTIGACION / "organizaciones.csv"
df_org.to_csv(bronze_path, index=False, encoding='utf-8-sig')

# Guardar en silver
silver_path = config.SILVER_DIR / "organizaciones.parquet"
df_org.to_parquet(silver_path, index=False)

print(f"\n✅ Archivos guardados:")
print(f"   📄 CSV: {bronze_path}")
print(f"   🗄️ Parquet: {silver_path}")

driver.quit()