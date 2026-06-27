"""Price datasource and fallback chart data for AI Stock Radar.

v0.8.0 tries Yahoo Finance's public chart endpoint for Taiwan stocks. If the
network is unavailable, blocked, or returns incomplete data, the product falls
back to deterministic sample data so the dashboard always remains usable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import random
import urllib.request

from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import PricePoint


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"


def _moving_average(values: list[float], window: int) -> list[float | None]:
    result: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < window:
            result.append(None)
            continue
        result.append(round(sum(values[idx + 1 - window : idx + 1]) / window, 2))
    return result


def _attach_ma(points: list[tuple[str, float, int | None]]) -> list[PricePoint]:
    closes = [point[1] for point in points]
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    return [
        PricePoint(date=day, close=round(close, 2), ma20=ma20[idx], ma60=ma60[idx], volume=volume)
        for idx, (day, close, volume) in enumerate(points)
    ]


def _fallback_history(ticker: str, days: int = 150) -> list[PricePoint]:
    """Generate stable fallback history by ticker.

    The data is not a market quote. It is a deterministic backup used only when
    online quote retrieval fails. The dashboard labels it clearly as fallback.
    """

    seed = int(ticker) if ticker.isdigit() else 1000
    random.seed(seed)
    base_price = {
        "2330": 980,
        "2382": 290,
        "3231": 110,
        "6669": 2200,
        "2449": 110,
        "2454": 1250,
        "2308": 390,
        "8299": 520,
        "2603": 190,
    }.get(ticker, 100)
    drift = {
        "2330": 0.22,
        "2382": 0.12,
        "3231": 0.10,
        "6669": 0.18,
        "2449": 0.04,
        "2454": 0.08,
        "2308": 0.06,
        "8299": -0.02,
        "2603": 0.03,
    }.get(ticker, 0.02)

    points: list[tuple[str, float, int | None]] = []
    price = float(base_price)
    today = datetime.now().date()
    for offset in range(days, 0, -1):
        day = today - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        wave = math.sin(offset / 9) * 0.8
        noise = random.uniform(-1.3, 1.3)
        price = max(10, price * (1 + (drift + wave + noise) / 1000))
        volume = int(8_000_000 + random.random() * 5_000_000)
        points.append((day.isoformat(), price, volume))

    return _attach_ma(points)


def _fetch_yahoo_history(ticker: str) -> list[PricePoint]:
    symbol = f"{ticker}.TW"
    url = YAHOO_CHART_URL.format(symbol=symbol)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Stock-Radar/0.8"})
    with urllib.request.urlopen(request, timeout=6) as response:  # noqa: S310 - public quote endpoint only
        payload = json.loads(response.read().decode("utf-8", errors="ignore"))

    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise ValueError("Yahoo chart result is empty")
    chart = result[0]
    timestamps = chart.get("timestamp") or []
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    points: list[tuple[str, float, int | None]] = []
    for idx, ts in enumerate(timestamps):
        if idx >= len(closes) or closes[idx] is None:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        volume = None
        if idx < len(volumes) and volumes[idx] is not None:
            volume = int(volumes[idx])
        points.append((day, float(closes[idx]), volume))

    if len(points) < 50:
        raise ValueError("Yahoo chart history is too short")
    return _attach_ma(points[-150:])


def load_price_history(ticker: str, prefer_live: bool = True) -> tuple[str, list[PricePoint]]:
    if prefer_live:
        try:
            return "即時 Yahoo Finance", _fetch_yahoo_history(ticker)
        except Exception:
            pass
    return "示意備援資料", _fallback_history(ticker)


def load_all_price_histories(prefer_live: bool = False) -> dict[str, tuple[str, list[PricePoint]]]:
    return {ticker: load_price_history(ticker, prefer_live=prefer_live) for ticker in WATCHLIST}
