"""Market price datasource for AI Stock Radar.

The product first tries Yahoo's public chart endpoint for Taiwan tickers.
If the request fails, it falls back to deterministic sample data so the dashboard
always remains usable during development and demos.
"""

from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import math
import random
import urllib.request

from radar.knowledge.stock_map import WATCHLIST


def _yahoo_symbol(ticker: str) -> str:
    return WATCHLIST[ticker].get("yahoo", f"{ticker}.TW")


def _fetch_yahoo_history(ticker: str, days: int = 90) -> tuple[str, list[dict[str, float | int | str]]]:
    symbol = _yahoo_symbol(ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AI-Stock-Radar/0.8"})
    with urllib.request.urlopen(request, timeout=2) as response:  # noqa: S310 - public market data endpoint
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise ValueError("Yahoo chart response has no result")

    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    rows: list[dict[str, float | int | str]] = []
    for ts, close, volume in zip(timestamps, closes, volumes):
        if close is None:
            continue
        day = date.fromtimestamp(ts).isoformat()
        rows.append({"date": day, "close": round(float(close), 2), "volume": int(volume or 0)})

    if len(rows) < 30:
        raise ValueError("Yahoo chart response does not contain enough rows")

    return "Yahoo 即時價格", rows[-days:]


def _fallback_history(ticker: str, days: int = 90) -> tuple[str, list[dict[str, float | int | str]]]:
    profile = WATCHLIST[ticker]
    base = float(profile.get("base_price", 100))
    seed = int(hashlib.sha256(ticker.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)

    drift_map = {
        "2330": 0.0018,
        "2382": 0.0012,
        "3231": 0.0009,
        "6669": 0.0010,
        "2449": 0.0006,
        "2454": 0.0005,
        "2308": 0.0008,
        "8299": 0.0002,
        "2603": -0.0002,
    }
    drift = drift_map.get(ticker, 0.0004)
    price = base * (0.94 + rng.random() * 0.08)
    rows: list[dict[str, float | int | str]] = []

    start = date.today() - timedelta(days=days * 1.45)
    day_index = 0
    current = start
    while len(rows) < days:
        if current.weekday() < 5:
            wave = math.sin(day_index / 5.0) * 0.006
            shock = rng.uniform(-0.018, 0.018)
            price = max(base * 0.55, price * (1 + drift + wave + shock))
            volume = int((1_000_000 + rng.random() * 8_000_000) * (1 + abs(shock) * 12))
            rows.append({"date": current.isoformat(), "close": round(price, 2), "volume": volume})
            day_index += 1
        current += timedelta(days=1)

    return "內建模擬價格", rows[-days:]


def load_price_history(ticker: str, days: int = 90) -> tuple[str, list[dict[str, float | int | str]]]:
    try:
        return _fetch_yahoo_history(ticker, days=days)
    except Exception:
        return _fallback_history(ticker, days=days)
