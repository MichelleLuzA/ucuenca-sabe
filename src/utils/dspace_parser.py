# src/utils/dspace_parser.py
import re
import pandas as pd
import numpy as np

def ejecutar_parseo_dspace(series_metadatos):
    """
    Función Maestra de la Capa Silver Optimizada.
    Parsea, limpia factores de impacto y balancea de forma estricta
    los pares de Autores e IDs híbridos para evitar registros huérfanos.
    """
    registros_parseados = []
    max_autores = 0
    
    for metadata_string in series_metadatos:
        if pd.isna(metadata_string):
            registros_parseados.append({})
            continue
            
        resultado = {}
        texto = str(metadata_string)
        
        # 1. Identificación del Tipo de Documento
        match_type = re.search(r'dc\.type:\s*([^|]+)', texto, re.IGNORECASE)
        tipo_doc = match_type.group(1).strip() if match_type else ''
        resultado['TIPO_DOCUMENTO_DSPACE'] = tipo_doc
        es_tesis = any(k in tipo_doc.lower() for k in ['thesis', 'tesis']) or 'dc.description.degree' in texto
        
        # 2. Extracción Cronológica Secuencial (Evita flotantes)
        match_anho = re.search(r'(?:dc\.date\.issued|Previous\s+issue\s+date):\s*(\d{4})', texto, re.IGNORECASE)
        resultado['ANHO_DSPACE'] = int(match_anho.group(1)) if match_anho else None
        
        # 3. Títulos (Principal y Alternativo)
        match_tit = re.search(r'dc\.title:\s*([^|]+)', texto)
        resultado['TITULO_DSPACE'] = match_tit.group(1).strip() if match_tit else None
        
        match_alt = re.search(r'dc\.title\.alternative:\s*([^|]+)', texto)
        resultado['TITULO_ALTERNATIVE_DSPACE'] = match_alt.group(1).strip() if match_alt else None
        
        # 4. Indicadores de Calidad (Sanitización de coma decimal latinoamericana)
        match_cuartil = re.search(r'dc\.ucuenca\.cuartil:\s*([^|]+)', texto, re.IGNORECASE)
        resultado['CUARTIL_DSPACE'] = match_cuartil.group(1).strip().upper() if match_cuartil else None
        
        match_impacto = re.search(r'dc\.ucuenca\.factorimpacto:\s*([^|]+)', texto)
        if match_impacto:
            impacto_texto = match_impacto.group(1).strip().replace(',', '.')
            try:
                resultado['FACTOR_IMPACTO_DSPACE'] = float(impacto_texto)
            except ValueError:
                resultado['FACTOR_IMPACTO_DSPACE'] = None
        else:
            resultado['FACTOR_IMPACTO_DSPACE'] = None
        
        match_indice = re.search(r'dc\.ucuenca\.indicebibliografico:\s*([^|]+)', texto)
        resultado['INDICE_BIBLIOGRAFICO_DSPACE'] = match_indice.group(1).strip().upper() if match_indice else None
        
        # 5. Extracción de IDs y Autores
        ids_encontrados = [id_art.strip() for id_art in re.findall(r'dc\.ucuenca\.idautor:\s*([^|]+?)(?:\s*\|\||$)', texto)]
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
                
        # 6. Taxonomías de Áreas del Conocimiento (UNESCO y Frascati)
        m_une_amp = re.search(r'dc\.ucuenca\.areaconocimientounescoamplio:\s*([^|]+)', texto)
        resultado['UNESCO_AMPLIO'] = m_une_amp.group(1).strip() if m_une_amp else None
        
        m_une_det = re.search(r'dc\.ucuenca\.areaconocimientounescodetallado:\s*([^|]+)', texto)
        resultado['UNESCO_DETALLADO'] = m_une_det.group(1).strip() if m_une_det else None
        
        m_une_esp = re.search(r'dc\.ucuenca\.areaconocimientounescoespecifico:\s*([^|]+)', texto)
        resultado['UNESCO_ESPECIFICO'] = m_une_esp.group(1).strip() if m_une_esp else None
        
        m_fra_amp = re.search(r'dc\.ucuenca\.areaconocimientofrascatiamplio:\s*([^|]+)', texto)
        resultado['FRASCATI_AMPLIO'] = m_fra_amp.group(1).strip() if m_fra_amp else None
        
        m_fra_det = re.search(r'dc\.ucuenca\.areaconocimientofrascatidetallado:\s*([^|]+)', texto)
        resultado['FRASCATI_DETALLADO'] = m_fra_det.group(1).strip() if m_fra_det else None
        
        m_fra_esp = re.search(r'dc\.ucuenca\.areaconocimientofrascatiespecifico:\s*([^|]+)', texto)
        resultado['FRASCATI_ESPECIFICO'] = m_fra_esp.group(1).strip() if m_fra_esp else None

        # 7. Palabras Clave y Resumen (NLP)
        subjects = re.findall(r'dc\.subject(?:\.[a-z]+)?:\s*([^|]+?)(?:\s*\|\||$)', texto)
        palabras_limpias = list(set([s.strip() for s in subjects if s.strip() and "::" not in s]))
        resultado['PALABRAS_CLAVE'] = ", ".join(palabras_limpias) if palabras_limpias else None
        
        match_desc = re.search(r'dc\.description(?:\.abstract)?:\s*([^|]+)', texto)
        if match_desc and not any(k in match_desc.group(1) for k in ["Made available", "Submitted by", "No. of bitstreams"]):
            resultado['RESUMEN_DSPACE'] = match_desc.group(1).strip()
        else:
            resultado['RESUMEN_DSPACE'] = None
            
        registros_parseados.append(resultado)
        
    # --- PROCESO DE EXPANSIÓN Y SANITIZACIÓN MATRICIAL ---
    df_resultado = pd.DataFrame(registros_parseados)
    
    if 'ANHO_DSPACE' in df_resultado.columns:
        df_resultado['ANHO_DSPACE'] = df_resultado['ANHO_DSPACE'].astype('Int64')
    
    if '_autores_lista' in df_resultado.columns:
        for i in range(max_autores):
            # Asignación segura basada en posición
            df_resultado[f'AUTOR_{i+1}'] = df_resultado['_autores_lista'].apply(
                lambda x: x[i] if isinstance(x, list) and i < len(x) else None
            )
            # Control estricto: El ID se extrae solo si el autor correspondiente en esa posición existe
            df_resultado[f'ID_AUTOR_{i+1}'] = df_resultado.apply(
                lambda row: row['_ids_lista'][i] if isinstance(row['_ids_lista'], list) 
                and i < len(row['_ids_lista']) and row[f'AUTOR_{i+1}'] is not None else None, axis=1
            )
            
            # Control de purga: Si la columna completa de AUTOR_N es nula debido a un desfase de DSpace, eliminamos el par
            if df_resultado[f'AUTOR_{i+1}'].isna().all():
                df_resultado = df_resultado.drop(columns=[f'AUTOR_{i+1}', f'ID_AUTOR_{i+1}'])
                
        # Eliminamos variables de control interno
        columnas_a_borrar = [c for c in ['_autores_lista', '_ids_lista'] if c in df_resultado.columns]
        df_resultado = df_resultado.drop(columns=columnas_a_borrar)
        
    return df_resultado