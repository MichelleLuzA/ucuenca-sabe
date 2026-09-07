#!/usr/bin/env python3
"""
Asegurar que Bronze (Kaggle ENEMDU) esté descargado localmente.

Uso:
    python ensure_bronze.py                  # Descarga solo si falta
    python ensure_bronze.py --force          # Fuerza descarga (ignora caché)
    python ensure_bronze.py --check-only     # Solo verifica, no descarga
    python ensure_bronze.py --years 2024 2025  # Descarga/verifica solo esos años
"""

import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Inyectar proyecto
PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def check_bronze_exists(years: List[int] = None) -> Dict:
    """Verifica qué años de Bronze existen localmente."""
    if years is None:
        years = list(range(2021, 2026))

    # Importar después del sys.path setup
    from src.processing import ENEMDUPaths

    paths = ENEMDUPaths.build(PROJECT_ROOT)
    manifest_path = paths.bronze / ".manifest.json"

    años_locales = []
    if paths.microdatos.exists():
        años_locales = sorted(
            int(m.group()) for f in paths.microdatos.glob("*.csv")
            if (m := re.search(r"(?:19|20)\d{2}", f.stem))
        )

    años_faltantes = [a for a in years if a not in años_locales]

    última_descarga = None
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                última_descarga = json.load(f).get("última_descarga")
        except Exception:
            pass

    tamaño_mb = 0.0
    if paths.microdatos.exists():
        tamaño_mb = sum(f.stat().st_size for f in paths.microdatos.rglob("*.csv")) / 1e6

    return {
        "años_locales": años_locales,
        "años_faltantes": años_faltantes,
        "existe_completo": len(años_faltantes) == 0 and len(años_locales) > 0,
        "tamaño_mb": tamaño_mb,
        "última_descarga": última_descarga,
        "bronze_dir": str(paths.bronze),
        "manifest_path": manifest_path,
    }


def save_manifest(manifest_path: Path, años_descargados: List[int]) -> None:
    """Guarda un manifest.json con timestamp de descarga."""
    from src.config import CONFIG

    manifest = {
        "última_descarga": datetime.now().isoformat(),
        "años": años_descargados,
        "fuente": CONFIG["sources"]["enemdu"]["kaggle_dataset"],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)


def download_bronze(years: List[int], manifest_path: Path):
    """Descarga desde Kaggle."""
    from src.ingestion.kaggle_downloader import download_and_organize_enemdu

    print("🚀 Descargando desde Kaggle ENEMDU...")
    print("   (esto puede tomar varios minutos)\n")

    try:
        inventario = download_and_organize_enemdu()
        save_manifest(manifest_path, years)
        return True, inventario
    except Exception as e:
        print(f"❌ Error durante descarga: {e}")
        return False, None


def main():
    parser = argparse.ArgumentParser(
        description="Asegurar que Bronze (Kaggle ENEMDU) esté descargado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python ensure_bronze.py              # Descarga si falta
  python ensure_bronze.py --force      # Fuerza descarga
  python ensure_bronze.py --check-only # Solo verifica
  python ensure_bronze.py --years 2024 2025  # Solo esos años
        """,
    )
    parser.add_argument("--force", action="store_true", help="Fuerza descarga (ignora caché local)")
    parser.add_argument("--check-only", action="store_true", help="Solo verifica sin descargar")
    parser.add_argument(
        "--years", type=int, nargs="+", default=list(range(2021, 2026)),
        help="Años a verificar (default: 2021-2025)",
    )
    parser.add_argument("--verbose", action="store_true", help="Output más detallado")

    args = parser.parse_args()

    # Verificar estado actual
    print("\n" + "=" * 70)
    print("📦 COMPROBANDO ESTADO DE CACHÉ LOCAL")
    print("=" * 70)

    estado = check_bronze_exists(years=args.years)

    print(f"\n  Años esperados:    {args.years}")
    print(f"  Años locales:      {estado['años_locales'] if estado['años_locales'] else '(ninguno)'}")
    if estado["años_faltantes"]:
        print(f"  Años faltantes:    {estado['años_faltantes']}")
    print(f"  Tamaño en disco:   {estado['tamaño_mb']:.1f} MB")
    if estado["última_descarga"]:
        print(f"  Última descarga:   {estado['última_descarga']}")

    print(f"\n  Ubicación:         {estado['bronze_dir']}")

    # Decidir qué hacer
    if args.check_only:
        print("\n  📋 (modo verificación: sin descargar)")
        print("=" * 70)
        return 0 if estado["existe_completo"] else 1

    if estado["existe_completo"] and not args.force:
        print("\n  ✅ Bronze completo en caché — saltando descarga")
        print("     (usa --force para re-descargar)")
        print("=" * 70)
        return 0

    # Descargar
    print("\n" + "-" * 70)
    if args.force:
        print("  🔄 Forzando descarga (por --force)")
    elif estado["años_faltantes"]:
        print(f"  📥 Faltan años {estado['años_faltantes']}: descargando")
    else:
        print("  🚀 Bronze no encontrado: descargando")
    print("-" * 70 + "\n")

    success, inventario = download_bronze(args.years, estado["manifest_path"])

    if success:
        estado_final = check_bronze_exists(years=args.years)
        print("\n✅ Descarga completada")
        print(f"   Años disponibles: {estado_final['años_locales']}")
        print(f"   Tamaño total:    {estado_final['tamaño_mb']:.1f} MB")
        print("=" * 70)
        return 0
    else:
        print("\n❌ Fallo en la descarga")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
