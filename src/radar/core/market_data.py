"""Market data provider with deterministic fallback."""

from __future__ import annotations

import math
import time
from datetime import date, timedelta

import requests

from radar.data.stock_master import StockInfo


FALLBACK_PRICES = {
    "2330": 1080.0,
    "2317": 210.0,
    "2382": 285.0,
    "3231": 118.0,
    "6669": 2350.0,
    "2327": 1015.0,
    "2313": 90.0,
    "3037": 170.0,
    "8046": 220.0,
    "2449": 110.0,
    "2454": 1300.0,
    "2379": 520.0,
    "2603": 185.0,
    "2308": 390.0,
    "8299": 520.0,
    "3324": 820.0,
    "3017": 780.0,
    "6257": 224.0,
    "3711": 175.0,
    "6213": 88.0,
    "6121": 360.0,
}


def _fallback_series(stock: StockInfo, days: int = 90) -> dict:
    base = FALLBACK_PRICES.get(stock.symbol, 100.0)
    rows = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=days - i)
        wave = math.sin(i / 7) * 0.035
        trend = (i - days / 2) / days * 0.08
        close = round(base * (1 + wave + trend), 2)
        open_ = round(close * (1 - 0.01 * math.sin(i / 3)), 2)
        high = round(max(open_, close) * 1.018, 2)
        low = round(min(open_, close) * 0.982, 2)
        volume = int(10000 + abs(math.sin(i / 5)) * 6000 + i * 20)
        rows.append({"date": d.isoformat(), "open": open_, "high": high, "low": low, "close": close, "volume": volume})
    return {"symbol": stock.symbol, "name": stock.name, "source": "fallback", "latest_date": rows[-1]["date"], "prices": rows}


def fetch_price_series(stock: StockInfo, days: int = 180, timeout: float = 4.0) -> dict:
    """Fetch daily prices from Yahoo chart API. Falls back safely."""
    now = int(time.time())
    start = now - days * 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock.yahoo_symbol}"
    params = {"period1": start, "period2": now, "interval": "1d", "events": "history"}
    try:
        response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result["indicators"]["quote"][0]
        rows = []
        for idx, ts in enumerate(timestamps):
            close = quote["close"][idx]
            if close is None:
                continue
            rows.append({
                "date": date.fromtimestamp(ts).isoformat(),
                "open": round(float(quote["open"][idx] or close), 2),
                "high": round(float(quote["high"][idx] or close), 2),
                "low": round(float(quote["low"][idx] or close), 2),
                "close": round(float(close), 2),
                "volume": int(quote["volume"][idx] or 0),
            })
        if len(rows) >= 30:
            return {"symbol": stock.symbol, "name": stock.name, "source": "Yahoo Finance", "latest_date": rows[-1]["date"], "prices": rows[-days:]}
    except Exception:
        pass
    return _fallback_series(stock, min(days, 120))
