# src/scrapers/noticias_economia_scraper.py
"""
Scraper de titulares + resumen de la sección Economía de Primicias y El
Universo. Pensado para correrse periódicamente (Task Scheduler / cron):
cada corrida agrega solo las noticias nuevas (dedup por URL) al CSV en
data/bronze/externas/noticias_economia/.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_external_bronze_dir

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUTPUT_FILE = get_external_bronze_dir("noticias_economia") / "noticias_economia.csv"


def parse_primicias(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for art in soup.select("article"):
        link = art.select_one("h2.c-article__title a")
        if not link:
            continue
        resumen = art.select_one("p.c-article__summary, p.c-article__extracto")
        out.append({
            "fuente": "Primicias",
            "titulo": link.get_text(strip=True),
            "resumen": resumen.get_text(strip=True) if resumen else "",
            "url": urljoin("https://www.primicias.ec", link["href"]),
        })
    return out


def parse_eluniverso(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select("div.card-content"):
        link = card.select_one("h2 a")
        if not link:
            continue
        resumen = card.select_one("p.summary")
        out.append({
            "fuente": "El Universo",
            "titulo": link.get_text(strip=True),
            "resumen": resumen.get_text(strip=True) if resumen else "",
            "url": urljoin("https://www.eluniverso.com", link["href"]),
        })
    return out


SOURCES = [
    ("https://www.primicias.ec/economia/", parse_primicias),
    ("https://www.eluniverso.com/noticias/economia/", parse_eluniverso),
]


def _self_test() -> None:
    """Verifica los parsers contra fragmentos reales congelados (sin red)."""
    primicias_fixture = """
    <article class="c-article"><h2 class="c-article__title">
    <a href="/economia/nota-133780/">Titulo de prueba</a></h2>
    <p class="c-article__summary">Resumen de prueba.</p></article>
    """
    r = parse_primicias(primicias_fixture)
    assert r == [{"fuente": "Primicias", "titulo": "Titulo de prueba",
                  "resumen": "Resumen de prueba.",
                  "url": "https://www.primicias.ec/economia/nota-133780/"}], r

    eluniverso_fixture = """
    <div class="card-content"><h2><a href="/noticias/economia/nota/">Titulo EU</a></h2>
    <p class="summary">Resumen EU.</p></div>
    """
    r = parse_eluniverso(eluniverso_fixture)
    assert r == [{"fuente": "El Universo", "titulo": "Titulo EU",
                  "resumen": "Resumen EU.",
                  "url": "https://www.eluniverso.com/noticias/economia/nota/"}], r


def scrape() -> pd.DataFrame:
    rows = []
    for url, parser in SOURCES:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        rows.extend(parser(resp.text))
    df = pd.DataFrame(rows)
    df["fecha_scrape"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return df


def fecha_publicacion(url: str) -> str:
    """Lee <meta property="article:published_time"> del artículo ('' si falla)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return ""
    meta = BeautifulSoup(resp.text, "html.parser").select_one('meta[property="article:published_time"]')
    return meta["content"] if meta else ""


def guardar(df_nuevo: pd.DataFrame) -> pd.DataFrame:
    if OUTPUT_FILE.exists():
        df_previo = pd.read_csv(OUTPUT_FILE)
        df_total = pd.concat([df_previo, df_nuevo], ignore_index=True)
    else:
        df_total = df_nuevo
    df_total = df_total.drop_duplicates(subset="url", keep="first")
    # Una request extra solo por noticia sin fecha (las nuevas de esta corrida o
    # las que fallaron antes), no por todo el histórico.
    if "fecha_publicacion" not in df_total:
        df_total["fecha_publicacion"] = ""
    faltan = df_total["fecha_publicacion"].fillna("") == ""
    df_total.loc[faltan, "fecha_publicacion"] = df_total.loc[faltan, "url"].map(fecha_publicacion)
    df_total.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    return df_total


if __name__ == "__main__":
    _self_test()
    nuevas = scrape()
    total = guardar(nuevas)
    print(f"Scrapeadas {len(nuevas)} noticias en esta corrida. Total acumulado: {len(total)} en {OUTPUT_FILE}")
