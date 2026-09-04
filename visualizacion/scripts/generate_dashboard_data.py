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

        return {
            'kpi_anual': kpi_anual,
            'empleabilidad_provincia': empleabilidad_provincia,
            'empleabilidad_sexo_edad': empleabilidad_sexo_edad,
            'graduados_rama_actividad': graduados_rama_actividad,
            'sobrecalificacion_ocupacion': sobrecalificacion_ocupacion
        }
    except Exception as e:
        print(f"❌ Error al leer Parquet: {e}")
        raise

def build_enemdu_module(data):
    """Construye el módulo ENEMDU"""
    print("📊 Generando módulo ENEMDU...")

    kpi_df = data['kpi_anual'].copy()
    prov_df = data['empleabilidad_provincia'].copy()
    rama_df = data['graduados_rama_actividad'].copy()

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

    # Filtros disponibles
    filtros = {
        "years": [int(y) for y in sorted(kpi_df['anio'].unique())],
        "provincias": sorted([str(p) for p in prov_df['provincia'].unique() if pd.notna(p)]),
        "sectores": sorted([str(r) for r in rama_df['rama_actividad'].unique() if pd.notna(r)])
    }

    return {
        "title": "Mercado Laboral ENEMDU — Contexto Nacional (2021-2025)",
        "kpi_latest": kpi_latest,
        "timeline": timeline,
        "por_provincia": por_provincia,
        "por_rama": por_rama,
        "filtros_disponibles": filtros
    }

def build_sobrecalificacion_module(data):
    """Construye el módulo Sobrecalificación"""
    print("📊 Generando módulo Sobrecalificación...")

    sobrecal_df = data['sobrecalificacion_ocupacion'].copy()
    sobrecal_df = sobrecal_df.sort_values('anio')

    # Tasa general por año
    tasa_por_ano = sobrecal_df.groupby('anio').agg({
        'participacion_ocupados_pct': 'mean'
    }).reset_index()

    tasa_general = {
        "years": [int(y) for y in sorted(tasa_por_ano['anio'].unique())],
        "tasa_sobrecalificacion": [float(t) if pd.notna(t) else 0 for t in tasa_por_ano['participacion_ocupados_pct']]
    }

    # Por ocupación (último año)
    latest_year = sobrecal_df['anio'].max()
    ocupacion_latest = sobrecal_df[sobrecal_df['anio'] == latest_year].copy()
    por_ocupacion = []
    for _, row in ocupacion_latest.iterrows():
        por_ocupacion.append({
            "ocupacion": str(row.get('ciuo_gran_grupo_desc', 'Unknown')),
            "ciuo_grupo": int(row.get('ciuo_gran_grupo', 0)) if pd.notna(row.get('ciuo_gran_grupo')) else 0,
            "tasa_sobrecalificacion": float(row.get('participacion_ocupados_pct', 0)) if pd.notna(row.get('participacion_ocupados_pct')) else 0,
            "requiere_titulo": int(row.get('requiere_titulo_superior', 0)) if pd.notna(row.get('requiere_titulo_superior')) else 0,
            "ocupados_totales": int(row.get('ocupados', 0)) if pd.notna(row.get('ocupados')) else 0
        })

    por_ocupacion.sort(key=lambda x: x['tasa_sobrecalificacion'], reverse=True)

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
        "metodologia": "Sobrecalificado = Graduado en ocupaciones CIUO-08 grupos 4-9"
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
            "enemdu": build_enemdu_module(data),
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
