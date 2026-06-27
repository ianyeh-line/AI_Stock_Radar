"""Price data provider.

The provider first tries Yahoo Finance chart API. If the network is unavailable,
it falls back to deterministic sample data so the product remains executable.
"""

from __future__ import annotations

from datetime import date, timedelta
import json
import math
import random
import urllib.request

from radar.knowledge.stock_map import WATCHLIST


def _round(value: float) -> float:
    return round(float(value), 2)


def _fetch_yahoo_history(ticker: str) -> tuple[str, list[dict]]:
    symbol = WATCHLIST[ticker]["yahoo"]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=8mo&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AIStockRadar/0.9"})
    with urllib.request.urlopen(req, timeout=7) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    history = []
    for i, ts in enumerate(timestamps):
        close = quote.get("close", [None])[i]
        open_ = quote.get("open", [None])[i]
        high = quote.get("high", [None])[i]
        low = quote.get("low", [None])[i]
        volume = quote.get("volume", [0])[i] or 0
        if close is None or open_ is None or high is None or low is None:
            continue
        d = date.fromtimestamp(ts).isoformat()
        history.append({
            "date": d,
            "open": _round(open_),
            "high": _round(high),
            "low": _round(low),
            "close": _round(close),
            "volume": int(volume),
        })
    if len(history) < 80:
        raise RuntimeError("not enough history")
    return "Yahoo Finance Live", history[-160:]


def _base_price(ticker: str) -> float:
    base_map = {
        "2330": 900, "2454": 1200, "2308": 410, "2382": 280, "3231": 120,
        "6669": 1900, "2356": 55, "3017": 680, "3324": 720, "3661": 3600,
        "2449": 120, "8299": 520, "3711": 170, "3037": 175, "8046": 160,
        "5269": 1800, "2603": 180, "2609": 75, "2615": 95, "2605": 25,
        "2606": 55, "2612": 50, "3034": 560, "2379": 590, "2317": 200,
    }
    return float(base_map.get(ticker, 100))


def _sample_history(ticker: str, days: int = 160) -> tuple[str, list[dict]]:
    seed = int(ticker) if ticker.isdigit() else sum(ord(ch) for ch in ticker)
    rng = random.Random(seed)
    base = _base_price(ticker)
    today = date.today()
    history = []
    close = base * (0.88 + (seed % 17) / 100)
    slope = ((seed % 9) - 3) / 1200
    cycle = (seed % 11) / 10

    for i in range(days):
        d = today - timedelta(days=days - i)
        drift = slope + 0.0015 * math.sin(i / 11 + cycle)
        noise = rng.uniform(-0.012, 0.014)
        close = max(base * 0.45, close * (1 + drift + noise))
        open_ = close * (1 + rng.uniform(-0.008, 0.008))
        high = max(open_, close) * (1 + rng.uniform(0.002, 0.018))
        low = min(open_, close) * (1 - rng.uniform(0.002, 0.018))
        volume_base = 5000 + (seed % 20000)
        volume = int(volume_base * (0.75 + rng.random() * 0.7) * (1 + max(0, drift) * 20))
        history.append({
            "date": d.isoformat(),
            "open": _round(open_),
            "high": _round(high),
            "low": _round(low),
            "close": _round(close),
            "volume": volume,
        })
    return "內建技術樣本資料", history


def get_price_history(ticker: str) -> tuple[str, list[dict]]:
    try:
        return _fetch_yahoo_history(ticker)
    except Exception:
        return _sample_history(ticker)
