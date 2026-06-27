"""Technical analysis engine based on daily price bars."""

from __future__ import annotations

import math
from statistics import mean, pstdev

from radar.models.domain import MacdCandidate, PriceBar, StockMeta, TechnicalProfile


def _clamp(value: int | float, low: int = 1, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def _rolling_mean(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            result.append(None)
        else:
            result.append(mean(values[idx + 1 - window : idx + 1]))
    return result


def _rolling_std(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            result.append(None)
        else:
            result.append(pstdev(values[idx + 1 - window : idx + 1]))
    return result


def _ema(values: list[float], span: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(value * alpha + result[-1] * (1 - alpha))
    return result


def _rsi(values: list[float], window: int = 14) -> list[float | None]:
    if len(values) < 2:
        return [None] * len(values)
    gains = [0.0]
    losses = [0.0]
    for prev, current in zip(values[:-1], values[1:]):
        change = current - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    result: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            result.append(None)
            continue
        avg_gain = mean(gains[idx + 1 - window : idx + 1])
        avg_loss = mean(losses[idx + 1 - window : idx + 1])
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
    return result


def _safe_latest(values: list[float | None], fallback: float) -> float:
    for value in reversed(values):
        if value is not None and not math.isnan(float(value)):
            return float(value)
    return fallback


def evaluate_technical(stock: StockMeta, bars: list[PriceBar], price_source: str) -> TechnicalProfile:
    closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]
    latest_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else latest_close
    change_pct = 0.0 if prev_close == 0 else (latest_close - prev_close) / prev_close * 100

    ma5_list = _rolling_mean(closes, 5)
    ma10_list = _rolling_mean(closes, 10)
    ma20_list = _rolling_mean(closes, 20)
    ma60_list = _rolling_mean(closes, 60)
    ma120_list = _rolling_mean(closes, 120)
    volume_ma5_list = _rolling_mean([float(v) for v in volumes], 5)
    volume_ma20_list = _rolling_mean([float(v) for v in volumes], 20)
    std20_list = _rolling_std(closes, 20)
    ma5 = _safe_latest(ma5_list, latest_close)
    ma10 = _safe_latest(ma10_list, ma5)
    ma20 = _safe_latest(ma20_list, ma10)
    ma60 = _safe_latest(ma60_list, ma20)
    ma120 = _safe_latest(ma120_list, ma60)
    std20 = _safe_latest(std20_list, 0.0)
    bb_upper = ma20 + 2 * std20
    bb_lower = ma20 - 2 * std20

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif_list = [a - b for a, b in zip(ema12, ema26)]
    dea_list = _ema(dif_list, 9)
    hist_list = [a - b for a, b in zip(dif_list, dea_list)]
    dif = dif_list[-1]
    dea = dea_list[-1]
    macd_hist = hist_list[-1]
    macd_hist_prev = hist_list[-2] if len(hist_list) >= 2 else macd_hist

    rsi_list = _rsi(closes, 14)
    rsi = _safe_latest(rsi_list, 50.0)
    avg_volume_20 = mean(volumes[-20:]) if len(volumes) >= 20 else mean(volumes)
    volume_ma5 = _safe_latest(volume_ma5_list, float(volumes[-1]))
    volume_ma20 = _safe_latest(volume_ma20_list, float(avg_volume_20))
    volume_ratio = 1.0 if avg_volume_20 == 0 else volumes[-1] / avg_volume_20

    score = 45
    score += 10 if latest_close > ma20 else -8
    score += 8 if latest_close > ma60 else -6
    score += 6 if latest_close > ma120 else -5
    score += 8 if ma20 > ma60 else -4
    score += 6 if ma60 > ma120 else -3
    score += 8 if macd_hist > macd_hist_prev else -7
    score += 6 if macd_hist > 0 else 0
    if 45 <= rsi <= 65:
        score += 6
    elif 65 < rsi <= 72:
        score += 2
    elif rsi > 72:
        score -= 7
    elif rsi < 40:
        score -= 6
    if volume_ratio >= 1.2 and change_pct > 0:
        score += 6
    elif volume_ratio < 0.7:
        score -= 3
    trend_score = _clamp(score)

    returns: list[float] = []
    for prev, curr in zip(closes[-21:-1], closes[-20:]):
        if prev:
            returns.append((curr - prev) / prev)
    volatility = pstdev(returns) * 100 if len(returns) >= 5 else 0.0
    risk = 34
    if rsi > 72:
        risk += 18
    elif rsi < 35:
        risk += 10
    if latest_close < ma20:
        risk += 10
    if latest_close < ma60:
        risk += 12
    if macd_hist < macd_hist_prev:
        risk += 8
    if volume_ratio > 2.2:
        risk += 6
    if volatility > 2.8:
        risk += 8
    if latest_close > bb_upper:
        risk += 7
    if latest_close < bb_lower:
        risk += 12
    if not price_source.startswith("Yahoo Finance"):
        risk += 4
    risk_score = _clamp(risk)

    if latest_close > ma20 > ma60 > ma120:
        ma_state = "多頭排列，波段趨勢偏強"
    elif latest_close > ma20 and ma20 > ma60:
        ma_state = "站上短中期均線，趨勢改善"
    elif latest_close < ma20 and latest_close > ma60:
        ma_state = "跌破短均但中期支撐仍在"
    elif latest_close < ma60:
        ma_state = "跌破中期均線，需等待止穩"
    else:
        ma_state = "均線結構中性"

    macd_state = "MACD 已翻正" if macd_hist > 0 else "MACD 即將翻正" if macd_hist > macd_hist_prev and abs(macd_hist) <= max(latest_close * 0.006, 0.3) else "MACD 尚未改善"
    rsi_state = "RSI 偏熱" if rsi >= 70 else "RSI 偏弱" if rsi <= 42 else "RSI 健康"
    technical_summary = f"{ma_state}；{macd_state}；{rsi_state}；量能比 {volume_ratio:.2f}。"

    history: list[dict[str, float | int | str | None]] = []
    for idx, bar in enumerate(bars):
        bb_mid = ma20_list[idx]
        std = std20_list[idx]
        history.append(
            {
                "date": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "ma5": ma5_list[idx],
                "ma10": ma10_list[idx],
                "ma20": ma20_list[idx],
                "ma60": ma60_list[idx],
                "ma120": ma120_list[idx],
                "volume_ma5": volume_ma5_list[idx],
                "volume_ma20": volume_ma20_list[idx],
                "bb_upper": None if bb_mid is None or std is None else bb_mid + 2 * std,
                "bb_lower": None if bb_mid is None or std is None else bb_mid - 2 * std,
                "dif": dif_list[idx] if idx < len(dif_list) else None,
                "dea": dea_list[idx] if idx < len(dea_list) else None,
                "macd_hist": hist_list[idx] if idx < len(hist_list) else None,
                "rsi": rsi_list[idx],
            }
        )

    return TechnicalProfile(
        symbol=stock.symbol,
        name=stock.name,
        yahoo_symbol=stock.yahoo_symbol,
        price_source=price_source,
        bars_count=len(bars),
        latest_close=round(latest_close, 2),
        change_pct=round(change_pct, 2),
        ma5=round(ma5, 2),
        ma10=round(ma10, 2),
        ma20=round(ma20, 2),
        ma60=round(ma60, 2),
        ma120=round(ma120, 2),
        volume_ma5=round(volume_ma5, 0),
        volume_ma20=round(volume_ma20, 0),
        bb_upper=round(bb_upper, 2),
        bb_lower=round(bb_lower, 2),
        dif=round(dif, 4),
        dea=round(dea, 4),
        macd_hist=round(macd_hist, 4),
        macd_hist_prev=round(macd_hist_prev, 4),
        rsi=round(rsi, 1),
        volume_ratio=round(volume_ratio, 2),
        trend_score=trend_score,
        risk_score=risk_score,
        ma_state=ma_state,
        technical_summary=technical_summary,
        latest_date=bars[-1].date,
        history=history,
    )


def macd_turn_score(profile: TechnicalProfile) -> int:
    improvement = profile.macd_hist - profile.macd_hist_prev
    hist_scale = max(abs(profile.latest_close) * 0.006, 0.3)
    near_zero_bonus = max(0.0, 1.0 - abs(profile.macd_hist) / hist_scale)
    improving_bonus = max(0.0, min(1.0, improvement / hist_scale + 0.45))
    trend_bonus = profile.trend_score / 100
    rsi_penalty = 0.0
    if profile.rsi > 70:
        rsi_penalty = 0.18
    elif profile.rsi < 42:
        rsi_penalty = 0.10
    raw = 100 * (0.42 * near_zero_bonus + 0.35 * improving_bonus + 0.23 * trend_bonus - rsi_penalty)
    return _clamp(raw, 1, 99)


def _macd_status(profile: TechnicalProfile) -> str:
    if profile.macd_hist > 0 and profile.macd_hist_prev <= 0:
        return "剛翻正"
    if profile.macd_hist > 0 and profile.macd_hist > profile.macd_hist_prev:
        return "已翻正延續"
    hist_scale = max(profile.latest_close * 0.006, 0.3)
    if profile.macd_hist <= 0 and profile.macd_hist > profile.macd_hist_prev and abs(profile.macd_hist) <= hist_scale:
        return "即將翻正"
    if profile.macd_hist > profile.macd_hist_prev:
        return "動能改善"
    return "尚未改善"


def _macd_status_priority(status: str) -> int:
    return {
        "剛翻正": 4,
        "即將翻正": 3,
        "已翻正延續": 2,
        "動能改善": 1,
        "尚未改善": 0,
    }.get(status, 0)


def rank_macd_turn_candidates(stocks: list[StockMeta], profiles: dict[str, TechnicalProfile], limit: int = 10) -> list[MacdCandidate]:
    candidates: list[MacdCandidate] = []
    for stock in stocks:
        profile = profiles[stock.symbol]
        status = _macd_status(profile)
        if status == "尚未改善":
            continue
        score = macd_turn_score(profile) + _macd_status_priority(status) * 5
        if status == "即將翻正":
            reason = "MACD 柱狀體仍在負值，但已明顯收斂並靠近零軸，屬於波段提前觀察名單。"
        elif status == "剛翻正":
            reason = "MACD 剛由負轉正，接下來需確認量能與均線支撐，適合列入波段攻擊候選。"
        elif status == "已翻正延續":
            reason = "MACD 已在正值且動能延續，適合追蹤波段續航力，但不宜盲目追高。"
        else:
            reason = "MACD 動能改善，但距離翻正仍需確認，先列入觀察。"
        candidates.append(
            MacdCandidate(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                score=_clamp(score, 1, 99),
                hist_prev=profile.macd_hist_prev,
                hist_current=profile.macd_hist,
                rsi=profile.rsi,
                trend=profile.trend_score,
                latest_close=profile.latest_close,
                latest_date=profile.latest_date,
                price_source=profile.price_source,
                macd_status=status,
                reason=reason,
            )
        )
    candidates = sorted(candidates, key=lambda item: (_macd_status_priority(item.macd_status), item.score), reverse=True)
    return candidates[:limit]
