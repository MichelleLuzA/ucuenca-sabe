"""
Módulo de Configuración Central y Gestión Dinámica de Rutas.
Resuelve rutas absolutas, administra parámetros globales y
garantiza la creación automática de directorios.
"""

from pathlib import Path
import yaml
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
# Determinar la raíz del proyecto de forma robusta
def get_project_root():
    """Encuentra la raíz del proyecto buscando una carpeta 'config' o '.git'."""
    current_path = Path(__file__).resolve().parent
    
    # Buscar hacia arriba hasta encontrar la carpeta 'config' o '.git'
    for _ in range(5):  # Máximo 5 niveles hacia arriba
        if (current_path / "config").exists() or (current_path / ".git").exists():
            return current_path
        current_path = current_path.parent
    
    # Fallback: asumir que estamos 2 niveles arriba de src
    return Path(__file__).resolve().parent.parent
# Determinar la raíz del proyecto de forma determinista (sube 1 nivel desde src/)
PROJECT_ROOT = get_project_root()
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

def _load_yaml_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"❌ Archivo de configuración no encontrado en: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = _load_yaml_config(CONFIG_PATH)

# Rutas Base
DATA_DIR = PROJECT_ROOT / CONFIG["paths"]["data_root"]
BRONZE_DIR = PROJECT_ROOT / CONFIG["paths"]["bronze"]
SILVER_DIR = PROJECT_ROOT / CONFIG["paths"]["silver"]
GOLD_DIR = PROJECT_ROOT / CONFIG["paths"]["gold"]

# Subcarpetas Base
BRONZE_INTERNAS_DIR = BRONZE_DIR / "internas"
BRONZE_EXTERNAS_DIR = BRONZE_DIR / "externas"
BRONZE_INVESTIGACION_DIR = BRONZE_DIR / "investigacion"

def ensure_base_directories():
    """Garantiza la existencia de las capas base del Lakehouse."""
    base_folders = [
        DATA_DIR,
        BRONZE_DIR,
        BRONZE_INTERNAS_DIR,
        BRONZE_EXTERNAS_DIR,
        BRONZE_INVESTIGACION_DIR,
        SILVER_DIR,
        GOLD_DIR
    ]
    for folder in base_folders:
        folder.mkdir(parents=True, exist_ok=True)

def get_external_bronze_dir(source_name: str) -> Path:
    """
    Construye y crea dinámicamente la carpeta para cualquier fuente externa.
    Uso: get_external_bronze_dir('enemdu') -> data/bronze/externas/enemdu
    """
    target_dir = BRONZE_EXTERNAS_DIR / source_name.lower().strip()
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir

def get_domain_silver_dir(domain_name: str) -> Path:
    """
    Construye y crea dinámicamente la carpeta de la capa Silver para un dominio.
    Uso: get_domain_silver_dir('enemdu') -> data/silver/enemdu
    """
    target_dir = SILVER_DIR / domain_name.lower().strip()
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir

# Ejecutar verificación básica al importar el módulo
ensure_base_directories()


class Config:
    """Compatibilidad para los notebooks de notebooks/01_docentes/, que importan
    `from config import Config` y esperan rutas de archivo concretas (no solo
    directorios). Reutiliza las constantes de arriba, no las recalcula."""

    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = DATA_DIR
    BRONZE_DIR = BRONZE_DIR
    BRONZE_INTERNAS = BRONZE_INTERNAS_DIR
    BRONZE_EXTERNAS = BRONZE_EXTERNAS_DIR
    BRONZE_INVESTIGACION = BRONZE_INVESTIGACION_DIR
    SILVER_DIR = SILVER_DIR
    GOLD_DIR = GOLD_DIR

    # Archivos fuente (Bronze)
    GTH_FILE = BRONZE_INTERNAS_DIR / "MATRIZ_ENVIADA_2.xlsx"
    ANALITICA_FILE = BRONZE_INTERNAS_DIR / "docentes_titulo_unesco.xlsx"
    DSPACE_FILE = BRONZE_INTERNAS_DIR / "BIBLIOTECA_DSPACE.xlsx"
    INVESTIGACION_FILE = BRONZE_INVESTIGACION_DIR / "investigadores_raw.xlsx"

    # Salidas Silver
    CATRASTRO_DOCENTES = SILVER_DIR / "catastro_docentes.parquet"
    TESIS_SILVER = SILVER_DIR / "tesis_silver.parquet"
    ARTICULOS_SILVER = SILVER_DIR / "articulos_silver.parquet"
    PUBLICACIONES_SILVER = SILVER_DIR / "publicaciones_silver.parquet"
    INVESTIGADORES_SILVER = SILVER_DIR / "investigadores.parquet"

    # Hojas del Excel de DSpace
    DSPACE_SHEETS = {
        "tesis": "tesis",
        "articulos": "art_docentes",
        "publicaciones": "publicaciones",
    }

    # Constantes de negocio (fuzzy matching por cédula)
    COL_CEDULA_GTH = "CEDULA"
    COL_CEDULA_ANALITICA = "NUMERO_DOCUMENTO"
    COL_CEDULA_NORM = "CEDULA_NORM"
    AÑO_CORTE_TESIS = 2020
    FUZZY_THRESHOLD = 85

    @classmethod
    def ensure_directories(cls):
        ensure_base_directories()
        print("✅ Directorios del proyecto verificados")

    @classmethod
    def verify_bronze_files(cls):
        files = {"GTH": cls.GTH_FILE, "Analítica": cls.ANALITICA_FILE, "DSpace": cls.DSPACE_FILE}
        for name, filepath in files.items():
            status = "✅" if filepath.exists() else "❌"
            print(f"{status} {name}: {filepath}")