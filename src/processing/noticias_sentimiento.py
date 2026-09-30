# src/processing/noticias_sentimiento.py
"""
Silver de noticias de economía: lee el bronze crudo del scraper
(noticias_economia_scraper.py), limpia/estructura y etiqueta sentimiento.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_external_bronze_dir, get_domain_silver_dir

BRONZE_FILE = get_external_bronze_dir("noticias_economia") / "noticias_economia.csv"
SILVER_FILE = get_domain_silver_dir("noticias_economia") / "noticias_economia_silver.parquet"

# ponytail: lexicón positivo/negativo a mano (sin modelo entrenado) — falla con
# sarcasmo/negación ("no hubo crecimiento") y vocabulario fuera de la lista.
# Upgrade: si la precisión importa, cambiar score_sentimiento() por
# pysentimiento (robertuito-sentiment-analysis), ya evaluado, solo que pesa
# ~1GB (torch+transformers) para lo que hoy son ~40 titulares/corrida.
POSITIVE_WORDS = {
    "crecimiento", "crece", "creció", "sube", "subio", "subió", "aumento",
    "aumenta", "aumentó", "mejora", "mejoró", "record", "récord", "recupera",
    "recuperacion", "recuperación", "superavit", "superávit", "impulsa",
    "impulso", "avanza", "avance", "gana", "ganancia", "positivo", "exito",
    "éxito", "acuerdo", "inversion", "inversión", "exporta", "exportacion",
    "exportación", "alza", "fortalece", "beneficio", "oportunidad",
}
NEGATIVE_WORDS = {
    "crisis", "caida", "caída", "cae", "recesion", "recesión", "deficit",
    "déficit", "desempleo", "perdida", "pérdida", "pierde", "reduce",
    "reduccion", "reducción", "baja", "bajo", "bajó", "corte", "cortes",
    "escasez", "estiaje", "alerta", "riesgo", "preocupacion", "preocupación",
    "conflicto", "protesta", "deuda", "quiebra", "inflacion", "inflación",
    "devaluacion", "devaluación", "paro", "afecta", "amenaza",
}


def _strip_accents(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_POSITIVE_NORM = {_strip_accents(w) for w in POSITIVE_WORDS}
_NEGATIVE_NORM = {_strip_accents(w) for w in NEGATIVE_WORDS}


def score_sentimiento(texto: str) -> tuple[str, int]:
    """Cuenta palabras positivas/negativas (sin acentos, por palabra completa)."""
    palabras = re.findall(r"[a-z]+", _strip_accents(texto or ""))
    pos = sum(1 for p in palabras if p in _POSITIVE_NORM)
    neg = sum(1 for p in palabras if p in _NEGATIVE_NORM)
    score = pos - neg
    if score > 0:
        return "positivo", score
    if score < 0:
        return "negativo", score
    return "neutro", score


def build_silver() -> pd.DataFrame:
    df = pd.read_csv(BRONZE_FILE)
    df = df.dropna(subset=["titulo", "url"]).drop_duplicates(subset="url", keep="first")
    df["resumen"] = df["resumen"].fillna("")
    df["fecha_scrape"] = pd.to_datetime(df["fecha_scrape"], utc=True, format="mixed")
    df["fecha_publicacion"] = pd.to_datetime(df["fecha_publicacion"], utc=True, format="mixed", errors="coerce")

    texto = df["titulo"] + " " + df["resumen"]
    etiquetas = texto.map(score_sentimiento)
    df["sentimiento"] = etiquetas.map(lambda t: t[0])
    df["sentimiento_score"] = etiquetas.map(lambda t: t[1])

    df = df.sort_values(["fecha_publicacion", "fecha_scrape"], ascending=False).reset_index(drop=True)
    SILVER_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SILVER_FILE, index=False)
    return df


def _self_test() -> None:
    label, score = score_sentimiento("La economía crece y el empleo mejora con récord de inversión")
    assert label == "positivo" and score > 0, (label, score)
    label, score = score_sentimiento("Crisis y caída del empleo por la recesión y el déficit")
    assert label == "negativo" and score < 0, (label, score)
    label, score = score_sentimiento("El Banco Central publicó el informe mensual")
    assert label == "neutro" and score == 0, (label, score)


if __name__ == "__main__":
    _self_test()
    silver = build_silver()
    print(f"Silver generado: {len(silver)} noticias -> {SILVER_FILE}")
    print(silver["sentimiento"].value_counts())
