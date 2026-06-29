"""Technical indicators."""

from __future__ import annotations


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def ema_series(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append(value * alpha + out[-1] * (1 - alpha))
    return out


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains = []
    losses = []
    for prev, cur in zip(values[-period - 1:-1], values[-period:]):
        diff = cur - prev
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def macd(values: list[float]) -> dict:
    if len(values) < 35:
        return {"macd": 0.0, "signal": 0.0, "hist": 0.0, "status": "資料不足"}
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26):], ema26)]
    signal_line = ema_series(macd_line, 9)
    hist = macd_line[-1] - signal_line[-1]
    prev_hist = macd_line[-2] - signal_line[-2]
    if hist > 0 and prev_hist <= 0:
        status = "剛翻正"
    elif hist > 0:
        status = "已翻正延續"
    elif hist < 0 and hist > prev_hist:
        status = "即將翻正"
    else:
        status = "偏弱"
    return {"macd": round(macd_line[-1], 4), "signal": round(signal_line[-1], 4), "hist": round(hist, 4), "status": status}


def volume_ratio(volumes: list[int], window: int = 20) -> float | None:
    if len(volumes) < window + 1:
        return None
    avg = sum(volumes[-window - 1:-1]) / window
    if avg <= 0:
        return None
    return round(volumes[-1] / avg, 2)


def analyze_prices(payload: dict) -> dict:
    rows = payload["prices"]
    closes = [float(row["close"]) for row in rows]
    volumes = [int(row["volume"]) for row in rows]
    close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else close
    change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else 0
    ma5 = sma(closes, 5)
    ma10 = sma(closes, 10)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60)
    m = macd(closes)
    rrsi = rsi(closes)
    vr = volume_ratio(volumes)
    support_high = round((ma20 or close) * 1.015, 2)
    support_low = round((ma20 or close) * 0.985, 2)
    breakout = round(max(row["high"] for row in rows[-20:]) * 1.01, 2)
    stop = round(min(support_low, close * 0.93), 2)
    trim1 = round(close * 1.06, 2)
    trim2 = round(close * 1.1, 2)
    return {
        "close": close,
        "previous_close": prev_close,
        "change_pct": change_pct,
        "ma5": round(ma5, 2) if ma5 else None,
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "ma60": round(ma60, 2) if ma60 else None,
        "macd": m,
        "rsi": rrsi,
        "volume_ratio": vr,
        "support_low": support_low,
        "support_high": support_high,
        "breakout": breakout,
        "stop": stop,
        "trim1": trim1,
        "trim2": trim2,
    }
