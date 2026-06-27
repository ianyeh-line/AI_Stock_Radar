"""Technical Radar engine."""

from __future__ import annotations

from statistics import mean

from radar.datasource.market_data import load_price_history
from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import TechnicalSnapshot


def _moving_average(values: list[float], window: int) -> float:
    if len(values) < window:
        return round(mean(values), 2)
    return round(mean(values[-window:]), 2)


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    recent = values[-(period + 1):]
    for prev, curr in zip(recent, recent[1:]):
        diff = curr - prev
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _score(price: float, ma5: float, ma20: float, ma60: float, rsi14: float) -> tuple[int, str, str, int]:
    score = 50
    reasons: list[str] = []

    if price > ma20:
        score += 12
        reasons.append("收盤價站上月線")
    else:
        score -= 10
        reasons.append("收盤價低於月線")

    if ma5 > ma20:
        score += 10
        reasons.append("短均線優於月線")
    else:
        score -= 6
        reasons.append("短均線尚未轉強")

    if price > ma60:
        score += 8
        reasons.append("價格高於季線")
    else:
        score -= 8
        reasons.append("價格低於季線")

    if 45 <= rsi14 <= 68:
        score += 8
        reasons.append("RSI 位於健康區間")
    elif rsi14 > 72:
        score -= 10
        reasons.append("RSI 過熱，追價風險升高")
    elif rsi14 < 35:
        score -= 8
        reasons.append("RSI 偏弱，動能不足")
    else:
        score += 2
        reasons.append("RSI 中性")

    score = max(25, min(92, score))

    if score >= 76:
        trend = "偏多"
    elif score >= 60:
        trend = "中性偏多"
    elif score >= 45:
        trend = "中性偏弱"
    else:
        trend = "偏弱"

    confidence = max(52, min(92, 50 + abs(score - 50)))
    return score, trend, "、".join(reasons[:3]), confidence


def build_technical_snapshot(ticker: str) -> TechnicalSnapshot:
    profile = WATCHLIST[ticker]
    data_source, history = load_price_history(ticker)
    closes = [float(row["close"]) for row in history if row.get("close") is not None]
    volumes = [int(row.get("volume", 0)) for row in history]

    price = round(closes[-1], 2)
    ma5 = _moving_average(closes, 5)
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    rsi14 = _rsi(closes, 14)
    volume = volumes[-1] if volumes else 0
    score, trend, signal, confidence = _score(price, ma5, ma20, ma60, rsi14)

    enriched: list[dict[str, float | int | str]] = []
    rolling_closes: list[float] = []
    for row in history:
        close = float(row["close"])
        rolling_closes.append(close)
        enriched.append(
            {
                "date": str(row["date"]),
                "close": round(close, 2),
                "ma5": _moving_average(rolling_closes, 5),
                "ma20": _moving_average(rolling_closes, 20),
                "volume": int(row.get("volume", 0)),
            }
        )

    return TechnicalSnapshot(
        ticker=ticker,
        name=profile["name"],
        price=price,
        ma5=ma5,
        ma20=ma20,
        ma60=ma60,
        rsi14=rsi14,
        volume=volume,
        trend=trend,
        signal=signal,
        score=score,
        confidence=confidence,
        data_source=data_source,
        chart_note="技術線圖優先使用 Yahoo 即時價格；若資料無法取得，會自動改用內建模擬價格。",
        history=enriched,
    )
