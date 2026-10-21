#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de JSON para el visualizador de Noticias de Economía.
Lee data/silver/noticias_economia/noticias_economia_silver.parquet
(generado por src/processing/noticias_sentimiento.py) y produce
visualizacion/static/noticias/: resumen.json (agregados globales + lista de meses)
y noticias_YYYY-MM.json (titulares y agregados de cada mes).
"""
import json
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd

SILVER_FILE = "../../data/silver/noticias_economia/noticias_economia_silver.parquet"
OUTPUT_DIR = "../static/noticias"

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


def agregados(df):
    """Conteos (fuente, sentimiento, sector, día) de un subconjunto de noticias."""
    df = df.copy()
    df["sector"] = df["titulo"].apply(_sector)
    # Día de publicación en hora de Ecuador; las noticias sin fecha (NaT) quedan fuera.
    dia = df["fecha_publicacion"].dt.tz_convert("America/Guayaquil").dt.strftime("%Y-%m-%d")
    tabla = lambda *cols: df.groupby(list(cols)).size().unstack(fill_value=0)
    return {
        "total_noticias": int(len(df)),
        "por_fuente": df["fuente"].value_counts().to_dict(),
        "sentimiento_total": df["sentimiento"].value_counts().to_dict(),
        "sentimiento_por_fuente": tabla("fuente", "sentimiento").to_dict(orient="index"),
        "sentimiento_por_sector": tabla("sector", "sentimiento").to_dict(orient="index"),
        "sentimiento_por_dia": df.groupby([dia, "sentimiento"]).size().unstack(fill_value=0).sort_index().to_dict(orient="index"),
    }


def titulares(df):
    noticias = df[
        ["fuente", "titulo", "resumen", "url", "sentimiento", "fecha_scrape", "fecha_publicacion"]
    ].copy()
    # ISO con 'T' (no el "YYYY-MM-DD HH:MM:SS+00:00" de str(Timestamp)): así el
    # bronze reconstruido desde estos JSON en CI queda en el mismo formato que
    # escribe el scraper, y pd.to_datetime no choca con fechas mixtas.
    for col in ["fecha_scrape", "fecha_publicacion"]:
        noticias[col] = noticias[col].apply(lambda t: t.isoformat() if pd.notna(t) else None)
    return noticias.sort_values("fecha_publicacion", ascending=False).to_dict(orient="records")


def guardar(nombre, data):
    with open(os.path.join(OUTPUT_DIR, nombre), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def main():
    df = pd.read_parquet(SILVER_FILE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Un archivo por mes de captura (no de publicación: las portadas enlazan notas viejas).
    mes = df["fecha_scrape"].dt.tz_convert("America/Guayaquil").dt.strftime("%Y-%m")
    for m, sub in df.groupby(mes):
        guardar(f"noticias_{m}.json", {"mes": m, **agregados(sub), "noticias": titulares(sub)})
    guardar("resumen.json", {
        "metadata": {"timestamp": datetime.now().isoformat(), "fuente": str(SILVER_FILE)},
        "meses": sorted(mes.unique(), reverse=True),
        **agregados(df),
    })
    print(f"{len(df)} noticias en {mes.nunique()} mes(es) -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
