# src/processing/enemdu_schema_analyzer.py
"""
Analiza automáticamente los diccionarios XLSX y extrae esquemas
¡Escalable! Funciona con cualquier año nuevo sin cambios
"""

import pandas as pd
from pathlib import Path
import re
from typing import Dict, List, Set, Optional
import json
from datetime import datetime

class ENEMDUSchemaAnalyzer:
    """Analiza y extrae esquemas de ENEMDU desde los diccionarios XLSX"""
    
    def __init__(self, bronze_dir: Path = None):
        self.bronze_dir = bronze_dir or Path("data/bronze/externas/enemdu")
        self.dicts_dir = self.bronze_dir / "diccionarios"
        self.data_dir = self.bronze_dir / "microdatos_csv"
        self.reports_dir = Path("reports/schemas")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.schemas: Dict[int, List[str]] = {}
        self.common_columns: Set[str] = set()
        self.year_specific: Dict[int, List[str]] = {}
        self.column_mapping: Dict[str, str] = {}
        
    def analyze_all(self) -> Dict[int, List[str]]:
        """Analiza TODOS los diccionarios disponibles"""
        print("🔍 ANALIZANDO ESQUEMAS DE ENEMDU...")
        print("=" * 60)
        
        # 1. Buscar todos los diccionarios XLSX
        xlsx_files = list(self.dicts_dir.glob("*.xlsx"))
        
        if not xlsx_files:
            raise FileNotFoundError(f"No se encontraron diccionarios en {self.dicts_dir}")
        
        print(f"📁 Encontrados {len(xlsx_files)} diccionarios")
        
        # 2. Procesar cada diccionario
        for xlsx_file in xlsx_files:
            year = self._extract_year(xlsx_file.name)
            if not year:
                continue
                
            columns = self._extract_columns_from_dictionary(xlsx_file)
            if columns:
                self.schemas[year] = columns
                print(f"   ✅ {year}: {len(columns)} columnas")
        
        # 3. Encontrar columnas comunes
        if self.schemas:
            all_columns_sets = [set(cols) for cols in self.schemas.values()]
            self.common_columns = set.intersection(*all_columns_sets)
            
            # Columnas específicas por año
            for year, cols in self.schemas.items():
                cols_set = set(cols)
                specific = cols_set - self.common_columns
                if specific:
                    self.year_specific[year] = list(specific)
        
        # 4. Generar reportes
        self._generate_reports()
        
        return self.schemas
    
    def _extract_columns_from_dictionary(self, xlsx_file: Path) -> List[str]:
        """Extrae nombres de columnas de un diccionario XLSX"""
        try:
            # Leer el archivo Excel
            df = pd.read_excel(xlsx_file, header=None)
            
            # Buscar la fila donde empiezan los nombres de columnas
            start_row = None
            for idx, row in df.iterrows():
                if isinstance(row.iloc[0], str):
                    row_text = row.iloc[0].lower()
                    if 'nombre del campo' in row_text or 'campo' in row_text:
                        start_row = idx + 1
                        break
            
            if start_row is None:
                # Si no encuentra, buscar primera fila con datos
                for idx, row in df.iterrows():
                    if isinstance(row.iloc[0], str) and len(str(row.iloc[0])) > 0:
                        if not any(header in str(row.iloc[0]).lower() for header in ['institución', 'identificador', 'documento']):
                            start_row = idx
                            break
            
            if start_row is None:
                print(f"   ⚠️ No se pudo encontrar inicio de columnas en {xlsx_file.name}")
                return []
            
            # Extraer columnas
            columns_df = df.iloc[start_row:].copy()
            columns_df.columns = ['columna', 'descripcion']
            
            # Limpiar y obtener nombres de columnas
            column_names = []
            for col in columns_df['columna'].dropna():
                col_str = str(col).strip()
                if col_str and col_str.lower() not in ['nan', 'none', '']:
                    column_names.append(col_str)
            
            return column_names
            
        except Exception as e:
            print(f"   ❌ Error procesando {xlsx_file.name}: {e}")
            return []
    
    def _extract_year(self, filename: str) -> Optional[int]:
        """Extrae el año del nombre del archivo"""
        match = re.search(r'(\d{4})', filename)
        return int(match.group(1)) if match else None
    
    def _generate_reports(self):
        """Genera reportes detallados de los esquemas"""
        # 1. Reporte principal
        report_path = self.reports_dir / f"schema_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        
        report_data = {
            'analysis_date': datetime.now().isoformat(),
            'years_analyzed': sorted(self.schemas.keys()),
            'total_columns_per_year': {year: len(cols) for year, cols in self.schemas.items()},
            'common_columns': sorted(list(self.common_columns)),
            'year_specific_columns': {
                str(year): sorted(cols) for year, cols in self.year_specific.items()
            },
            'all_schemas': {str(year): cols for year, cols in self.schemas.items()}
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Reporte guardado: {report_path}")
        
        # 2. Reporte legible para humanos
        txt_path = self.reports_dir / f"schema_analysis_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ANÁLISIS DE ESQUEMAS ENEMDU\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Fecha análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Años analizados: {sorted(self.schemas.keys())}\n\n")
            
            f.write("RESUMEN POR AÑO:\n")
            f.write("-" * 40 + "\n")
            for year, cols in sorted(self.schemas.items()):
                f.write(f"{year}: {len(cols)} columnas\n")
            
            f.write(f"\n\nCOLUMNAS COMUNES (TODOS LOS AÑOS): {len(self.common_columns)}\n")
            f.write("-" * 40 + "\n")
            for col in sorted(self.common_columns):
                f.write(f"  • {col}\n")
            
            f.write(f"\n\nCOLUMNAS ESPECÍFICAS POR AÑO:\n")
            f.write("-" * 40 + "\n")
            for year, cols in sorted(self.year_specific.items()):
                f.write(f"\n{year} ({len(cols)} columnas únicas):\n")
                for col in sorted(cols):
                    f.write(f"  • {col}\n")
        
        print(f"📄 Reporte legible guardado: {txt_path}")
    
    def get_relevant_columns(self, keywords: List[str] = None) -> Dict[int, List[str]]:
        """Filtra columnas relevantes según keywords"""
        if keywords is None:
            keywords = [
                'empleo', 'trabajo', 'ocupacion', 'ingreso', 'horas',
                'educacion', 'titulo', 'profesion', 'salario', 'remuneracion'
            ]
        
        relevant = {}
        for year, cols in self.schemas.items():
            relevant[year] = [
                col for col in cols 
                if any(keyword in col.lower() for keyword in keywords)
            ]
        
        return relevant