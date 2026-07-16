"""Technical indicators for AI Stock Radar."""

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


def kd(values_high: list[float], values_low: list[float], values_close: list[float], period: int = 9) -> dict:
    if len(values_close) < period:
        return {"k": None, "d": None, "j": None, "status": "資料不足"}
    k = 50.0
    d = 50.0
    start = max(0, len(values_close) - 30)
    for idx in range(start, len(values_close)):
        lo = min(values_low[max(0, idx - period + 1):idx + 1])
        hi = max(values_high[max(0, idx - period + 1):idx + 1])
        rsv = 50.0 if hi == lo else (values_close[idx] - lo) / (hi - lo) * 100
        k = k * 2 / 3 + rsv / 3
        d = d * 2 / 3 + k / 3
    j = 3 * k - 2 * d
    if k > d and k < 80:
        status = "KD偏多"
    elif k > 80:
        status = "KD高檔，留意震盪"
    elif k < d:
        status = "KD轉弱"
    else:
        status = "KD中性"
    return {"k": round(k, 1), "d": round(d, 1), "j": round(j, 1), "status": status}


def bias(values: list[float], window: int = 20) -> float | None:
    ma = sma(values, window)
    if not ma:
        return None
    return round((values[-1] - ma) / ma * 100, 2)


def macd_components(values: list[float]) -> dict:
    """Return MACD series aligned for charting.

    In this project, `macd` means DIF / MACD line, and `signal` means DEA.
    The histogram is DIF - DEA. This naming matches the labels used in many
    Taiwan chart apps more closely than the generic English naming.
    """
    if len(values) < 35:
        return {"macd_line": [], "signal_line": [], "hist": []}
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_line = [a - b for a, b in zip(ema12[-len(ema26):], ema26)]
    signal_line = ema_series(macd_line, 9)
    hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    # Align all three series to the shortest length.
    n = min(len(macd_line), len(signal_line), len(hist))
    return {
        "macd_line": macd_line[-n:],
        "signal_line": signal_line[-n:],
        "hist": hist[-n:],
    }


def macd(values: list[float]) -> dict:
    """Return MACD status with correct zero-axis wording.

    v3.2.0 fix:
    A positive MACD/DIF line must never be labelled as `0軸下方偏弱`.
    When DIF is above zero but declining, the correct wording is `0軸上方轉弱/整理`.
    """
    comp = macd_components(values)
    macd_line = comp["macd_line"]
    signal_line = comp["signal_line"]
    hist_series = comp["hist"]
    if len(macd_line) < 5 or len(signal_line) < 2 or len(hist_series) < 2:
        return {
            "macd": 0.0,
            "signal": 0.0,
            "hist": 0.0,
            "prev_macd": 0.0,
            "prev_hist": 0.0,
            "status": "資料不足",
            "hist_status": "資料不足",
            "zero_axis_status": "資料不足",
            "zero_axis_score": 0,
        }
    cur_macd = macd_line[-1]
    prev_macd = macd_line[-2]
    macd_5 = macd_line[-5]
    cur_signal = signal_line[-1]
    cur_hist = hist_series[-1]
    prev_hist = hist_series[-2]
    close = values[-1] or 1.0

    if cur_hist > 0 and prev_hist <= 0:
        hist_status = "柱狀體剛翻正"
    elif cur_hist > 0:
        hist_status = "柱狀體已翻正延續"
    elif cur_hist < 0 and cur_hist > prev_hist:
        hist_status = "柱狀體即將翻正"
    else:
        hist_status = "柱狀體偏弱"

    macd_pct = cur_macd / close if close else 0
    rising_5d = cur_macd > prev_macd > macd_5
    near_zero = -0.006 <= macd_pct < 0

    if cur_macd > 0 and prev_macd <= 0:
        zero_axis_status = "剛從0軸翻正"
        zero_axis_score = 100
    elif cur_macd > 0 and cur_macd >= prev_macd:
        zero_axis_status = "0軸上方延續"
        zero_axis_score = 82
    elif cur_macd > 0 and cur_macd < prev_macd:
        zero_axis_status = "0軸上方整理"
        zero_axis_score = 62
    elif near_zero and rising_5d:
        zero_axis_status = "即將從0軸翻正"
        zero_axis_score = 95
    elif cur_macd < 0 and cur_macd > prev_macd:
        zero_axis_status = "0軸下方改善"
        zero_axis_score = 58
    else:
        zero_axis_status = "0軸下方偏弱"
        zero_axis_score = 20

    return {
        "macd": round(cur_macd, 4),
        "signal": round(cur_signal, 4),
        "hist": round(cur_hist, 4),
        "prev_macd": round(prev_macd, 4),
        "prev_hist": round(prev_hist, 4),
        "status": hist_status,
        "hist_status": hist_status,
        "zero_axis_status": zero_axis_status,
        "zero_axis_score": zero_axis_score,
    }


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
    highs = [float(row["high"]) for row in rows]
    lows = [float(row["low"]) for row in rows]
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
    kdj = kd(highs, lows, closes)
    b20 = bias(closes, 20)
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
        "kd": kdj,
        "bias20": b20,
        "volume_ratio": vr,
        "support_low": support_low,
        "support_high": support_high,
        "breakout": breakout,
        "stop": stop,
        "trim1": trim1,
        "trim2": trim2,
    }
