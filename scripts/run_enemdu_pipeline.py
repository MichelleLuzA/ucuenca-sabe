#!/usr/bin/env python
"""
run_enemdu_pipeline.py
======================
Orquestador del pipeline ENEMDU (Bronze → Silver → Gold).

Ejemplos
--------
    python scripts/run_enemdu_pipeline.py --all
    python scripts/run_enemdu_pipeline.py --audit
    python scripts/run_enemdu_pipeline.py --silver --gold --years 2021 2022 2023
    python scripts/run_enemdu_pipeline.py --all --sample 50000   # prueba rápida
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.processing import (  # noqa: E402
    ENEMDUGoldBuilder,
    ENEMDUSchemaAnalyzer,
    ENEMDUSilverBuilder,
    get_logger,
    load_silver,
)

log = get_logger("pipeline_enemdu")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline medallón ENEMDU 2021-2025")
    p.add_argument("--audit", action="store_true", help="Analiza esquemas y audita Bronze")
    p.add_argument("--silver", action="store_true", help="Construye la capa Silver")
    p.add_argument("--gold", action="store_true", help="Construye la capa Gold")
    p.add_argument("--all", action="store_true", help="Ejecuta las tres etapas")
    p.add_argument("--years", nargs="+", type=int, default=None, help="Años a procesar")
    p.add_argument("--sample", type=int, default=None,
                   help="Filas por año (modo prueba, no usar en producción)")
    p.add_argument("--no-csv", action="store_true", help="No exportar CSV para Power BI")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not any((args.audit, args.silver, args.gold, args.all)):
        args.all = True

    t0 = time.time()
    analyzer = ENEMDUSchemaAnalyzer(years=args.years)

    if args.audit or args.all or args.silver:
        log.info("── Etapa 1/3: análisis de esquemas y auditoría Bronze ──")
        analyzer.analyze_all()
        print(analyzer.summary().to_string(index=False))
        if args.audit or args.all:
            print(analyzer.audit().to_string(index=False))
        analyzer.save_report()

    if args.silver or args.all:
        log.info("── Etapa 2/3: construcción de Silver ──")
        builder = ENEMDUSilverBuilder(analyzer=analyzer, years=args.years)
        result = builder.build(sample_rows=args.sample)
        print(result.quality.to_string(index=False))
        builder.save(result)

    if args.gold or args.all:
        log.info("── Etapa 3/3: construcción de Gold ──")
        silver = load_silver(analyzer.paths)
        gold = ENEMDUGoldBuilder(silver, paths=analyzer.paths)
        res = gold.build()
        print(res.kpi_anual.to_string(index=False))
        gold.save(res, export_csv=not args.no_csv)

    log.info("Pipeline finalizado en %.1f s", time.time() - t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
