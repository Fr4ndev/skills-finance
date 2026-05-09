#!/usr/bin/env python3
"""
finviz_scraper.py — Extrae datos de insider trading de Finviz y los enriquece
con clasificación sectorial, scoring de señal y análisis de flujos.

Uso:
    python finviz_scraper.py [--pages N] [--filter buy|sale|all] [--output data.json]
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FINVIZ_URL = "https://finviz.com/insidertrading.ashx"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://finviz.com/",
}

# ---------------------------------------------------------------------------
# Mapping sectorial ampliado
# ---------------------------------------------------------------------------

SECTOR_MAP = {
    # Semiconductores / Hardware
    "NVDA": "Semiconductores", "INTC": "Semiconductores", "AMD": "Semiconductores",
    "MU": "Semiconductores", "AVGO": "Semiconductores", "QCOM": "Semiconductores",
    "TXN": "Semiconductores", "AMAT": "Semiconductores", "LRCX": "Semiconductores",
    "KLAC": "Semiconductores", "DELL": "Tecnología Hardware", "HPQ": "Tecnología Hardware",
    "AEHR": "Semiconductores", "SMCI": "Tecnología Hardware",
    # Software / Cloud / SaaS
    "SNOW": "Software/Cloud", "WDAY": "Software/Cloud", "NET": "Software/Cloud",
    "APP": "Software/Cloud", "SHOP": "Software/Cloud", "RDDT": "Software/Cloud",
    "CRM": "Software/Cloud", "NOW": "Software/Cloud", "MSFT": "Software/Cloud",
    "ORCL": "Software/Cloud", "SAP": "Software/Cloud", "ADBE": "Software/Cloud",
    "PLTR": "Software/Cloud", "DDOG": "Software/Cloud", "ZS": "Software/Cloud",
    "CRWD": "Software/Cloud", "HIMS": "Software/Cloud",
    # Biotecnología / Farma
    "ALDX": "Biotecnología/Farma", "OPK": "Biotecnología/Farma",
    "ACOG": "Biotecnología/Farma", "KYMR": "Biotecnología/Farma",
    "TLSI": "Biotecnología/Farma", "ATAI": "Biotecnología/Farma",
    "ARWR": "Biotecnología/Farma", "BCDA": "Biotecnología/Farma",
    "PHVS": "Biotecnología/Farma", "LUNR": "Biotecnología/Farma",
    "TLRY": "Biotecnología/Farma", "RDHL": "Biotecnología/Farma",
    "CLNN": "Biotecnología/Farma",
    # Energía
    "AMR": "Energía", "PBF": "Energía", "DK": "Energía",
    "XOM": "Energía", "CVX": "Energía", "COP": "Energía",
    "OXY": "Energía", "SLB": "Energía", "HAL": "Energía",
    # Consumo Discrecional
    "HSY": "Consumo Discrecional", "FIVE": "Consumo Discrecional",
    "LOVE": "Consumo Discrecional", "KSS": "Consumo Discrecional",
    "TXRH": "Consumo Discrecional", "MCD": "Consumo Discrecional",
    "SBUX": "Consumo Discrecional", "NKE": "Consumo Discrecional",
    "FLWS": "Consumo Discrecional",
    # Servicios Industriales / Financieros
    "BBSI": "Servicios Industriales", "WD": "Servicios Financieros",
    "GF": "Servicios Financieros", "CTAS": "Servicios Industriales",
    "AGX": "Servicios Industriales", "SBH": "Servicios Industriales",
    "VCX": "Servicios Financieros",
    # Fintech / Cripto
    "SOFI": "Fintech/Cripto", "WULF": "Fintech/Cripto",
    "COIN": "Fintech/Cripto", "MSTR": "Fintech/Cripto",
    # Robótica / Industrial
    "EKSO": "Robótica/Industrial",
    # Transporte / Logística
    "DASH": "Transporte/Logística", "UBER": "Transporte/Logística",
    "LYFT": "Transporte/Logística",
    # Agricultura / Materias Primas
    "AGRO": "Agricultura/Materias Primas",
    # Otros
    "PLMR": "Seguros", "QSI": "Tecnología Médica",
    "XYZ": "Software/Cloud", "FLL": "Entretenimiento",
    "VINP": "Servicios Financieros",
}

# Roles de insider con peso de señal
ROLE_WEIGHTS = {
    "ceo": 10, "founder": 10, "president": 9, "cfo": 8, "coo": 8,
    "chairman": 9, "director": 7, "officer": 6, "vp": 5,
    "evp": 7, "svp": 6, "10% owner": 8, "beneficial owner": 7,
}

# Tipos de transacción
BUY_TYPES = {"buy", "purchase"}
SELL_TYPES = {"sale", "sell", "proposed sale"}
NEUTRAL_TYPES = {"option exercise", "gift", "conversion of derivative security"}


# ---------------------------------------------------------------------------
# Funciones de scraping
# ---------------------------------------------------------------------------

def fetch_page(page: int = 0, transaction_filter: str = "all") -> str:
    """Descarga una página de Finviz insider trading."""
    params = {}
    if page > 0:
        params["p"] = page
    if transaction_filter == "buy":
        params["tc"] = "1"
    elif transaction_filter == "sale":
        params["tc"] = "2"

    resp = requests.get(FINVIZ_URL, headers=HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_table(html: str) -> list[dict]:
    """Parsea la tabla de insider trading del HTML de Finviz."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "styled-table-new"})
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    records = []

    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < len(headers):
            continue
        record = {}
        for i, h in enumerate(headers):
            record[h] = cells[i].get_text(strip=True)
        records.append(record)

    return records


def clean_value(val_str: str) -> float:
    """Convierte string de valor monetario a float."""
    if not val_str or val_str in ("-", "N/A", ""):
        return 0.0
    cleaned = re.sub(r"[,$\s]", "", val_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def get_role_weight(relationship: str) -> int:
    """Calcula el peso de señal según el rol del insider."""
    rel_lower = relationship.lower()
    for role, weight in ROLE_WEIGHTS.items():
        if role in rel_lower:
            return weight
    return 4  # peso por defecto


def classify_transaction(transaction: str) -> str:
    """Clasifica el tipo de transacción."""
    t = transaction.lower()
    if any(bt in t for bt in BUY_TYPES):
        return "BUY"
    elif "proposed" in t:
        return "PROPOSED_SALE"
    elif any(st in t for st in SELL_TYPES):
        return "SALE"
    else:
        return "NEUTRAL"


def get_sector(ticker: str) -> str:
    """Devuelve el sector del ticker, con fallback a yfinance."""
    if ticker in SECTOR_MAP:
        return SECTOR_MAP[ticker]
    # Intentar con yfinance (puede ser lento, se usa como fallback)
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        if sector:
            return sector
        if industry:
            return industry
    except Exception:
        pass
    return "Otros"


def calculate_signal_score(row: dict) -> int:
    """
    Calcula un score de señal de 0-100 basado en:
    - Tipo de transacción (discrecional > plan > propuesta)
    - Rol del insider
    - Tamaño de la operación
    - Número de shares vs total
    """
    score = 0
    tx_type = row.get("tx_type", "NEUTRAL")

    # Tipo de transacción
    if tx_type == "BUY":
        score += 30  # compras son señal fuerte
    elif tx_type == "SALE":
        score += 20
    elif tx_type == "PROPOSED_SALE":
        score += 8
    else:
        return 0  # neutral no puntúa

    # Rol del insider
    score += min(row.get("role_weight", 4) * 1.5, 15)

    # Tamaño relativo de la operación
    value = row.get("value_usd", 0)
    if value >= 10_000_000:
        score += 25
    elif value >= 1_000_000:
        score += 18
    elif value >= 100_000:
        score += 10
    elif value >= 10_000:
        score += 5

    # % de shares vendidos vs total
    shares = clean_value(row.get("#Shares", "0"))
    total = clean_value(row.get("#Shares Total", "0"))
    if total > 0 and shares > 0:
        pct = shares / total
        if pct > 0.5:
            score += 20
        elif pct > 0.2:
            score += 12
        elif pct > 0.05:
            score += 6

    return min(int(score), 100)


def signal_label(score: int) -> str:
    if score >= 75:
        return "MAXIMA"
    elif score >= 55:
        return "FUERTE"
    elif score >= 35:
        return "MODERADA"
    else:
        return "DEBIL"


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def scrape_finviz(pages: int = 1, transaction_filter: str = "all",
                  enrich_sectors: bool = False) -> pd.DataFrame:
    """
    Descarga y procesa N páginas de Finviz insider trading.

    Args:
        pages: Número de páginas a descargar (cada página ~100 filas).
        transaction_filter: 'all', 'buy' o 'sale'.
        enrich_sectors: Si True, usa yfinance para tickers no mapeados.

    Returns:
        DataFrame con los datos procesados.
    """
    all_records = []

    for page in range(pages):
        print(f"  Descargando página {page + 1}/{pages}...", file=sys.stderr)
        try:
            html = fetch_page(page=page * 100, transaction_filter=transaction_filter)
            records = parse_table(html)
            all_records.extend(records)
            if page < pages - 1:
                time.sleep(1.5)  # respetar rate limit
        except Exception as e:
            print(f"  Error en página {page + 1}: {e}", file=sys.stderr)
            break

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    # Limpiar y enriquecer
    df["value_usd"] = df["Value ($)"].apply(clean_value)
    df["tx_type"] = df["Transaction"].apply(classify_transaction)
    df["role_weight"] = df["Relationship"].apply(get_role_weight)

    # Sector
    print("  Clasificando sectores...", file=sys.stderr)
    if enrich_sectors:
        df["sector"] = df["Ticker"].apply(get_sector)
    else:
        df["sector"] = df["Ticker"].apply(
            lambda t: SECTOR_MAP.get(t, "Otros")
        )

    # Signal score
    df["signal_score"] = df.apply(calculate_signal_score, axis=1)
    df["signal_label"] = df["signal_score"].apply(signal_label)

    # Separar flujos
    df["inflow"] = df.apply(
        lambda r: r["value_usd"] if r["tx_type"] == "BUY" else 0, axis=1
    )
    df["outflow"] = df.apply(
        lambda r: r["value_usd"] if r["tx_type"] in ("SALE", "PROPOSED_SALE") else 0,
        axis=1,
    )

    # Fecha de extracción
    df["extracted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    return df


def aggregate_by_sector(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega flujos por sector."""
    if df.empty:
        return pd.DataFrame()

    agg = (
        df[df["tx_type"].isin(["BUY", "SALE", "PROPOSED_SALE"])]
        .groupby("sector")
        .agg(
            inflows=("inflow", "sum"),
            outflows=("outflow", "sum"),
            n_buys=("tx_type", lambda x: (x == "BUY").sum()),
            n_sales=("tx_type", lambda x: x.isin(["SALE", "PROPOSED_SALE"]).sum()),
            avg_signal=("signal_score", "mean"),
        )
        .reset_index()
    )
    agg["net_flow"] = agg["inflows"] - agg["outflows"]
    agg["total_volume"] = agg["inflows"] + agg["outflows"]
    agg = agg.sort_values("total_volume", ascending=False)
    return agg


def get_top_transactions(df: pd.DataFrame, n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve top N compras y ventas por valor."""
    buys = (
        df[df["tx_type"] == "BUY"]
        .nlargest(n, "value_usd")[
            ["Ticker", "Owner", "Relationship", "Date", "Transaction",
             "value_usd", "signal_score", "signal_label", "sector"]
        ]
        .copy()
    )
    sales = (
        df[df["tx_type"].isin(["SALE", "PROPOSED_SALE"])]
        .nlargest(n, "value_usd")[
            ["Ticker", "Owner", "Relationship", "Date", "Transaction",
             "value_usd", "signal_score", "signal_label", "sector"]
        ]
        .copy()
    )
    return buys, sales


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extrae y analiza insider trading de Finviz"
    )
    parser.add_argument("--pages", type=int, default=1,
                        help="Número de páginas a descargar (default: 1)")
    parser.add_argument("--filter", choices=["all", "buy", "sale"], default="all",
                        help="Filtro de transacciones (default: all)")
    parser.add_argument("--enrich", action="store_true",
                        help="Enriquecer sectores con yfinance (más lento)")
    parser.add_argument("--output", default="insider_data.json",
                        help="Archivo de salida JSON (default: insider_data.json)")
    args = parser.parse_args()

    print(f"Extrayendo {args.pages} página(s) de Finviz...", file=sys.stderr)
    df = scrape_finviz(pages=args.pages, transaction_filter=args.filter,
                       enrich_sectors=args.enrich)

    if df.empty:
        print("ERROR: No se obtuvieron datos.", file=sys.stderr)
        sys.exit(1)

    sector_df = aggregate_by_sector(df)
    top_buys, top_sales = get_top_transactions(df)

    result = {
        "extracted_at": datetime.now().isoformat(),
        "total_transactions": len(df),
        "transactions": df.to_dict(orient="records"),
        "sector_aggregation": sector_df.to_dict(orient="records"),
        "top_buys": top_buys.to_dict(orient="records"),
        "top_sales": top_sales.to_dict(orient="records"),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"Datos guardados en: {args.output}", file=sys.stderr)
    print(f"Total transacciones: {len(df)}", file=sys.stderr)
    print(f"Sectores encontrados: {df['sector'].nunique()}", file=sys.stderr)


if __name__ == "__main__":
    main()
