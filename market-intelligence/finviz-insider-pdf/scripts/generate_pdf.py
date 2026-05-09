#!/usr/bin/env python3
"""
generate_pdf.py — Genera un PDF visual con dashboard de insider trading.

Uso:
    python generate_pdf.py --data insider_data.json --output report.pdf
    python generate_pdf.py --data insider_data.json --output report.pdf --lang en

Requiere: reportlab, matplotlib, pandas
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, Image, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.utils import ImageReader

# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------

DARK_BG = colors.HexColor("#0D1117")
CARD_BG = colors.HexColor("#161B22")
ACCENT_GREEN = colors.HexColor("#00FF94")
ACCENT_RED = colors.HexColor("#FF4B4B")
ACCENT_YELLOW = colors.HexColor("#FFD700")
ACCENT_BLUE = colors.HexColor("#58A6FF")
ACCENT_PURPLE = colors.HexColor("#BC8CFF")
TEXT_PRIMARY = colors.HexColor("#E6EDF3")
TEXT_SECONDARY = colors.HexColor("#8B949E")
BORDER_COLOR = colors.HexColor("#30363D")

# Colores matplotlib
MPL_BG = "#0D1117"
MPL_CARD = "#161B22"
MPL_GREEN = "#00FF94"
MPL_RED = "#FF4B4B"
MPL_YELLOW = "#FFD700"
MPL_BLUE = "#58A6FF"
MPL_PURPLE = "#BC8CFF"
MPL_TEXT = "#E6EDF3"
MPL_SECONDARY = "#8B949E"

# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def fmt_usd(value: float) -> str:
    """Formatea un valor en USD de forma compacta."""
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:.0f}"


def signal_color(label: str) -> colors.Color:
    mapping = {
        "MAXIMA": ACCENT_RED,
        "FUERTE": ACCENT_YELLOW,
        "MODERADA": ACCENT_BLUE,
        "DEBIL": TEXT_SECONDARY,
    }
    return mapping.get(label, TEXT_SECONDARY)


def signal_emoji(label: str) -> str:
    mapping = {
        "MAXIMA": "●",
        "FUERTE": "●",
        "MODERADA": "●",
        "DEBIL": "○",
    }
    return mapping.get(label, "○")


# ---------------------------------------------------------------------------
# Gráficos matplotlib
# ---------------------------------------------------------------------------

def make_sector_bar_chart(sector_df: pd.DataFrame) -> io.BytesIO:
    """Gráfico de barras horizontales de flujos netos por sector."""
    df = sector_df.copy()
    df = df[df["total_volume"] > 0].head(12)
    df = df.sort_values("net_flow")

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.55)))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_CARD)

    colors_list = [MPL_GREEN if v >= 0 else MPL_RED for v in df["net_flow"]]
    bars = ax.barh(df["sector"], df["net_flow"] / 1e6, color=colors_list,
                   edgecolor="none", height=0.65)

    # Etiquetas de valor
    for bar, val in zip(bars, df["net_flow"]):
        x = bar.get_width()
        label = fmt_usd(val)
        ha = "left" if x >= 0 else "right"
        offset = 0.3 if x >= 0 else -0.3
        ax.text(x / 1e6 + offset, bar.get_y() + bar.get_height() / 2,
                label, va="center", ha=ha, color=MPL_TEXT, fontsize=8.5,
                fontweight="bold")

    ax.axvline(0, color=MPL_SECONDARY, linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_xlabel("Flujo Neto (USD Millones)", color=MPL_SECONDARY, fontsize=9)
    ax.set_title("Flujo Neto por Sector (Compras − Ventas)", color=MPL_TEXT,
                 fontsize=11, fontweight="bold", pad=12)
    ax.tick_params(colors=MPL_TEXT, labelsize=8.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MPL_SECONDARY)
    ax.spines["bottom"].set_color(MPL_SECONDARY)
    ax.xaxis.label.set_color(MPL_SECONDARY)
    ax.yaxis.label.set_color(MPL_SECONDARY)

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close()
    buf.seek(0)
    return buf


def make_volume_donut(sector_df: pd.DataFrame) -> io.BytesIO:
    """Donut chart del volumen total por sector."""
    df = sector_df[sector_df["total_volume"] > 0].head(8).copy()
    total = df["total_volume"].sum()

    # Agrupar sectores pequeños en "Otros"
    threshold = total * 0.02
    small = df[df["total_volume"] < threshold]
    main = df[df["total_volume"] >= threshold].copy()
    if not small.empty:
        otros_row = pd.DataFrame([{
            "sector": "Otros",
            "total_volume": small["total_volume"].sum(),
        }])
        main = pd.concat([main, otros_row], ignore_index=True)

    palette = [MPL_BLUE, MPL_GREEN, MPL_RED, MPL_YELLOW, MPL_PURPLE,
               "#FF8C00", "#00CED1", "#FF69B4", "#A9A9A9"]

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    wedges, texts, autotexts = ax.pie(
        main["total_volume"],
        labels=None,
        autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
        colors=palette[:len(main)],
        startangle=90,
        wedgeprops={"width": 0.55, "edgecolor": MPL_BG, "linewidth": 2},
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_color(MPL_BG)
        at.set_fontsize(7.5)
        at.set_fontweight("bold")

    # Leyenda
    legend_patches = [
        mpatches.Patch(color=palette[i], label=f"{row['sector']} ({fmt_usd(row['total_volume'])})")
        for i, (_, row) in enumerate(main.iterrows())
    ]
    ax.legend(handles=legend_patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.25), ncol=2,
              fontsize=7.5, frameon=False,
              labelcolor=MPL_TEXT)

    ax.set_title("Volumen Total por Sector", color=MPL_TEXT,
                 fontsize=11, fontweight="bold", pad=10)

    # Texto central
    ax.text(0, 0, fmt_usd(total), ha="center", va="center",
            color=MPL_TEXT, fontsize=12, fontweight="bold")
    ax.text(0, -0.18, "Total", ha="center", va="center",
            color=MPL_SECONDARY, fontsize=8)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close()
    buf.seek(0)
    return buf


def make_signal_histogram(df: pd.DataFrame) -> io.BytesIO:
    """Histograma de distribución de scores de señal."""
    scores = df[df["tx_type"].isin(["BUY", "SALE", "PROPOSED_SALE"])]["signal_score"]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_CARD)

    n, bins, patches = ax.hist(scores, bins=20, range=(0, 100),
                                edgecolor=MPL_BG, linewidth=0.5)
    # Colorear por zona
    for patch, left in zip(patches, bins[:-1]):
        if left >= 75:
            patch.set_facecolor(MPL_RED)
        elif left >= 55:
            patch.set_facecolor(MPL_YELLOW)
        elif left >= 35:
            patch.set_facecolor(MPL_BLUE)
        else:
            patch.set_facecolor(MPL_SECONDARY)

    ax.set_xlabel("Score de Señal (0-100)", color=MPL_SECONDARY, fontsize=9)
    ax.set_ylabel("Nº Transacciones", color=MPL_SECONDARY, fontsize=9)
    ax.set_title("Distribución de Señales", color=MPL_TEXT,
                 fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MPL_SECONDARY)
    ax.spines["bottom"].set_color(MPL_SECONDARY)

    # Zonas de referencia
    for x, label, color in [(75, "MÁXIMA", MPL_RED), (55, "FUERTE", MPL_YELLOW),
                              (35, "MODERADA", MPL_BLUE)]:
        ax.axvline(x, color=color, linewidth=1, linestyle="--", alpha=0.7)
        ax.text(x + 0.5, ax.get_ylim()[1] * 0.95, label,
                color=color, fontsize=7, va="top")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close()
    buf.seek(0)
    return buf


def make_buy_sell_comparison(sector_df: pd.DataFrame) -> io.BytesIO:
    """Gráfico de barras agrupadas: compras vs ventas por sector."""
    df = sector_df[sector_df["total_volume"] > 0].head(10).copy()
    df = df.sort_values("total_volume", ascending=False)

    x = np.arange(len(df))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_CARD)

    bars1 = ax.bar(x - width / 2, df["inflows"] / 1e6, width,
                   label="Compras (Inflows)", color=MPL_GREEN, alpha=0.85, edgecolor="none")
    bars2 = ax.bar(x + width / 2, df["outflows"] / 1e6, width,
                   label="Ventas (Outflows)", color=MPL_RED, alpha=0.85, edgecolor="none")

    ax.set_xticks(x)
    ax.set_xticklabels(df["sector"], rotation=35, ha="right",
                       color=MPL_TEXT, fontsize=8)
    ax.set_ylabel("USD Millones", color=MPL_SECONDARY, fontsize=9)
    ax.set_title("Compras vs Ventas por Sector", color=MPL_TEXT,
                 fontsize=11, fontweight="bold", pad=10)
    ax.tick_params(colors=MPL_TEXT, labelsize=8)
    ax.legend(fontsize=8.5, frameon=False, labelcolor=MPL_TEXT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(MPL_SECONDARY)
    ax.spines["bottom"].set_color(MPL_SECONDARY)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=MPL_BG, edgecolor="none")
    plt.close()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Estilos ReportLab
# ---------------------------------------------------------------------------

def build_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=26,
        textColor=TEXT_PRIMARY,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=TEXT_SECONDARY,
        spaceAfter=8,
        fontName="Helvetica",
        alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=ACCENT_BLUE,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        borderPad=0,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=TEXT_PRIMARY,
        spaceAfter=4,
        fontName="Helvetica",
        leading=13,
    )
    insight_style = ParagraphStyle(
        "InsightBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.black,
        spaceAfter=4,
        fontName="Helvetica",
        leading=13,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=TEXT_SECONDARY,
        fontName="Helvetica",
        leading=10,
    )
    caption_style = ParagraphStyle(
        "Caption",
        parent=styles["Normal"],
        fontSize=8,
        textColor=TEXT_SECONDARY,
        fontName="Helvetica-Oblique",
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "section": section_style,
        "body": body_style,
        "small": small_style,
        "caption": caption_style,
        "insight": insight_style,
    }


# ---------------------------------------------------------------------------
# Tablas ReportLab
# ---------------------------------------------------------------------------

def sector_table(sector_df: pd.DataFrame, styles: dict) -> Table:
    """Tabla de flujos por sector."""
    headers = ["Sector", "Inflows", "Outflows", "Flujo Neto", "Compras", "Ventas", "Vol. Total"]
    data = [headers]

    for _, row in sector_df.iterrows():
        net = row["net_flow"]
        net_color = "#00FF94" if net >= 0 else "#FF4B4B"
        net_str = fmt_usd(net)

        data.append([
            row["sector"],
            fmt_usd(row["inflows"]),
            fmt_usd(row["outflows"]),
            Paragraph(f'<font color="{net_color}"><b>{net_str}</b></font>', styles["body"]),
            str(int(row["n_buys"])),
            str(int(row["n_sales"])),
            fmt_usd(row["total_volume"]),
        ])

    col_widths = [4.5 * cm, 2.2 * cm, 2.2 * cm, 2.5 * cm, 1.5 * cm, 1.5 * cm, 2.5 * cm]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), ACCENT_BLUE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        # Data rows
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK_BG, CARD_BG]),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        # Borders
        ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT_BLUE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORDER_COLOR),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def transactions_table(tx_df: pd.DataFrame, styles: dict, tx_type: str = "BUY") -> Table:
    """Tabla de top transacciones."""
    headers = ["Ticker", "Insider", "Rol", "Fecha", "Valor (USD)", "Score", "Sector"]
    data = [headers]

    accent = ACCENT_GREEN if tx_type == "BUY" else ACCENT_RED

    for _, row in tx_df.iterrows():
        score = int(row.get("signal_score", 0))
        label = row.get("signal_label", "DEBIL")
        score_color = {
            "MAXIMA": "#FF4B4B", "FUERTE": "#FFD700",
            "MODERADA": "#58A6FF", "DEBIL": "#8B949E"
        }.get(label, "#8B949E")

        data.append([
            Paragraph(f'<font color="#58A6FF"><b>{row["Ticker"]}</b></font>', styles["body"]),
            Paragraph(f'<font color="#E6EDF3">{row["Owner"][:28]}</font>', styles["small"]),
            Paragraph(f'<font color="#8B949E">{row["Relationship"][:22]}</font>', styles["small"]),
            row.get("Date", ""),
            Paragraph(f'<font color="{score_color}"><b>{fmt_usd(row["value_usd"])}</b></font>', styles["body"]),
            Paragraph(f'<font color="{score_color}"><b>{score}</b></font>', styles["body"]),
            Paragraph(f'<font color="#8B949E">{row.get("sector", "Otros")[:18]}</font>', styles["small"]),
        ])

    col_widths = [1.5 * cm, 4.0 * cm, 3.5 * cm, 2.2 * cm, 2.5 * cm, 1.5 * cm, 3.2 * cm]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), DARK_BG),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_PRIMARY),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK_BG, CARD_BG]),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, accent),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORDER_COLOR),
        ("ALIGN", (4, 0), (5, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def kpi_table(data: dict, styles: dict) -> Table:
    """Tarjetas KPI en la parte superior."""
    total = data["total_transactions"]
    tx_df = pd.DataFrame(data["transactions"])
    buys = len(tx_df[tx_df["tx_type"] == "BUY"])
    sales = len(tx_df[tx_df["tx_type"].isin(["SALE", "PROPOSED_SALE"])])
    total_buy_vol = tx_df[tx_df["tx_type"] == "BUY"]["value_usd"].sum()
    total_sell_vol = tx_df[tx_df["tx_type"].isin(["SALE", "PROPOSED_SALE"])]["value_usd"].sum()
    sectors = tx_df["sector"].nunique()
    high_signal = len(tx_df[tx_df["signal_score"] >= 55])

    kpis = [
        ("TRANSACCIONES", str(total), TEXT_PRIMARY),
        ("COMPRAS", str(buys), ACCENT_GREEN),
        ("VENTAS", str(sales), ACCENT_RED),
        ("VOL. COMPRAS", fmt_usd(total_buy_vol), ACCENT_GREEN),
        ("VOL. VENTAS", fmt_usd(total_sell_vol), ACCENT_RED),
        ("SECTORES", str(sectors), ACCENT_BLUE),
        ("SEÑAL ALTA", str(high_signal), ACCENT_YELLOW),
    ]

    # Construir tabla de KPIs como 2 filas (label + valor)
    labels_row = []
    values_row = []
    for label, value, color in kpis:
        labels_row.append(
            Paragraph(f'<font color="#8B949E" size="7"><b>{label}</b></font>', styles["small"])
        )
        values_row.append(
            Paragraph(f'<font color="{color.hexval()}" size="14"><b>{value}</b></font>', styles["body"])
        )

    t = Table([labels_row, values_row], colWidths=[2.5 * cm] * len(kpis))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDER_COLOR),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("ROUNDEDCORNERS", [6]),
    ]))
    return t


# ---------------------------------------------------------------------------
# Generación de insights automáticos
# ---------------------------------------------------------------------------

def generate_insights(data: dict) -> list[str]:
    """Genera insights automáticos basados en los datos."""
    sector_df = pd.DataFrame(data["sector_aggregation"])
    tx_df = pd.DataFrame(data["transactions"])
    insights = []

    if sector_df.empty:
        return ["No hay datos suficientes para generar insights."]

    # Sector con mayor outflow
    top_sell = sector_df.nlargest(1, "outflows").iloc[0]
    insights.append(
        f"El sector <b>{top_sell['sector']}</b> lidera las ventas con "
        f"{fmt_usd(top_sell['outflows'])} en outflows "
        f"({int(top_sell['n_sales'])} transacciones). "
        f"Señal de toma de beneficios o deterioro de fundamentales."
    )

    # Sector con mayor inflow
    top_buy = sector_df.nlargest(1, "inflows").iloc[0]
    if top_buy["inflows"] > 0:
        insights.append(
            f"Las compras más significativas se concentran en <b>{top_buy['sector']}</b> "
            f"con {fmt_usd(top_buy['inflows'])} en inflows "
            f"({int(top_buy['n_buys'])} transacciones). "
            f"Posible acumulación por valoración atractiva o catalizadores próximos."
        )

    # Ratio compras/ventas
    total_buys = sector_df["inflows"].sum()
    total_sells = sector_df["outflows"].sum()
    if total_sells > 0:
        ratio = total_buys / total_sells
        sentiment = "bajista" if ratio < 0.3 else ("alcista" if ratio > 0.7 else "neutral")
        insights.append(
            f"El ratio compras/ventas es <b>{ratio:.2f}</b> — sentimiento general "
            f"<b>{sentiment.upper()}</b>. "
            f"Inflows totales: {fmt_usd(total_buys)} vs Outflows: {fmt_usd(total_sells)}."
        )

    # Señales de alta convicción
    high_signal = tx_df[tx_df["signal_score"] >= 75]
    if not high_signal.empty:
        tickers = ", ".join(high_signal["Ticker"].unique()[:5])
        insights.append(
            f"Señales de máxima convicción detectadas en: <b>{tickers}</b>. "
            f"Estas transacciones tienen score ≥75 y merecen seguimiento prioritario."
        )

    # Coordinación (múltiples insiders mismo ticker)
    multi = tx_df.groupby("Ticker").size()
    multi_tickers = multi[multi >= 3].index.tolist()
    if multi_tickers:
        tickers_str = ", ".join(multi_tickers[:4])
        insights.append(
            f"Coordinación detectada (3+ insiders): <b>{tickers_str}</b>. "
            f"La actividad coordinada amplifica la señal de la transacción."
        )

    return insights


# ---------------------------------------------------------------------------
# Construcción del PDF
# ---------------------------------------------------------------------------

def build_pdf(data: dict, output_path: str):
    """Construye el PDF completo del dashboard."""
    styles = build_styles()
    extracted_at = data.get("extracted_at", datetime.now().isoformat())[:16]

    # Preparar DataFrames
    sector_df = pd.DataFrame(data["sector_aggregation"])
    top_buys = pd.DataFrame(data["top_buys"])
    top_sales = pd.DataFrame(data["top_sales"])
    tx_df = pd.DataFrame(data["transactions"])

    # Generar gráficos
    print("  Generando gráficos...", file=sys.stderr)
    bar_buf = make_sector_bar_chart(sector_df)
    donut_buf = make_volume_donut(sector_df)
    hist_buf = make_signal_histogram(tx_df)
    compare_buf = make_buy_sell_comparison(sector_df)

    # Ensure all buffers are at position 0
    for buf in [bar_buf, donut_buf, hist_buf, compare_buf]:
        buf.seek(0)

    # Configurar documento
    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    page_w, page_h = A4
    content_w = page_w - 3 * cm

    # Frame y template
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        content_w, page_h - 3 * cm,
        id="main"
    )

    def header_footer(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(CARD_BG)
        canvas.rect(0, page_h - 1.2 * cm, page_w, 1.2 * cm, fill=1, stroke=0)
        canvas.setFillColor(ACCENT_BLUE)
        canvas.rect(0, page_h - 1.2 * cm, 4 * mm, 1.2 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(TEXT_PRIMARY)
        canvas.drawString(1 * cm, page_h - 0.8 * cm, "FINVIZ INSIDER TRADING DASHBOARD")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_SECONDARY)
        canvas.drawRightString(page_w - 1.5 * cm, page_h - 0.8 * cm,
                               f"Datos: {extracted_at}  |  Pág. {doc.page}")
        # Footer
        canvas.setFillColor(CARD_BG)
        canvas.rect(0, 0, page_w, 0.8 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(TEXT_SECONDARY)
        canvas.drawString(1.5 * cm, 0.3 * cm,
                          "Fuente: Finviz.com — Solo informativo, no constituye asesoramiento financiero.")
        canvas.drawRightString(page_w - 1.5 * cm, 0.3 * cm,
                               "Generado con finviz-insider-pdf skill")
        canvas.restoreState()

    template = PageTemplate(id="main", frames=[frame], onPage=header_footer)
    doc.addPageTemplates([template])

    # ---------------------------------------------------------------------------
    # Contenido
    # ---------------------------------------------------------------------------
    story = []

    # --- Portada / Header ---
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Insider Trading Dashboard", styles["title"]))
    story.append(Paragraph(
        f"Rotación Sectorial de Capital · Datos extraídos: {extracted_at} · Fuente: Finviz.com",
        styles["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_BLUE, spaceAfter=8))

    # --- KPIs ---
    story.append(kpi_table(data, styles))
    story.append(Spacer(1, 0.5 * cm))

    # --- Gráfico de barras + donut en paralelo ---
    story.append(Paragraph("Flujos por Sector", styles["section"]))
    bar_img = Image(bar_buf, width=content_w * 0.62, height=5.5 * cm)
    donut_img = Image(donut_buf, width=content_w * 0.36, height=5.5 * cm)
    charts_row = Table(
        [[bar_img, donut_img]],
        colWidths=[content_w * 0.63, content_w * 0.37],
    )
    charts_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(charts_row)
    story.append(Spacer(1, 0.3 * cm))

    # --- Tabla de sectores ---
    story.append(Paragraph("Agregación por Sector", styles["section"]))
    if not sector_df.empty:
        story.append(sector_table(sector_df.head(12), styles))
    story.append(Spacer(1, 0.4 * cm))

    # --- Gráfico comparativo ---
    compare_img = Image(compare_buf, width=content_w, height=4.5 * cm)
    story.append(compare_img)
    story.append(Spacer(1, 0.4 * cm))

    # --- Top Compras ---
    story.append(Paragraph("Top Compras (Inflows)", styles["section"]))
    if not top_buys.empty:
        story.append(transactions_table(top_buys, styles, tx_type="BUY"))
    story.append(Spacer(1, 0.4 * cm))

    # --- Top Ventas ---
    story.append(Paragraph("Top Ventas (Outflows)", styles["section"]))
    if not top_sales.empty:
        story.append(transactions_table(top_sales, styles, tx_type="SALE"))
    story.append(Spacer(1, 0.4 * cm))

    # --- Histograma de señales ---
    story.append(Paragraph("Distribución de Señales", styles["section"]))
    hist_img = Image(hist_buf, width=content_w * 0.65, height=3.8 * cm)
    # Leyenda de señales
    signal_legend = Table([
        [
            Paragraph('<font color="#FF4B4B"><b>● MÁXIMA</b></font> Score ≥75', styles["small"]),
            Paragraph('<font color="#FFD700"><b>● FUERTE</b></font> Score 55-74', styles["small"]),
            Paragraph('<font color="#58A6FF"><b>● MODERADA</b></font> Score 35-54', styles["small"]),
            Paragraph('<font color="#8B949E"><b>○ DÉBIL</b></font> Score <35', styles["small"]),
        ]
    ], colWidths=[content_w * 0.25] * 4)
    signal_legend.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
    ]))
    hist_row = Table(
        [[hist_img, signal_legend]],
        colWidths=[content_w * 0.66, content_w * 0.34],
    )
    hist_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(hist_row)
    story.append(Spacer(1, 0.5 * cm))

    # --- Insights ---
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6))
    story.append(Paragraph("Insights y Recomendaciones", styles["section"]))
    insights = generate_insights(data)
    for i, insight in enumerate(insights, 1):
        story.append(Paragraph(
            f'<font color="#1a6fcc"><b>{i}.</b></font> {insight}',
            styles["insight"]
        ))
        story.append(Spacer(1, 0.2 * cm))

    # --- Nota metodológica ---
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6))
    base_styles = getSampleStyleSheet()
    nota_style = ParagraphStyle(
        "NotaStyle",
        parent=base_styles["Normal"],
        fontSize=7.5,
        textColor=colors.HexColor("#333333"),
        fontName="Helvetica",
        leading=10,
    )
    story.append(Paragraph(
        "<b>Nota metodológica:</b> Los flujos se calculan sumando el campo Value($) de Finviz "
        "para transacciones de tipo Buy (inflows) y Sale/Proposed Sale (outflows). "
        "El score de señal pondera el tipo de transacción (discrecional > plan 10b5-1 > propuesta), "
        "el rol del insider, el tamaño absoluto y el porcentaje de holdings transaccionados. "
        "Este reporte es solo informativo y no constituye asesoramiento financiero.",
        nota_style
    ))

    # Construir PDF
    print(f"  Construyendo PDF: {output_path}", file=sys.stderr)
    doc.build(story)
    print(f"  PDF generado exitosamente.", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera PDF de insider trading")
    parser.add_argument("--data", required=True,
                        help="Archivo JSON con datos de finviz_scraper.py")
    parser.add_argument("--output", default="insider_dashboard.pdf",
                        help="Ruta del PDF de salida")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"ERROR: No se encuentra el archivo {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    build_pdf(data, args.output)
    print(f"PDF guardado en: {args.output}")


if __name__ == "__main__":
    main()
