"""
Módulo de Ingesta de Datos desde Kaggle.
Encapsula la descarga y organización de archivos en la Capa Bronze.
"""

import os
import sys
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi
# Asegurar que podemos importar src.config
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

try:
    from src.config import CONFIG, get_external_bronze_dir
    from dotenv import load_dotenv
    load_dotenv()  # Cargar variables de entorno desde .env
except ImportError as e:
    print(f"❌ Error importando config: {e}")
    print(f"📁 Project root: {project_root}")
    raise

def download_and_organize_enemdu() -> dict:
    """
    Descarga el dataset de ENEMDU desde Kaggle y clasifica los archivos
    extraídos en la capa Bronze de externas/enemdu.
    """
    try:
        # 1. Obtener la ruta dinámicamente usando src/config.py
        enemdu_bronze_path = get_external_bronze_dir("enemdu")
        dicts_path = enemdu_bronze_path / "diccionarios"
        data_path = enemdu_bronze_path / "microdatos_csv"
        
        dicts_path.mkdir(parents=True, exist_ok=True)
        data_path.mkdir(parents=True, exist_ok=True)

        # 2. Verificar que existe la configuración
        if "sources" not in CONFIG or "enemdu" not in CONFIG["sources"]:
            raise KeyError("❌ Configuración 'sources.enemdu' no encontrada en config.yaml")
        
        dataset_name = CONFIG["sources"]["enemdu"]["kaggle_dataset"]
        print(f"🚀 Autenticando con Kaggle API...")
        # 3. Obtener el token del .env
        kaggle_api_token = os.getenv("KAGGLE_API_TOKEN")
        
        if not kaggle_api_token:
            raise ValueError(
                "❌ Token de Kaggle no encontrado en .env. "
                "Asegúrate de tener KAGGLE_API_TOKEN definido."
            )
        
        # 4. Configurar el token para la librería de Kaggle
        # La librería espera que el token esté en una variable de entorno específica
        os.environ["KAGGLE_API_TOKEN"] = kaggle_api_token        
        # 5. Autenticar con Kaggle
        try:
            api = KaggleApi()
            api.authenticate()
            print("✅ Autenticación exitosa con Access Token.")
        except Exception as e:
            print(f"❌ Error autenticando con Kaggle: {e}")
            print("💡 Asegúrate de tener el archivo kaggle.json en ~/.kaggle/")
            raise

        # 4. Descargar Dataset a Bronze
        print(f"📥 Descargando dataset '{dataset_name}' en: {enemdu_bronze_path}")
        api.dataset_download_files(dataset_name, path=str(enemdu_bronze_path), unzip=True)
        print("✅ Descarga finalizada.")

        # 5. Clasificar archivos extraídos (.xlsx vs .csv)
        inventory = {"diccionarios": [], "microdatos_csv": []}

        for file_path in enemdu_bronze_path.glob("*"):
            if file_path.is_file():
                if file_path.suffix.lower() in [".xlsx", ".xls"]:
                    target = dicts_path / file_path.name
                    file_path.rename(target)
                    inventory["diccionarios"].append(target.name)
                elif file_path.suffix.lower() == ".csv":
                    target = data_path / file_path.name
                    file_path.rename(target)
                    inventory["microdatos_csv"].append(target.name)

        print(f"📁 Clasificación en Bronze exitosa:")
        print(f"   - Diccionarios (.xlsx): {len(inventory['diccionarios'])}")
        print(f"   - Microdatos (.csv): {len(inventory['microdatos_csv'])}")

        return inventory
        
    except Exception as e:
        print(f"❌ Error en download_and_organize_enemdu: {e}")
        raise

if __name__ == "__main__":
    download_and_organize_enemdu()