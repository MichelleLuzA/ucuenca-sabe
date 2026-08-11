import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation  # ¡CORREGIDO!
from datetime import datetime
import os

# ============================================================
# CONFIGURACIÓN DE COLORES INSTITUCIONALES UCUENCA
# ============================================================
COLOR_AZUL_OSCURO = "003366"
COLOR_AZUL_CLARO = "E6F0FA"
COLOR_AZUL_MUY_CLARO = "F2F7FC"
COLOR_GRIS_ALTERNO = "F7FAFD"
COLOR_AMARILLO_LISTA = "FFF9E6"
COLOR_BLANCO = "FFFFFF"
COLOR_GRIS_BORDE = "D0D0D0"
COLOR_NEGRO = "1A1A1A"
COLOR_ROJO_ADVERTENCIA = "FFE6E6"

# ============================================================
# DEFINIR LISTAS DE VALORES (para validación)
# ============================================================
CATEGORIAS = [
    "Ingeniería y arquitectura",
    "Gestión empresarial",
    "Gestión de proyectos I+D+i",
    "Gestión de la Innovación",
    "Gestión de Fondos de Capital de Riesgo"
]

SUBCATEGORIAS = {
    "Ingeniería y arquitectura": [
        "Fiscalización de obras de infraestructura",
        "Diseños arquitectónicos",
        "Diseños de obras de infraestructura",
        "Estudios de ingeniería",
        "Otros"
    ],
    "Gestión empresarial": [
        "Estudios de costos y tarifas públicas",
        "Asesoría empresarial",
        "Estudios de talento humano",
        "Estudios de movilidad",
        "Planificación territorial",
        "Evaluaciones técnicas",
        "Evaluaciones económicas y financieras",
        "Otros"
    ],
    "Gestión de proyectos I+D+i": [
        "Gestión administrativa financiera de programas y proyectos de I+D+i públicos, privados provenientes de fondos nacionales e internacionales",
        "Otros"
    ],
    "Gestión de la Innovación": [
        "Diseño e implementación de centros de innovación y emprendimiento públicos y privados",
        "Otros"
    ],
    "Gestión de Fondos de Capital de Riesgo": [
        "Diseño de fondos de capital de riesgo públicos y privados",
        "Administración de fondos de capital de riesgo (acreditación SENESCYT)",
        "Otros"
    ]
}

SECTORES = ["Público", "Privado", "Mixto"]
ACTIVIDADES = ["Construcción", "Educación", "Salud", "Energía", "Infraestructura", "Gobierno", "Banca/Finanzas", "Tecnología", "Otro"]
TIPOS_RETENCION = ["IVA", "Renta", "Exento"]

# ============================================================
# CREAR DATOS DE EJEMPLO (5 contratos)
# ============================================================
data = {
    "id_contrato": ["CON-2026-001", "CON-2026-002", "CON-2026-003", "CON-2026-004", "CON-2026-005"],
    "objeto_contrato": [
        "Fiscalización de obra vial en Cuenca",
        "Diseño de centro de innovación tecnológica",
        "Estudio de costos y tarifas públicas",
        "Gestión de proyecto I+D+i con fondos internacionales",
        "Diseño de fondos de capital de riesgo"
    ],
    "fecha_firma": ["15/05/2026", "10/02/2026", "20/03/2026", "05/01/2026", "01/07/2026"],
    "fecha_inicio": ["01/06/2026", "01/03/2026", "01/04/2026", "15/01/2026", "15/07/2026"],
    "fecha_fin": ["31/12/2026", "30/11/2026", "30/09/2026", "31/12/2027", "31/12/2026"],
    "monto_total": [45000.00, 120000.00, 35000.00, 250000.00, 80000.00],
    "porcentaje_retencion": [8, 5, 10, 0, 7],
    "tipo_retencion": ["IVA", "Renta", "IVA", "Exento", "IVA"],
    "id_cliente": ["CLI-001", "CLI-002", "CLI-003", "CLI-004", "CLI-005"],
    "razon_social_cliente": [
        "Constructora ABC S.A.",
        "Ministerio de Innovación",
        "Empresa Eléctrica Regional",
        "SENESCYT",
        "Banco de Desarrollo"
    ],
    "sector_cliente": ["Privado", "Público", "Mixto", "Público", "Privado"],
    "actividad_cliente": ["Construcción", "Gobierno", "Energía", "Educación", "Banca/Finanzas"],
    "categoria_servicio_1": [
        "Ingeniería y arquitectura", 
        "Gestión de la Innovación", 
        "Gestión empresarial", 
        "Gestión de proyectos I+D+i", 
        "Gestión de Fondos de Capital de Riesgo"
    ],
    "subcategoria_servicio_1": [
        "Fiscalización de obras de infraestructura",
        "Diseño e implementación de centros de innovación y emprendimiento públicos y privados",
        "Estudios de costos y tarifas públicas",
        "Gestión administrativa financiera de programas y proyectos de I+D+i públicos, privados provenientes de fondos nacionales e internacionales",
        "Diseño de fondos de capital de riesgo públicos y privados"
    ],
    "categoria_servicio_2": ["", "Gestión de Fondos de Capital de Riesgo", "", "Gestión de Fondos de Capital de Riesgo", ""],
    "subcategoria_servicio_2": [
        "", 
        "Administración de fondos de capital de riesgo (acreditación SENESCYT)", 
        "", 
        "Administración de fondos de capital de riesgo (acreditación SENESCYT)", 
        ""
    ]
}

df = pd.DataFrame(data)

# ============================================================
# CREAR ARCHIVO EXCEL CON openpyxl
# ============================================================
wb = Workbook()
ws = wb.active
ws.title = "Contratos UCUENCA EP"

# ============================================================
# 1. TÍTULO
# ============================================================
ws.merge_cells('A1:P1')
titulo = ws['A1']
titulo.value = "🏛️ MATRIZ DE CONTRATOS - UCUENCA EP"
titulo.font = Font(name='Calibri', size=18, bold=True, color=COLOR_AZUL_OSCURO)
titulo.alignment = Alignment(horizontal='center', vertical='center')
titulo.fill = PatternFill(start_color=COLOR_AZUL_CLARO, end_color=COLOR_AZUL_CLARO, fill_type='solid')

ws.merge_cells('A2:P2')
subtitulo = ws['A2']
subtitulo.value = "📋 Registro de servicios contratados por cliente (Máximo 2 servicios por contrato)"
subtitulo.font = Font(name='Calibri', size=11, color=COLOR_AZUL_OSCURO)
subtitulo.alignment = Alignment(horizontal='center', vertical='center')
subtitulo.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')

# ============================================================
# 2. ENCABEZADOS (fila 4)
# ============================================================
headers = [
    "ID Contrato", "Objeto", "Fecha Firma", "Fecha Inicio", "Fecha Fin",
    "Monto ($)", "% Ret.", "Tipo Ret.", "ID Cliente", "Razón Social",
    "Sector", "Actividad",
    "Cat. Servicio 1", "Subcat. Servicio 1",
    "Cat. Servicio 2", "Subcat. Servicio 2"
]

header_row = 4
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=header_row, column=col, value=header)
    cell.font = Font(name='Calibri', size=10, bold=True, color=COLOR_BLANCO)
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell.fill = PatternFill(start_color=COLOR_AZUL_OSCURO, end_color=COLOR_AZUL_OSCURO, fill_type='solid')
    cell.border = Border(
        left=Side(style='thin', color=COLOR_AZUL_OSCURO),
        right=Side(style='thin', color=COLOR_AZUL_OSCURO),
        top=Side(style='thin', color=COLOR_AZUL_OSCURO),
        bottom=Side(style='thin', color=COLOR_AZUL_OSCURO)
    )

# ============================================================
# 3. ESCRIBIR DATOS
# ============================================================
for row_idx, row_data in enumerate(df.values, start=header_row + 1):
    for col_idx, value in enumerate(row_data, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        
        # Formato según tipo de columna
        if col_idx == 6:  # Monto
            cell.number_format = '#,##0.00'
        elif col_idx == 7:  # % Retención
            if value is not None and value != '':
                cell.number_format = '0"%"'
        elif col_idx in [3, 4, 5]:  # Fechas
            if value and value != '':
                try:
                    # Convertir string a fecha
                    fecha = datetime.strptime(str(value), '%d/%m/%Y')
                    cell.value = fecha
                    cell.number_format = 'DD/MM/YYYY'
                except:
                    pass
        
        # Estilo de celda según tipo de columna
        if col_idx in [2, 10]:  # Objeto y Razón Social (texto libre)
            cell.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        elif col_idx in [8, 11, 12, 13, 14, 15, 16]:  # Columnas con listas desplegables
            cell.fill = PatternFill(start_color=COLOR_AMARILLO_LISTA, end_color=COLOR_AMARILLO_LISTA, fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            # Borde especial para listas
            cell.border = Border(
                left=Side(style='medium', color=COLOR_AZUL_OSCURO),
                right=Side(style='medium', color=COLOR_AZUL_OSCURO),
                top=Side(style='medium', color=COLOR_AZUL_OSCURO),
                bottom=Side(style='medium', color=COLOR_AZUL_OSCURO)
            )
        else:
            # Color alternado por fila
            if row_idx % 2 == 0:
                cell.fill = PatternFill(start_color=COLOR_GRIS_ALTERNO, end_color=COLOR_GRIS_ALTERNO, fill_type='solid')
            else:
                cell.fill = PatternFill(start_color=COLOR_BLANCO, end_color=COLOR_BLANCO, fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Bordes estándar para todas las celdas (que no sean listas)
        if col_idx not in [8, 11, 12, 13, 14, 15, 16]:
            cell.border = Border(
                left=Side(style='thin', color=COLOR_GRIS_BORDE),
                right=Side(style='thin', color=COLOR_GRIS_BORDE),
                top=Side(style='thin', color=COLOR_GRIS_BORDE),
                bottom=Side(style='thin', color=COLOR_GRIS_BORDE)
            )

# ============================================================
# 4. AGREGAR VALIDACIÓN DE DATOS (LISTAS DESPLEGABLES)
# ============================================================
# Función helper para crear validaciones
def crear_validacion(lista, mensaje_error):
    dv = DataValidation(
        type="list",
        formula1=f'"{",".join(lista)}"',
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Valor no válido",
        error=mensaje_error
    )
    return dv

# Columna Tipo Retención (columna 8 - H)
dv_tipo = crear_validacion(TIPOS_RETENCION, "Seleccione: IVA, Renta o Exento")
ws.add_data_validation(dv_tipo)
dv_tipo.add('H5:H1000')

# Columna Sector (columna 11 - K)
dv_sector = crear_validacion(SECTORES, "Seleccione: Público, Privado o Mixto")
ws.add_data_validation(dv_sector)
dv_sector.add('K5:K1000')

# Columna Actividad (columna 12 - L)
dv_actividad = crear_validacion(ACTIVIDADES, "Seleccione una actividad de la lista")
ws.add_data_validation(dv_actividad)
dv_actividad.add('L5:L1000')

# Columna Categoría Servicio 1 (columna 13 - M)
dv_cat1 = crear_validacion(CATEGORIAS, "Seleccione una categoría de la lista")
ws.add_data_validation(dv_cat1)
dv_cat1.add('M5:M1000')

# Columna Categoría Servicio 2 (columna 15 - O)
dv_cat2 = crear_validacion(CATEGORIAS, "Seleccione una categoría de la lista")
ws.add_data_validation(dv_cat2)
dv_cat2.add('O5:O1000')

# ============================================================
# 5. NOTA DE VALIDACIÓN
# ============================================================
nota_row = header_row + len(df) + 3
ws.merge_cells(f'A{nota_row}:P{nota_row}')
nota = ws[f'A{nota_row}']
nota.value = "⚠️ IMPORTANTE: Las columnas con fondo AMARILLO deben llenarse EXCLUSIVAMENTE seleccionando valores de las listas desplegables."
nota.font = Font(name='Calibri', size=9, bold=True, color=COLOR_AZUL_OSCURO)
nota.alignment = Alignment(horizontal='left', vertical='center')
nota.fill = PatternFill(start_color=COLOR_ROJO_ADVERTENCIA, end_color=COLOR_ROJO_ADVERTENCIA, fill_type='solid')

# ============================================================
# 6. LEYENDA DE COLORES
# ============================================================
leyenda_row = nota_row + 2
leyenda_items = [
    ("🔵 Azul oscuro", COLOR_AZUL_OSCURO, "Encabezados"),
    ("⬜ Blanco", COLOR_BLANCO, "Datos normales"),
    ("⬜ Gris", COLOR_GRIS_ALTERNO, "Datos alternos"),
    ("🟨 Amarillo", COLOR_AMARILLO_LISTA, "Listas desplegables"),
    ("🟦 Azul claro", COLOR_AZUL_MUY_CLARO, "Texto libre")
]

for i, (label, color, desc) in enumerate(leyenda_items):
    col = i * 3 + 1
    # Celda de color
    cell_color = ws.cell(row=leyenda_row, column=col)
    cell_color.fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
    cell_color.border = Border(
        left=Side(style='thin', color=COLOR_GRIS_BORDE),
        right=Side(style='thin', color=COLOR_GRIS_BORDE),
        top=Side(style='thin', color=COLOR_GRIS_BORDE),
        bottom=Side(style='thin', color=COLOR_GRIS_BORDE)
    )
    cell_color.alignment = Alignment(horizontal='center', vertical='center')
    # Texto descriptivo
    cell_text = ws.cell(row=leyenda_row, column=col+1, value=f"{label}: {desc}")
    cell_text.font = Font(name='Calibri', size=8, color=COLOR_NEGRO)
    cell_text.alignment = Alignment(horizontal='left', vertical='center')

# ============================================================
# 7. AJUSTAR ANCHO DE COLUMNAS
# ============================================================
column_widths = {
    'A': 15, 'B': 45, 'C': 14, 'D': 14, 'E': 14,
    'F': 14, 'G': 10, 'H': 14, 'I': 14, 'J': 35,
    'K': 14, 'L': 20, 'M': 30, 'N': 50, 'O': 30, 'P': 50
}
for col, width in column_widths.items():
    ws.column_dimensions[col].width = width

# ============================================================
# 8. CONGELAR PANELES (encabezados)
# ============================================================
ws.freeze_panes = 'A5'
# ============================================================
# HOJA DE INSTRUCTIVO
# ============================================================
def crear_hoja_instructivo(wb):
    ws_inst = wb.create_sheet("INSTRUCTIVO", 0)  # La pone primero
    ws_inst.sheet_view.showGridLines = False
    
    # Título principal
    ws_inst.merge_cells('A1:G1')
    titulo = ws_inst['A1']
    titulo.value = "📋 INSTRUCTIVO DE LLENADO - MATRIZ DE CONTRATOS"
    titulo.font = Font(name='Calibri', size=18, bold=True, color=COLOR_AZUL_OSCURO)
    titulo.alignment = Alignment(horizontal='center', vertical='center')
    titulo.fill = PatternFill(start_color=COLOR_AZUL_CLARO, end_color=COLOR_AZUL_CLARO, fill_type='solid')
    
    # Subtítulo
    ws_inst.merge_cells('A2:G2')
    subt = ws_inst['A2']
    subt.value = "Instrucciones para el llenado de la matriz (hoja 'Contratos UCUENCA EP')"
    subt.font = Font(name='Calibri', size=11, color=COLOR_AZUL_OSCURO)
    subt.alignment = Alignment(horizontal='center', vertical='center')
    subt.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')
    
    # ============================================================
    # SECCIÓN 1: REGLAS BÁSICAS
    # ============================================================
    row = 4
    ws_inst[f'A{row}'] = "🔹 REGLAS BÁSICAS"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=COLOR_AZUL_OSCURO)
    row += 1
    reglas = [
        "• Complete UNA FILA por cada contrato.",
        "• Máximo 2 servicios por contrato (use las columnas Servicio 1 y Servicio 2).",
        "• No modifique los encabezados (fila 4) ni las fórmulas.",
        "• Las columnas con fondo AMARILLO tienen listas desplegables: SELECCIONE un valor.",
        "• Las columnas con fondo AZUL CLARO son de TEXTO LIBRE (escriba lo que corresponda).",
        "• Las columnas con fondo BLANCO/GRIS son DATOS ESTRUCTURADOS (fechas, montos, etc.)."
    ]
    for regla in reglas:
        ws_inst[f'A{row}'] = regla
        ws_inst[f'A{row}'].font = Font(name='Calibri', size=10)
        row += 1
    row += 1
    
    # ============================================================
    # SECCIÓN 2: EXPLICACIÓN DE COLUMNAS
    # ============================================================
    ws_inst[f'A{row}'] = "🔹 EXPLICACIÓN DE COLUMNAS"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=COLOR_AZUL_OSCURO)
    row += 1
    
    # Encabezados de la tabla
    headers_cols = ["Columna", "Tipo", "Qué llenar", "Ejemplo"]
    for col, header in enumerate(headers_cols, 1):
        cell = ws_inst.cell(row=row, column=col, value=header)
        cell.font = Font(name='Calibri', size=10, bold=True, color=COLOR_BLANCO)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = PatternFill(start_color=COLOR_AZUL_OSCURO, end_color=COLOR_AZUL_OSCURO, fill_type='solid')
    row += 1
    
    # Datos de columnas (16 columnas)
    columnas_info = [
        ("A: ID Contrato", "Texto", "Identificador único", "CON-2026-001"),
        ("B: Objeto", "Texto libre", "Descripción del contrato", "Fiscalización de obra vial"),
        ("C-E: Fechas", "Fecha", "DD/MM/YYYY", "15/05/2026"),
        ("F: Monto", "Número", "Valor en dólares (sin signos)", "45000"),
        ("G: % Retención", "Número", "Porcentaje (ej: 8 para 8%)", "8"),
        ("H: Tipo Ret.", "Lista", "Seleccione de la lista", "IVA"),
        ("I: ID Cliente", "Texto", "Código del cliente", "CLI-001"),
        ("J: Razón Social", "Texto libre", "Nombre del cliente", "Constructora ABC"),
        ("K: Sector", "Lista", "Público / Privado / Mixto", "Privado"),
        ("L: Actividad", "Lista", "Sector económico", "Construcción"),
        ("M: Cat. Servicio 1", "Lista", "Categoría del servicio principal", "Ingeniería y arquitectura"),
        ("N: Subcat. Servicio 1", "Lista", "Subcategoría del servicio principal", "Fiscalización de obras"),
        ("O: Cat. Servicio 2", "Lista", "Categoría del 2do servicio (opcional)", ""),
        ("P: Subcat. Servicio 2", "Lista", "Subcategoría del 2do servicio (opcional)", "")
    ]
    
    for info in columnas_info:
        for col_idx, val in enumerate(info, 1):
            cell = ws_inst.cell(row=row, column=col_idx, value=val)
            cell.font = Font(name='Calibri', size=9)
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            # Color según tipo de columna
            if "Lista" in info[1]:
                cell.fill = PatternFill(start_color=COLOR_AMARILLO_LISTA, end_color=COLOR_AMARILLO_LISTA, fill_type='solid')
            elif "Texto libre" in info[1]:
                cell.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')
            else:
                if row % 2 == 0:
                    cell.fill = PatternFill(start_color=COLOR_GRIS_ALTERNO, end_color=COLOR_GRIS_ALTERNO, fill_type='solid')
                else:
                    cell.fill = PatternFill(start_color=COLOR_BLANCO, end_color=COLOR_BLANCO, fill_type='solid')
            cell.border = Border(
                left=Side(style='thin', color=COLOR_GRIS_BORDE),
                right=Side(style='thin', color=COLOR_GRIS_BORDE),
                top=Side(style='thin', color=COLOR_GRIS_BORDE),
                bottom=Side(style='thin', color=COLOR_GRIS_BORDE)
            )
        row += 1
    row += 1
    
    # ============================================================
    # SECCIÓN 3: LISTAS DE VALORES PERMITIDOS
    # ============================================================
    ws_inst[f'A{row}'] = "🔹 LISTAS DE VALORES PERMITIDOS (para columnas con lista)"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=COLOR_AZUL_OSCURO)
    row += 1
    
    # Tabla de listas
    listas_info = [
        ("Categorías (Nivel 1)", "\n".join(CATEGORIAS)),
        ("Sectores", "\n".join(SECTORES)),
        ("Actividades", "\n".join(ACTIVIDADES)),
        ("Tipos de Retención", "\n".join(TIPOS_RETENCION))
    ]
    
    # Encabezados de la tabla de listas
    for col, header in enumerate(["Lista", "Valores permitidos"], 1):
        cell = ws_inst.cell(row=row, column=col, value=header)
        cell.font = Font(name='Calibri', size=10, bold=True, color=COLOR_BLANCO)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.fill = PatternFill(start_color=COLOR_AZUL_OSCURO, end_color=COLOR_AZUL_OSCURO, fill_type='solid')
    row += 1
    
    for lista, valores in listas_info:
        cell1 = ws_inst.cell(row=row, column=1, value=lista)
        cell1.font = Font(name='Calibri', size=9, bold=True)
        cell1.alignment = Alignment(horizontal='left', vertical='center')
        cell1.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')
        
        cell2 = ws_inst.cell(row=row, column=2, value=valores)
        cell2.font = Font(name='Calibri', size=9)
        cell2.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        cell2.fill = PatternFill(start_color=COLOR_BLANCO, end_color=COLOR_BLANCO, fill_type='solid')
        
        # Borde
        for col in [1, 2]:
            ws_inst.cell(row=row, column=col).border = Border(
                left=Side(style='thin', color=COLOR_GRIS_BORDE),
                right=Side(style='thin', color=COLOR_GRIS_BORDE),
                top=Side(style='thin', color=COLOR_GRIS_BORDE),
                bottom=Side(style='thin', color=COLOR_GRIS_BORDE)
            )
        row += 1
    row += 1
    
    # ============================================================
    # SECCIÓN 4: EJEMPLO VISUAL
    # ============================================================
    ws_inst[f'A{row}'] = "🔹 EJEMPLO DE LLENADO (fila de la hoja 'Contratos')"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=COLOR_AZUL_OSCURO)
    row += 1
    
    # Copiar la primera fila de ejemplo (la de CON-2026-001) con colores
    ejemplo_data = [
        "CON-2026-001", "Fiscalización de obra vial", "15/05/2026", "01/06/2026", "31/12/2026",
        "45,000.00", "8%", "IVA", "CLI-001", "Constructora ABC", "Privado", "Construcción",
        "Ingeniería y arquitectura", "Fiscalización de obras", "", ""
    ]
    for col_idx, val in enumerate(ejemplo_data, 1):
        cell = ws_inst.cell(row=row, column=col_idx, value=val)
        cell.font = Font(name='Calibri', size=9)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        # Color según columna (simulando la hoja de contratos)
        if col_idx in [2, 10]:  # texto libre
            cell.fill = PatternFill(start_color=COLOR_AZUL_MUY_CLARO, end_color=COLOR_AZUL_MUY_CLARO, fill_type='solid')
        elif col_idx in [8, 11, 12, 13, 14, 15, 16]:  # listas
            cell.fill = PatternFill(start_color=COLOR_AMARILLO_LISTA, end_color=COLOR_AMARILLO_LISTA, fill_type='solid')
        else:
            cell.fill = PatternFill(start_color=COLOR_BLANCO, end_color=COLOR_BLANCO, fill_type='solid')
        cell.border = Border(
            left=Side(style='thin', color=COLOR_GRIS_BORDE),
            right=Side(style='thin', color=COLOR_GRIS_BORDE),
            top=Side(style='thin', color=COLOR_GRIS_BORDE),
            bottom=Side(style='thin', color=COLOR_GRIS_BORDE)
        )
    row += 2
    
    # ============================================================
    # SECCIÓN 5: CONTACTO
    # ============================================================
    ws_inst[f'A{row}'] = "🔹 ¿DUDAS? CONTACTO"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=12, bold=True, color=COLOR_AZUL_OSCURO)
    row += 1
    ws_inst[f'A{row}'] = "Si tiene preguntas sobre el llenado, comuníquese con:"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=10)
    row += 1
    ws_inst[f'A{row}'] = "📧 [Tu correo]  |  📞 [Tu teléfono]  |  💬 [Tu canal de comunicación]"
    ws_inst[f'A{row}'].font = Font(name='Calibri', size=10, bold=True, color=COLOR_AZUL_OSCURO)
    ws_inst[f'A{row}'].fill = PatternFill(start_color=COLOR_AZUL_CLARO, end_color=COLOR_AZUL_CLARO, fill_type='solid')
    
    # Ajustar ancho de columnas en hoja instructivo
    ws_inst.column_dimensions['A'].width = 25
    ws_inst.column_dimensions['B'].width = 40
    ws_inst.column_dimensions['C'].width = 20
    ws_inst.column_dimensions['D'].width = 20
    ws_inst.column_dimensions['E'].width = 20
    ws_inst.column_dimensions['F'].width = 20
    ws_inst.column_dimensions['G'].width = 20
    
    return ws_inst
crear_hoja_instructivo(wb)
# ============================================================
# 9. GUARDAR ARCHIVO
# ============================================================
nombre_archivo = "matriz_contratos_ucuenca.xlsx"
wb.save(nombre_archivo)
print(f"✅ Excel generado exitosamente: {nombre_archivo}")
print(f"📁 Ubicación: {os.path.abspath(nombre_archivo)}")
print("\n📊 Características del archivo:")
print("  • 16 columnas (2 servicios por contrato)")
print("  • Listas desplegables en columnas amarillas")
print("  • Colores institucionales UCUENCA (#003366)")
print("  • Formato de montos, fechas y porcentajes")
print("  • 5 filas de ejemplo para referencia")