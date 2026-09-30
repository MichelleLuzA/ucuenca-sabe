#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de JSON para el visualizador de Noticias de Economía.
Lee data/silver/noticias_economia/noticias_economia_silver.parquet
(generado por src/processing/noticias_sentimiento.py) y produce
visualizacion/static/noticias_data.json.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd

SILVER_FILE = "../../data/silver/noticias_economia/noticias_economia_silver.parquet"
OUTPUT_FILE = "../static/noticias_data.json"

# Sector -> prefijos de palabras (sin tildes, minúscula). Gana el primer sector que coincida.
# ponytail: clasificación por palabras clave; migrar a un clasificador si los titulares dejan de calzar.
SECTORES = {
    "Energía y minería": ["energ", "electric", "hidroelectric", "coca codo", "caudal", "embalse", "estiaje",
                          "petrol", "diesel", "mineri", "megavat", "generacion", "apagon", r"cortes de luz"],
    "Finanzas y sector público": [r"iva\b", "impuesto", "banco", "credito", "riesgo pais", "cuentas del estado",
                                  "deuda", "ahorro", "tarjeta", "sueldo", "gastos personales", "ministerio", "gobierno"],
    "Agro y comercio exterior": ["exporta", "importa", "banan", "agricol", "tractor", "carne", "aduana", "camaron", "cacao"],
    "Industria y manufactura": ["fabrica", "ceramic", "manufactur", "automatizacion", "industria"],
    "Turismo y comercio": ["turis", "feriado", "comercio", "hotel"],
    "Telecom y tecnología": ["internet", "starlink", r"cnt\b", "inteligencia artificial", "telecom"],
    "Vivienda": ["casa propia", "vivienda", "inmobiliar"],
}


def _norm(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _sector(titulo: str) -> str:
    t = _norm(titulo)
    for sector, kws in SECTORES.items():
        if any(re.search(r"\b" + k, t) for k in kws):
            return sector
    return "Otros"


def build():
    df = pd.read_parquet(SILVER_FILE)

    por_fuente = df["fuente"].value_counts().to_dict()

    sentimiento_total = df["sentimiento"].value_counts().to_dict()
    sentimiento_por_fuente = (
        df.groupby(["fuente", "sentimiento"]).size().unstack(fill_value=0).to_dict(orient="index")
    )

    df["sector"] = df["titulo"].apply(_sector)
    sentimiento_por_sector = (
        df.groupby(["sector", "sentimiento"]).size().unstack(fill_value=0).to_dict(orient="index")
    )

    # Día de publicación en hora de Ecuador; las noticias sin fecha (NaT) quedan fuera.
    dia = df["fecha_publicacion"].dt.tz_convert("America/Guayaquil").dt.strftime("%Y-%m-%d")
    sentimiento_por_dia = (
        df.groupby([dia, "sentimiento"]).size().unstack(fill_value=0).sort_index().to_dict(orient="index")
    )

    noticias = df[
        ["fuente", "titulo", "resumen", "url", "sentimiento", "fecha_scrape", "fecha_publicacion"]
    ].copy()
    # ISO con 'T' (no el "YYYY-MM-DD HH:MM:SS+00:00" de str(Timestamp)): así el
    # bronze reconstruido desde este JSON en CI queda en el mismo formato que
    # escribe el scraper, y pd.to_datetime no choca con fechas mixtas.
    for col in ["fecha_scrape", "fecha_publicacion"]:
        noticias[col] = noticias[col].apply(lambda t: t.isoformat() if pd.notna(t) else None)

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "fuente": str(SILVER_FILE),
            "total_noticias": int(len(df)),
        },
        "por_fuente": por_fuente,
        "sentimiento_total": sentimiento_total,
        "sentimiento_por_fuente": sentimiento_por_fuente,
        "sentimiento_por_sector": sentimiento_por_sector,
        "sentimiento_por_dia": sentimiento_por_dia,
        "noticias": noticias.to_dict(orient="records"),
    }


def main():
    data = build()
    os.makedirs("../static", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"noticias_data.json generado: {data['metadata']['total_noticias']} noticias")


if __name__ == "__main__":
    main()
