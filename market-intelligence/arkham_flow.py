import os
import requests
from datetime import datetime
from sema4ai.actions import action

@action
def arkham_cex_flow_tracking(period: str = "this week", min_usd: float = 250000) -> str:
    """
    Arkham CEX Flow Tracking INTELIGENTE para Market Makers.
    Usa tu API-Key oficial.
    Aplica el WALKTHROUGH completo anti-falsos-positivos.
    """
    api_key = os.getenv("ARKHAM_API_KEY")
    if not api_key:
        return "❌ FALTA ARKHAM_API_KEY en .env o variables del Action Server."

    base_url = "https://api.arkhamintelligence.com"
    headers = {"API-Key": api_key}

    mm_list = [
        "gsr-markets", "wintermute", "jump-trading", "cumberland",
        "market-making-pro", "galaxy-digital", "b2c2", "flow-traders"
    ]

    CEX_LABELS = ["binance", "coinbase", "okx", "bybit", "kraken", "bitfinex", "huobi", "gate.io"]
    DEX_LABELS = ["uniswap", "1inch", "pancake", "router", "curve"]
    STABLES = ["usdt", "usdc", "dai", "usdc.e", "tusd", "fdusd"]

    def is_cex(label: str) -> bool:
        return any(k in (label or "").lower() for k in CEX_LABELS)
    def is_dex(label: str) -> bool:
        return any(k in (label or "").lower() for k in DEX_LABELS)
    def is_stable(token: str) -> bool:
        return (token or "").lower() in [s.lower() for s in STABLES]

    if "weekend" in period.lower() or "finde" in period.lower():
        time_last = "3d"
    elif "week" in period.lower() or "semana" in period.lower():
        time_last = "7d"
    else:
        time_last = "24h"

    resumen = [f"🔍 **ARKHAM CEX FLOW TRACKING - {period.upper()}** ({datetime.now().strftime('%d/%m %H:%M')})\n"]
    resumen.append("WALKTHROUGH APLICADO AUTOMÁTICAMENTE:\n")

    for entity in mm_list:
        params = {"base": entity, "timeLast": time_last, "limit": 50, "sortDir": "desc", "flow": "all"}
        try:
            r = requests.get(f"{base_url}/transfers", headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                resumen.append(f"⚠️ {entity}: HTTP {r.status_code}")
                continue

            transfers = r.json().get("transfers", []) or r.json().get("items", [])
            for t in transfers:
                usd = float(t.get("usd", 0))
                if usd < min_usd: continue

                token = t.get("token", "").upper()
                from_label = (t.get("fromEntity") or {}).get("name", "") or ""
                to_label = (t.get("toEntity") or {}).get("name", "") or ""
                direction = "OUTFLOW" if entity.lower() in from_label.lower() else "INFLOW"

                if is_stable(token) and not is_cex(to_label) and not is_cex(from_label):
                    continue

                if is_stable(token) and is_dex(to_label):
                    tipo = "REBALANCEO / Liquidity (AMBIGUO - IGNORAR)"
                elif direction == "OUTFLOW" and is_cex(to_label):
                    tipo = "🚨 VENTA FUERTE" if not is_stable(token) else "🚨 POSIBLE FUNDING TRADING"
                elif direction == "INFLOW" and is_cex(from_label):
                    tipo = "🚨 COMPRA / ACUMULACIÓN"
                elif direction == "OUTFLOW" and is_cex(to_label) and is_stable(token):
                    tipo = "POSIBLE VENTA (stable a CEX)"
                else:
                    tipo = "MOVIMIENTO INTERNO / AMBIGUO (IGNORAR)"

                if "VENTA" in tipo or "COMPRA" in tipo or "FUNDING" in tipo:
                    resumen.append(
                        f"🔸 {entity.replace('-',' ').title()} | {direction} | "
                        f"${usd:,.0f} {token} → {to_label or from_label} | {tipo}"
                    )

        except Exception as e:
            resumen.append(f"❌ Error {entity}: {str(e)[:80]}")

    resultado = "\n".join(resumen)
    return resultado if len(resumen) > 2 else f"No hay movimientos relevantes > ${min_usd:,.0f} en {period}."
