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
from collections import Counter
from datetime import datetime

import pandas as pd

SILVER_FILE = "../../data/silver/noticias_economia/noticias_economia_silver.parquet"
OUTPUT_FILE = "../static/noticias_data.json"

STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "en", "y", "a", "que", "un", "una",
    "para", "por", "con", "su", "se", "al", "es", "no", "mas", "más", "como",
    "sobre", "entre", "sus", "le", "lo", "este", "esta", "ecuador",
}


def _tokens(texto: str) -> list[str]:
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    limpio = "".join(c for c in nfkd if not unicodedata.combining(c))
    return [p for p in re.findall(r"[a-z]+", limpio) if len(p) > 3 and p not in STOPWORDS]


def build():
    df = pd.read_parquet(SILVER_FILE)

    por_fuente = df["fuente"].value_counts().to_dict()

    sentimiento_total = df["sentimiento"].value_counts().to_dict()
    sentimiento_por_fuente = (
        df.groupby(["fuente", "sentimiento"]).size().unstack(fill_value=0).to_dict(orient="index")
    )

    palabras = Counter()
    for titulo in df["titulo"]:
        palabras.update(_tokens(titulo))
    top_palabras = palabras.most_common(15)

    noticias = df.sort_values("fecha_scrape", ascending=False)[
        ["fuente", "titulo", "resumen", "url", "sentimiento", "fecha_scrape"]
    ].copy()
    # ISO con 'T' (no el "YYYY-MM-DD HH:MM:SS+00:00" de str(Timestamp)): así el
    # bronze reconstruido desde este JSON en CI queda en el mismo formato que
    # escribe el scraper, y pd.to_datetime no choca con fechas mixtas.
    noticias["fecha_scrape"] = noticias["fecha_scrape"].apply(lambda t: t.isoformat())

    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "fuente": str(SILVER_FILE),
            "total_noticias": int(len(df)),
        },
        "por_fuente": por_fuente,
        "sentimiento_total": sentimiento_total,
        "sentimiento_por_fuente": sentimiento_por_fuente,
        "top_palabras": [{"palabra": p, "conteo": c} for p, c in top_palabras],
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
