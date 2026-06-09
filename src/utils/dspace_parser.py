# src/utils/dspace_parser.py
import re
import pandas as pd
import numpy as np

def ejecutar_parseo_dspace(series_metadatos):
    """
    Función Maestra de la Capa Silver Robustecida.
    Mapea de manera determinista cuartiles, clasificaciones UNESCO/Frascati,
    e IDs híbridos (Cédula/ORCID) en perfecta correspondencia con sus autores.
    """
    registros_parseados = []
    max_autores = 0  # Rastreador para la expansión dinámica de columnas
    
    for metadata_string in series_metadatos:
        if pd.isna(metadata_string):
            registros_parseados.append({})
            continue
            
        resultado = {}
        texto = str(metadata_string)
        
        # 1. Identificación del Tipo de Documento y Enfoque
        match_type = re.search(r'dc\.type:\s*([^|]+)', texto, re.IGNORECASE)
        tipo_doc = match_type.group(1).strip() if match_type else ''
        resultado['TIPO_DOCUMENTO_DSPACE'] = tipo_doc
        es_tesis = any(k in tipo_doc.lower() for k in ['thesis', 'tesis']) or 'dc.description.degree' in texto
        
        # 2. Extracción Cronológica (Retorna entero puro, previene flotantes)
        match_anho = re.search(r'(?:dc\.date\.issued|Previous\s+issue\s+date):\s*(\d{4})', texto, re.IGNORECASE)
        resultado['ANHO_DSPACE'] = int(match_anho.group(1)) if match_anho else None
        
        # 3. Títulos (Principal y Alternativo en Español si existe)
        match_tit = re.search(r'dc\.title:\s*([^|]+)', texto)
        resultado['TITULO_DSPACE'] = match_tit.group(1).strip() if match_tit else None
        
        match_alt = re.search(r'dc\.title\.alternative:\s*([^|]+)', texto)
        resultado['TITULO_ALTERNATIVE_DSPACE'] = match_alt.group(1).strip() if match_alt else None
        
        # 4. Indicadores de Calidad e Impacto Científico (Mapeo de tu muestra)
        match_cuartil = re.search(r'dc\.ucuenca\.cuartil:\s*([^|]+)', texto, re.IGNORECASE)
        resultado['CUARTIL_DSPACE'] = match_cuartil.group(1).strip().upper() if match_cuartil else None
        
        match_impacto = re.search(r'dc\.ucuenca\.factorimpacto:\s*([^|]+)', texto)
        resultado['FACTOR_IMPACTO_DSPACE'] = float(match_impacto.group(1).strip()) if match_impacto else None
        
        match_indice = re.search(r'dc\.ucuenca\.indicebibliografico:\s*([^|]+)', texto)
        resultado['INDICE_BIBLIOGRAFICO_DSPACE'] = match_indice.group(1).strip().upper() if match_indice else None
        
        # 5. Extracción Atómica de IDs Híbridos (Cédulas u ORCIDs)
        ids_encontrados = [id_art.strip() for id_art in re.findall(r'dc\.ucuenca\.idautor:\s*([^|]+?)(?:\s*\|\||$)', texto)]
        # Guardamos el primero como ID Principal de control
        resultado['ID_AUTOR_PRINCIPAL_DSPACE'] = ids_encontrados[0] if ids_encontrados else None
        
        # 6. Gestión de Autores y Directores por tipo de hoja
        autores = re.findall(r'dc\.contributor\.author:\s*([^|]+?)(?:\s*\|\||$)', texto)
        autores_limpios = [a.strip() for a in autores if a.strip()]
        
        if es_tesis:
            resultado['AUTOR_PRINCIPAL'] = autores_limpios[0] if autores_limpios else None
            match_director = re.search(r'dc\.contributor\.advisor:\s*([^|]+)', texto)
            resultado['DIRECTOR_TESIS'] = match_director.group(1).strip() if match_director else None
            resultado['ID_DIRECTOR_TESIS'] = ids_encontrados[1] if len(ids_encontrados) > 1 else None
        else:
            resultado['_autores_lista'] = autores_limpios
            resultado['_ids_lista'] = ids_encontrados
            if len(autores_limpios) > max_autores:
                max_autores = len(autores_limpios)
                
        # 7. Taxonomías de Áreas del Conocimiento (Estandarización Macro)
        # 7a. Línea UNESCO
        m_une_amp = re.search(r'dc\.ucuenca\.areaconocimientounescoamplio:\s*([^|]+)', texto)
        resultado['UNESCO_AMPLIO'] = m_une_amp.group(1).strip() if m_une_amp else None
        
        m_une_det = re.search(r'dc\.ucuenca\.areaconocimientounescodetallado:\s*([^|]+)', texto)
        resultado['UNESCO_DETALLADO'] = m_une_det.group(1).strip() if m_une_det else None
        
        m_une_esp = re.search(r'dc\.ucuenca\.areaconocimientounescoespecifico:\s*([^|]+)', texto)
        resultado['UNESCO_ESPECIFICO'] = m_une_esp.group(1).strip() if m_une_esp else None
        
        # 7b. Línea Frascati
        m_fra_amp = re.search(r'dc\.ucuenca\.areaconocimientofrascatiamplio:\s*([^|]+)', texto)
        resultado['FRASCATI_AMPLIO'] = m_fra_amp.group(1).strip() if m_fra_amp else None
        
        m_fra_det = re.search(r'dc\.ucuenca\.areaconocimientofrascatidetallado:\s*([^|]+)', texto)
        resultado['FRASCATI_DETALLADO'] = m_fra_det.group(1).strip() if m_fra_det else None
        
        m_fra_esp = re.search(r'dc\.ucuenca\.areaconocimientofrascatiespecifico:\s*([^|]+)', texto)
        resultado['FRASCATI_ESPECIFICO'] = m_fra_esp.group(1).strip() if m_fra_esp else None

        # 8. Palabras Clave y Resumen (NLP)
        subjects = re.findall(r'dc\.subject(?:\.[a-z]+)?:\s*([^|]+?)(?:\s*\|\||$)', texto)
        palabras_limpias = list(set([s.strip() for s in subjects if s.strip() and "::" not in s]))
        resultado['PALABRAS_CLAVE'] = ", ".join(palabras_limpias) if palabras_limpias else None
        
        match_desc = re.search(r'dc\.description(?:\.abstract)?:\s*([^|]+)', texto)
        if match_desc and not any(k in match_desc.group(1) for k in ["Made available", "Submitted by"]):
            resultado['RESUMEN_DSPACE'] = match_desc.group(1).strip()
        else:
            resultado['RESUMEN_DSPACE'] = None
            
        registros_parseados.append(resultado)
        
    # --- PROCESO DE EXPANSION MATRICIAL (AUTOR_N vs ID_AUTOR_N) ---
    df_resultado = pd.DataFrame(registros_parseados)
    
    # Forzar el año a tipo entero de Pandas que tolera nulos (Previene el .0 de flotantes)
    if 'ANHO_DSPACE' in df_resultado.columns:
        df_resultado['ANHO_DSPACE'] = df_resultado['ANHO_DSPACE'].astype('Int64')
    
    if '_autores_lista' in df_resultado.columns:
        for i in range(max_autores):
            df_resultado[f'AUTOR_{i+1}'] = df_resultado['_autores_lista'].apply(
                lambda x: x[i] if isinstance(x, list) and i < len(x) else None
            )
            df_resultado[f'ID_AUTOR_{i+1}'] = df_resultado['_ids_lista'].apply(
                lambda x: x[i] if isinstance(x, list) and i < len(x) else None
            )
        df_resultado = df_resultado.drop(columns=['_autores_lista', '_ids_lista'])
        
    return df_resultado