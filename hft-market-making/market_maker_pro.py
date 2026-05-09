from sema4ai.actions import action
import ccxt
import ccxt.pro as ccxtpro
import pandas as pd
import asyncio
from datetime import datetime
from typing import Dict, List, Literal, Optional

_orderbook_cache = {}

@action
async def generate_super_mm_insights_pro(
    exchange_id: str = "binance",
    symbol: str = "BTC/USDT:USDT",
    symbols: Optional[List[str]] = None,
    timeframe: str = "5m",
    mode: Literal["scalp", "swing"] = "scalp",
    my_current_position: float = 0.0,
    ob_depth: int = 50,
    use_pro: bool = True
) -> Dict:
    """
    SUPER SKILL MARKET MAKER para trading discrecional.
    Versión loca: más rápida, más profunda y multi-símbolo.
    """
    symbols = symbols or [symbol]
    results = {}

    for sym in symbols:
        try:
            if use_pro:
                exchange = getattr(ccxtpro, exchange_id)({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
                orderbook = await exchange.watch_order_book(sym, limit=ob_depth)
                ticker = await exchange.watch_ticker(sym)
                ohlcv = await exchange.fetch_ohlcv(sym, timeframe, limit=100)
                await exchange.close()
            else:
                exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
                # Fallback implementation
                orderbook = exchange.fetch_order_book(sym, limit=ob_depth)
                ticker = exchange.fetch_ticker(sym)
                ohlcv = exchange.fetch_ohlcv(sym, timeframe, limit=100)

            mid = (orderbook['bids'][0][0] + orderbook['asks'][0][0]) / 2

            bids_vol_10 = sum(b[1] for b in orderbook['bids'][:10])
            asks_vol_10 = sum(a[1] for a in orderbook['asks'][:10])
            imbalance_10 = (bids_vol_10 - asks_vol_10) / (bids_vol_10 + asks_vol_10 + 1e-8)

            bids_vol_full = sum(b[1] for b in orderbook['bids'][:ob_depth])
            asks_vol_full = sum(a[1] for a in orderbook['asks'][:ob_depth])
            imbalance_full = (bids_vol_full - asks_vol_full) / (bids_vol_full + asks_vol_full + 1e-8)

            prev_ob = _orderbook_cache.get(sym)
            imbalance_delta = imbalance_10 - prev_ob.get('imbalance_10', 0) if prev_ob else 0
            _orderbook_cache[sym] = {'imbalance_10': imbalance_10, 'timestamp': datetime.utcnow()}

            df = pd.DataFrame(ohlcv, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            vol = df['c'].pct_change().std() * 100 if len(df) > 1 else 0

            # Mocked funding/oi for standalone template, in production use actual skills
            funding = 0.0001 
            oi_change = 5.0

            bias_score = 0.0
            reasons = []

            if imbalance_10 > 0.22:
                bias_score += 3.0
                reasons.append(f"📈 OB Imbalance fuerte (+{imbalance_10:.3f}) en top 10")
            elif imbalance_10 < -0.22:
                bias_score -= 3.0
                reasons.append(f"📉 OB Imbalance fuerte ({imbalance_10:.3f}) en top 10")

            if abs(imbalance_delta) > 0.08:
                reasons.append(f"⚡ Delta imbalance rápido ({imbalance_delta:.3f}) → momentum")

            if funding > 0.0008:
                bias_score -= 2.0
                reasons.append(f"💰 Funding alto positivo → sesgo SHORT")
            elif funding < -0.0008:
                bias_score += 2.0
                reasons.append(f"💰 Funding negativo → sesgo LONG")

            if abs(oi_change) > 15:
                bias_score += 1.5 * (1 if oi_change > 0 else -1)
                reasons.append("🔥 OI cambio fuerte → confirma dirección")

            if abs(my_current_position) > 0.05:
                skew_effect = my_current_position * 25
                bias_score -= skew_effect
                reasons.append(f"🧳 Inventory skew: {skew_effect:.1f}")

            if bias_score >= 4.0:
                rec = "🟢 LONG FUERTE"
                conf = "Muy Alta"
            elif bias_score <= -4.0:
                rec = "🔴 SHORT FUERTE"
                conf = "Muy Alta"
            elif bias_score >= 1.5:
                rec = "🟡 LONG con ventaja"
                conf = "Alta"
            elif bias_score <= -1.5:
                rec = "🟡 SHORT con ventaja"
                conf = "Alta"
            else:
                rec = "⚪ NEUTRAL / esperar mejor setup"
                conf = "Baja"

            results[sym] = {
                "mid_price": round(mid, 2),
                "recommendation": rec,
                "confidence": conf,
                "bias_score": round(bias_score, 2),
                "imbalance_top10": round(imbalance_10, 3),
                "imbalance_full": round(imbalance_full, 3),
                "imbalance_delta": round(imbalance_delta, 3),
                "predicted_funding_bps": round(funding * 10000, 2),
                "volatility": round(vol, 3),
                "reasons": reasons[:8],
                "suggested_tp_sl": _calculate_tp_sl(mid, mode, vol),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            results[sym] = {"error": str(e)}

    return {
        "mode": mode,
        "timeframe": timeframe,
        "results": results,
        "global_advice": "Usa bias_score > 4 o < -4 para entradas agresivas. Combina siempre con tu discrecional."
    }

def _calculate_tp_sl(mid: float, mode: str, vol: float):
    if mode == "scalp":
        return {"tp": round(mid * 1.006, 2), "sl": round(mid * 0.994, 2)}
    else:
        return {"tp": round(mid * 1.018, 2), "sl": round(mid * 0.978, 2)}
