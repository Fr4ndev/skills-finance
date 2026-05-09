#!/usr/bin/env python3
"""
run_pipeline.py — Pipeline completo: scraping Finviz → análisis → PDF.

Uso básico:
    python run_pipeline.py

Opciones:
    python run_pipeline.py --pages 2 --output mi_reporte.pdf
    python run_pipeline.py --pages 3 --filter buy --enrich --output compras.pdf
    python run_pipeline.py --data existing_data.json --output reporte.pdf  # solo PDF

Argumentos:
    --pages N       Páginas de Finviz a descargar (default: 1, ~100 filas/página)
    --filter        all | buy | sale (default: all)
    --enrich        Enriquecer sectores con yfinance (más lento pero más preciso)
    --data PATH     Usar JSON existente en vez de descargar (saltar scraping)
    --output PATH   Ruta del PDF de salida (default: insider_dashboard_FECHA.pdf)
    --json PATH     Guardar datos intermedios en JSON (default: no guardar)
    --top N         Top N transacciones en el reporte (default: 10)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Añadir directorio del script al path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from finviz_scraper import scrape_finviz, aggregate_by_sector, get_top_transactions
from generate_pdf import build_pdf


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: Finviz → Análisis → PDF Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pages", type=int, default=1,
                        help="Páginas de Finviz (default: 1)")
    parser.add_argument("--filter", choices=["all", "buy", "sale"], default="all",
                        help="Filtro de transacciones (default: all)")
    parser.add_argument("--enrich", action="store_true",
                        help="Enriquecer sectores con yfinance")
    parser.add_argument("--data", default=None,
                        help="JSON existente (omite scraping)")
    parser.add_argument("--output", default=None,
                        help="Ruta del PDF de salida")
    parser.add_argument("--json", default=None,
                        help="Guardar datos en JSON")
    parser.add_argument("--top", type=int, default=10,
                        help="Top N transacciones (default: 10)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_pdf = args.output or f"insider_dashboard_{timestamp}.pdf"

    # -----------------------------------------------------------------------
    # Paso 1: Obtener datos
    # -----------------------------------------------------------------------
    if args.data:
        print(f"[1/3] Cargando datos desde: {args.data}")
        with open(args.data, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"[1/3] Extrayendo datos de Finviz ({args.pages} página(s), filtro: {args.filter})...")
        import pandas as pd

        df = scrape_finviz(
            pages=args.pages,
            transaction_filter=args.filter,
            enrich_sectors=args.enrich,
        )

        if df.empty:
            print("ERROR: No se obtuvieron datos de Finviz. Verifica tu conexión.")
            sys.exit(1)

        print(f"  ✓ {len(df)} transacciones obtenidas")

        # -----------------------------------------------------------------------
        # Paso 2: Análisis
        # -----------------------------------------------------------------------
        print("[2/3] Analizando datos...")
        sector_df = aggregate_by_sector(df)
        top_buys, top_sales = get_top_transactions(df, n=args.top)

        print(f"  ✓ {df['sector'].nunique()} sectores identificados")
        print(f"  ✓ {len(df[df['tx_type']=='BUY'])} compras, "
              f"{len(df[df['tx_type'].isin(['SALE','PROPOSED_SALE'])])} ventas")

        # Señales de alta convicción
        high = df[df["signal_score"] >= 75]
        if not high.empty:
            print(f"  ✓ {len(high)} señales de MÁXIMA convicción detectadas: "
                  f"{', '.join(high['Ticker'].unique()[:5])}")

        data = {
            "extracted_at": datetime.now().isoformat(),
            "total_transactions": len(df),
            "transactions": df.to_dict(orient="records"),
            "sector_aggregation": sector_df.to_dict(orient="records"),
            "top_buys": top_buys.to_dict(orient="records"),
            "top_sales": top_sales.to_dict(orient="records"),
        }

        # Guardar JSON si se solicitó
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"  ✓ Datos guardados en: {args.json}")

    # -----------------------------------------------------------------------
    # Paso 3: Generar PDF
    # -----------------------------------------------------------------------
    print(f"[3/3] Generando PDF: {output_pdf}")
    build_pdf(data, output_pdf)

    print(f"\n{'='*50}")
    print(f"✓ Dashboard generado exitosamente: {output_pdf}")
    print(f"{'='*50}")
    print(f"  Transacciones analizadas: {data.get('total_transactions', 'N/A')}")
    if "sector_aggregation" in data:
        print(f"  Sectores: {len(data['sector_aggregation'])}")
    print(f"  Archivo: {os.path.abspath(output_pdf)}")


if __name__ == "__main__":
    main()
