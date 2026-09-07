#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de datos JSON para Dashboard de Empleabilidad ENEMDU + Sobrecalificación
Proyecto: UCuenca-SABE | Sistema de Inteligencia Territorial
Última actualización: 2026-09-04
"""

import json
import pandas as pd
import os
from datetime import datetime

def read_gold_data():
    """Lee los 5 archivos Parquet de Gold"""
    print("📥 Leyendo datos de Gold...")

    base_path = "../../data/gold/enemdu"

    try:
        kpi_anual = pd.read_parquet(f"{base_path}/kpi_anual.parquet")
        print(f"  ✓ kpi_anual: {len(kpi_anual)} filas")

        empleabilidad_provincia = pd.read_parquet(f"{base_path}/empleabilidad_provincia.parquet")
        print(f"  ✓ empleabilidad_provincia: {len(empleabilidad_provincia)} filas")

        empleabilidad_sexo_edad = pd.read_parquet(f"{base_path}/empleabilidad_sexo_edad.parquet")
        print(f"  ✓ empleabilidad_sexo_edad: {len(empleabilidad_sexo_edad)} filas")

        graduados_rama_actividad = pd.read_parquet(f"{base_path}/graduados_rama_actividad.parquet")
        print(f"  ✓ graduados_rama_actividad: {len(graduados_rama_actividad)} filas")

        sobrecalificacion_ocupacion = pd.read_parquet(f"{base_path}/sobrecalificacion_ocupacion.parquet")
        print(f"  ✓ sobrecalificacion_ocupacion: {len(sobrecalificacion_ocupacion)} filas")

        comparativo_nivel_instruccion = pd.read_parquet(f"{base_path}/comparativo_nivel_instruccion.parquet")
        print(f"  ✓ comparativo_nivel_instruccion: {len(comparativo_nivel_instruccion)} filas")

        return {
            'kpi_anual': kpi_anual,
            'empleabilidad_provincia': empleabilidad_provincia,
            'empleabilidad_sexo_edad': empleabilidad_sexo_edad,
            'graduados_rama_actividad': graduados_rama_actividad,
            'sobrecalificacion_ocupacion': sobrecalificacion_ocupacion,
            'comparativo_nivel_instruccion': comparativo_nivel_instruccion
        }
    except Exception as e:
        print(f"❌ Error al leer Parquet: {e}")
        raise

#: Orden pedagógico (no alfabético) de nivel_instruccion, igual al fallback de
#: enemdu_mappings.py — así el frontend no tiene que ordenar por texto.
NIVEL_INSTRUCCION_ORDEN = [
    "Ninguno", "Centro de alfabetización", "Jardín de infantes", "Primaria",
    "Educación Básica", "Secundaria", "Educación Media/Bachillerato",
    "Superior no universitaria", "Superior universitaria", "Post-grado",
]
#: Orden de grupo_edad, igual a GRUPOS_EDAD de enemdu_silver_builder.py.
GRUPO_EDAD_ORDEN = ["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]


def build_enemdu_module(data, segmento, title):
    """Construye un módulo de empleabilidad para un `segmento` de Gold.

    Gold trae 'general' (toda la PEA/PET) y 'educacion_superior' (graduados)
    apiladas en las mismas tablas con una columna `segmento` — anidadas, no una
    partición. Hay que filtrar por segmento ANTES de agregar; nunca mezclar
    ambas filas de un mismo año/provincia o los totales se duplican.
    """
    print(f"📊 Generando módulo ENEMDU (segmento={segmento})...")

    kpi_df = data['kpi_anual']
    kpi_df = kpi_df[kpi_df['segmento'] == segmento].copy()
    prov_df = data['empleabilidad_provincia']
    prov_df = prov_df[prov_df['segmento'] == segmento].copy()
    rama_df = data['graduados_rama_actividad']
    rama_df = rama_df[rama_df['segmento'] == segmento].copy()

    # Años disponibles
    latest_year = kpi_df['anio'].max()
    latest_kpi = kpi_df[kpi_df['anio'] == latest_year].iloc[0]

    kpi_latest = {
        "year": int(latest_year),
        "tasa_desempleo": float(latest_kpi.get('tasa_desempleo', 0)) if pd.notna(latest_kpi.get('tasa_desempleo')) else 0,
        "tasa_empleo_adecuado": float(latest_kpi.get('tasa_empleo_adecuado', 0)) if pd.notna(latest_kpi.get('tasa_empleo_adecuado')) else 0,
        "tasa_subempleo": float(latest_kpi.get('tasa_subempleo', 0)) if pd.notna(latest_kpi.get('tasa_subempleo')) else 0,
        "ingreso_laboral_medio": float(latest_kpi.get('ingreso_laboral_medio', 0)) if pd.notna(latest_kpi.get('ingreso_laboral_medio')) else 0,
        "n_muestral": int(latest_kpi.get('n_muestral', 0)) if pd.notna(latest_kpi.get('n_muestral')) else 0,
        "poblacion": float(latest_kpi.get('poblacion', 0)) if pd.notna(latest_kpi.get('poblacion')) else 0
    }

    # Timeline 2021-2025
    years = sorted(kpi_df['anio'].unique())
    timeline = {
        "years": [int(y) for y in years],
        "tasa_desempleo": [float(kpi_df[kpi_df['anio'] == y]['tasa_desempleo'].iloc[0]) if len(kpi_df[kpi_df['anio'] == y]) > 0 and pd.notna(kpi_df[kpi_df['anio'] == y]['tasa_desempleo'].iloc[0]) else 0 for y in years],
        "tasa_empleo_adecuado": [float(kpi_df[kpi_df['anio'] == y]['tasa_empleo_adecuado'].iloc[0]) if len(kpi_df[kpi_df['anio'] == y]) > 0 and pd.notna(kpi_df[kpi_df['anio'] == y]['tasa_empleo_adecuado'].iloc[0]) else 0 for y in years],
        "tasa_subempleo": [float(kpi_df[kpi_df['anio'] == y]['tasa_subempleo'].iloc[0]) if len(kpi_df[kpi_df['anio'] == y]) > 0 and pd.notna(kpi_df[kpi_df['anio'] == y]['tasa_subempleo'].iloc[0]) else 0 for y in years]
    }

    # Por provincia (último año)
    prov_latest = prov_df[prov_df['anio'] == latest_year].copy()
    por_provincia = []
    for _, row in prov_latest.iterrows():
        por_provincia.append({
            "provincia": str(row.get('provincia', 'Unknown')),
            "tasa_desempleo": float(row.get('tasa_desempleo', 0)) if pd.notna(row.get('tasa_desempleo')) else 0,
            "tasa_empleo_adecuado": float(row.get('tasa_empleo_adecuado', 0)) if pd.notna(row.get('tasa_empleo_adecuado')) else 0,
            "ingreso_laboral_medio": float(row.get('ingreso_laboral_medio', 0)) if pd.notna(row.get('ingreso_laboral_medio')) else 0,
            "n_muestral": int(row.get('n_muestral', 0)) if pd.notna(row.get('n_muestral')) else 0
        })

    por_provincia.sort(key=lambda x: x['tasa_desempleo'], reverse=True)

    # Por rama (último año)
    rama_latest = rama_df[rama_df['anio'] == latest_year].copy()
    por_rama = []
    for _, row in rama_latest.iterrows():
        por_rama.append({
            "rama_actividad": str(row.get('rama_actividad', 'Unknown')),
            "ocupados": int(row.get('ocupados', 0)) if pd.notna(row.get('ocupados')) else 0,
            "participacion_pct": float(row.get('participacion_pct', 0)) if pd.notna(row.get('participacion_pct')) else 0,
            "ingreso_laboral_medio": float(row.get('ingreso_laboral_medio', 0)) if pd.notna(row.get('ingreso_laboral_medio')) else 0
        })

    # Por sexo y grupo etario (último año) — brecha de género en desempleo
    sexo_edad_df = data['empleabilidad_sexo_edad']
    sexo_edad_df = sexo_edad_df[sexo_edad_df['segmento'] == segmento].copy()
    sexo_edad_latest = sexo_edad_df[sexo_edad_df['anio'] == latest_year].copy()
    sexo_edad_latest['orden'] = sexo_edad_latest['grupo_edad'].apply(
        lambda g: GRUPO_EDAD_ORDEN.index(g) if g in GRUPO_EDAD_ORDEN else 99)
    sexo_edad_latest = sexo_edad_latest.sort_values(['orden', 'sexo'])

    por_sexo_edad = []
    for _, row in sexo_edad_latest.iterrows():
        por_sexo_edad.append({
            "sexo": str(row.get('sexo', 'Unknown')),
            "grupo_edad": str(row.get('grupo_edad', 'Unknown')),
            "tasa_desempleo": float(row['tasa_desempleo']) if pd.notna(row.get('tasa_desempleo')) else 0,
            "tasa_empleo_adecuado": float(row['tasa_empleo_adecuado']) if pd.notna(row.get('tasa_empleo_adecuado')) else 0,
            "brecha_desempleo_pp": (
                float(row['brecha_desempleo_pp']) if pd.notna(row.get('brecha_desempleo_pp')) else None
            ),
            "n_muestral": int(row.get('n_muestral', 0)) if pd.notna(row.get('n_muestral')) else 0
        })

    # Por nivel de instrucción (último año) — sólo en el segmento 'general':
    # compara TODOS los niveles educativos entre sí (incluye no-graduados), que
    # es justamente lo que 'educacion_superior' ya excluye por definición.
    por_nivel_instruccion = None
    if segmento == "general":
        nivel_df = data['comparativo_nivel_instruccion']
        nivel_latest = nivel_df[nivel_df['anio'] == latest_year].copy()
        nivel_latest['orden'] = nivel_latest['nivel_instruccion'].apply(
            lambda n: NIVEL_INSTRUCCION_ORDEN.index(n) if n in NIVEL_INSTRUCCION_ORDEN else 99)
        nivel_latest = nivel_latest.sort_values('orden')

        por_nivel_instruccion = []
        for _, row in nivel_latest.iterrows():
            por_nivel_instruccion.append({
                "nivel_instruccion": str(row.get('nivel_instruccion', 'Unknown')),
                "tasa_desempleo": float(row['tasa_desempleo']) if pd.notna(row.get('tasa_desempleo')) else 0,
                "tasa_empleo_adecuado": float(row['tasa_empleo_adecuado']) if pd.notna(row.get('tasa_empleo_adecuado')) else 0,
                "tasa_sobrecalificacion": (
                    float(row['tasa_sobrecalificacion']) if pd.notna(row.get('tasa_sobrecalificacion')) else None
                ),
                "n_muestral": int(row.get('n_muestral', 0)) if pd.notna(row.get('n_muestral')) else 0
            })

    # Filtros disponibles
    filtros = {
        "years": [int(y) for y in sorted(kpi_df['anio'].unique())],
        "provincias": sorted([str(p) for p in prov_df['provincia'].unique() if pd.notna(p)]),
        "sectores": sorted([str(r) for r in rama_df['rama_actividad'].unique() if pd.notna(r)])
    }

    module = {
        "title": title,
        "segmento": segmento,
        "kpi_latest": kpi_latest,
        "timeline": timeline,
        "por_provincia": por_provincia,
        "por_rama": por_rama,
        "por_sexo_edad": por_sexo_edad,
        "filtros_disponibles": filtros
    }
    if por_nivel_instruccion is not None:
        module["por_nivel_instruccion"] = por_nivel_instruccion
    return module

def build_sobrecalificacion_module(data):
    """Construye el módulo Sobrecalificación"""
    print("📊 Generando módulo Sobrecalificación...")

    sobrecal_df = data['sobrecalificacion_ocupacion'].copy()
    sobrecal_df = sobrecal_df.sort_values('anio')

    # Tasa general por año: SIEMPRE desde kpi_anual (sobrecalificados/ocupados_con_ciuo
    # ponderado por fexp, segmento graduados). NO promediar 'participacion_ocupados_pct'
    # de sobrecalificacion_ocupacion: esa columna es la distribución de graduados
    # ocupados ENTRE grupos CIUO (suma 100% por año) — su media es un artefacto
    # (~100/n_grupos, ~11% siempre) sin relación con la tasa real de sobrecalificación.
    kpi_superior = data['kpi_anual']
    kpi_superior = kpi_superior[kpi_superior['segmento'] == 'educacion_superior'].sort_values('anio')

    tasa_general = {
        "years": [int(y) for y in kpi_superior['anio']],
        "tasa_sobrecalificacion": [
            float(t) if pd.notna(t) else 0 for t in kpi_superior['tasa_sobrecalificacion']
        ]
    }

    # Por ocupación (último año). OJO: esto es DISTRIBUCIÓN, no una tasa de
    # sobrecalificación por grupo — a este nivel de grano, "sobrecalificado" es
    # 0%/100% tautológico según si el grupo requiere título (CIUO-08 1-3) o no
    # (4-9). 'participacion_pct' responde "¿en qué ocupación termina cada
    # graduado ocupado?"; la única tasa de sobrecalificación real y ponderada
    # es la de tasa_general_por_anio (arriba, viene de kpi_anual).
    latest_year = sobrecal_df['anio'].max()
    ocupacion_latest = sobrecal_df[sobrecal_df['anio'] == latest_year].copy()
    por_ocupacion = []
    for _, row in ocupacion_latest.iterrows():
        por_ocupacion.append({
            "ocupacion": str(row.get('ciuo_gran_grupo_desc', 'Unknown')),
            "ciuo_grupo": int(row.get('ciuo_gran_grupo', 0)) if pd.notna(row.get('ciuo_gran_grupo')) else 0,
            "participacion_pct": float(row.get('participacion_ocupados_pct', 0)) if pd.notna(row.get('participacion_ocupados_pct')) else 0,
            "requiere_titulo": int(row.get('requiere_titulo_superior', 0)) if pd.notna(row.get('requiere_titulo_superior')) else 0,
            "sobrecalificado": not bool(row.get('requiere_titulo_superior', False)),
            "ocupados_totales": int(row.get('ocupados', 0)) if pd.notna(row.get('ocupados')) else 0
        })

    por_ocupacion.sort(key=lambda x: x['participacion_pct'], reverse=True)

    # CIUO mapping
    ciuo_mapping = {
        1: "Profesionales",
        2: "Técnicos",
        3: "Personal de apoyo",
        4: "Empleados de oficina",
        5: "Servicios y ventas",
        6: "Agricultura",
        7: "Oficios",
        8: "Operarios",
        9: "Trabajadores no calificados"
    }

    return {
        "title": "Sobrecalificación — Graduados en Ocupaciones No Acordes",
        "tasa_general_por_anio": tasa_general,
        "por_ocupacion_2025": por_ocupacion,
        "ciuo_mapping": ciuo_mapping,
        "metodologia": (
            "Sobrecalificado = graduado de educación superior ocupado en una ocupación "
            "(CIUO-08 grupos 4-9) que no requiere título superior. 'tasa_general_por_anio' "
            "es la tasa real (sobrecalificados/ocupados, ponderada por fexp). "
            "'por_ocupacion_2025.participacion_pct' es distinto: qué % de los graduados "
            "ocupados trabaja en cada grupo CIUO (no es, en sí, una tasa de sobrecalificación)."
        )
    }

def build_dashboard_json(data):
    """Construye el JSON completo del dashboard"""
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "fuente": "data/gold/enemdu/*.parquet",
            "descripcion": "Dashboard Empleabilidad ENEMDU + Sobrecalificación"
        },
        "modules": {
            "enemdu": build_enemdu_module(
                data, "general",
                "Mercado Laboral ENEMDU — Contexto Nacional, toda la PEA (2021-2025)"),
            "empleabilidad_superior": build_enemdu_module(
                data, "educacion_superior",
                "Empleabilidad — Graduados de Educación Superior (2021-2025)"),
            "sobrecalificacion": build_sobrecalificacion_module(data)
        }
    }

def main():
    """Función principal"""
    try:
        data = read_gold_data()
        dashboard_data = build_dashboard_json(data)
        os.makedirs("../static", exist_ok=True)
        output_path = "../static/data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        file_size = os.path.getsize(output_path) / 1024
        print(f"\n✅ JSON generado: {os.path.abspath(output_path)}")
        print(f"   Tamaño: {file_size:.1f} KB")
        print(f"   Módulos: {', '.join(dashboard_data['modules'].keys())}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
