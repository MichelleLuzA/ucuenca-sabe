# ==========================================
# src/config.py - CONFIGURACIÓN CENTRALIZADA
# ==========================================
"""
Configuración centralizada del proyecto ucuenca-sabe.
Todas las rutas y constantes se definen AQUÍ.
Los notebooks importan desde aquí.
"""

from pathlib import Path
import os

class Config:
    """Configuración global del proyecto"""
    
    # ==========================================
    # RUTAS BASE
    # ==========================================
    @staticmethod
    def get_project_root():
        """Encuentra la raíz del proyecto automáticamente"""
        current = Path.cwd()
        while current != current.parent:
            if (current / 'data').exists() and (current / 'src').exists():
                return current
            current = current.parent
        raise FileNotFoundError("❌ No se encontró la raíz del proyecto")
    
    # Raíz del proyecto
    PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Sube desde src/ a raíz
    
    # ==========================================
    # CAPAS DEL LAKEHOUSE
    # ==========================================
    DATA_DIR = PROJECT_ROOT / 'data'
    BRONZE_DIR = DATA_DIR / 'bronze'
    BRONZE_INTERNAS = BRONZE_DIR / 'internas'
    BRONZE_EXTERNAS = BRONZE_DIR / 'externas'
    SILVER_DIR = DATA_DIR / 'silver'
    GOLD_DIR = DATA_DIR / 'gold'
    
    # ==========================================
    # ARCHIVOS FUENTE (BRONZE)
    # ==========================================
    GTH_FILE = BRONZE_INTERNAS / "MATRIZ_ENVIADA_2.xlsx"
    ANALITICA_FILE = BRONZE_INTERNAS / "docentes_titulo_unesco.xlsx"
    DSPACE_FILE = BRONZE_INTERNAS / "BIBLIOTECA_DSPACE.xlsx"
    
    # ==========================================
    # ARCHIVOS DE SALIDA (SILVER)
    # ==========================================
    CATRASTRO_DOCENTES = SILVER_DIR / "catastro_docentes.parquet"
    PRODUCCION_DSPACE = SILVER_DIR / "produccion_dspace.parquet"
    TESIS_DSPACE = SILVER_DIR / "tesis_dspace.parquet"
    
    # ==========================================
    # ARCHIVOS GOLD
    # ==========================================
    KPI_RECTORADO = GOLD_DIR / "kpi_rectorado.csv"
    
    # ==========================================
    # CONSTANTES DEL NEGOCIO
    # ==========================================
    COL_CEDULA_GTH = "CEDULA"
    COL_CEDULA_ANALITICA = "NUMERO_DOCUMENTO"
    COL_CEDULA_NORM = "CEDULA_NORM"
    
    AÑO_CORTE_TESIS = 2020  # Solo tesis desde este año
    FUZZY_THRESHOLD = 85    # Umbral para Fuzzy Matching
    
    # ==========================================
    # HOJAS DEL EXCEL DE DSPACE
    # ==========================================
    DSPACE_SHEETS = {
        'tesis': 'tesis',
        'articulos': 'art_docentes',
        'publicaciones': 'publicaciones'
    }
    
    # ==========================================
    # MÉTODOS ÚTILES
    # ==========================================
    @classmethod
    def ensure_directories(cls):
        """Crea todos los directorios necesarios"""
        directories = [
            cls.BRONZE_INTERNAS,
            cls.BRONZE_EXTERNAS,
            cls.SILVER_DIR,
            cls.GOLD_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        print("✅ Directorios del proyecto verificados")
    
    @classmethod
    def verify_bronze_files(cls):
        """Verifica que los archivos fuente existan"""
        files = {
            'GTH': cls.GTH_FILE,
            'Analítica': cls.ANALITICA_FILE,
            'DSpace': cls.DSPACE_FILE
        }
        for name, filepath in files.items():
            status = "✅" if filepath.exists() else "❌"
            print(f"{status} {name}: {filepath}")