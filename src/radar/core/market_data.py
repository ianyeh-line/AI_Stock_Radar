"""Market data provider with Yahoo Finance and deterministic fallback."""

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
    "4952": 56.7,
    "3324": 820.0,
    "3017": 780.0,
    "6257": 224.0,
    "3711": 175.0,
    "6213": 88.0,
    "6121": 360.0,
    "2408": 72.0,
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
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "market": stock.market,
        "yahoo_symbol": stock.yahoo_symbol,
        "source": "fallback",
        "latest_date": rows[-1]["date"],
        "prices": rows,
        "data_quality": "fallback",
    }


def _clean_yahoo_name(raw_name: str | None, symbol: str, fallback: str) -> str:
    if not raw_name:
        return fallback
    name = raw_name.strip()
    if not name or name.upper() in {f"{symbol}.TW", f"{symbol}.TWO", symbol}:
        return fallback
    # Yahoo Taiwan often returns names like "凌通科技股份有限公司". Keep it readable.
    name = name.replace("股份有限公司", "").replace("科技", "")
    return name[:16] if len(name) > 16 else name


def _candidate_symbols(stock: StockInfo) -> list[tuple[str, str]]:
    preferred = (stock.yahoo_symbol, stock.market)
    alt_market = "TWO" if stock.market == "TW" else "TW"
    alt_suffix = ".TWO" if alt_market == "TWO" else ".TW"
    candidates = [preferred, (f"{stock.symbol}{alt_suffix}", alt_market)]
    # Deduplicate while preserving order.
    seen = set()
    out = []
    for yahoo_symbol, market in candidates:
        if yahoo_symbol not in seen:
            seen.add(yahoo_symbol)
            out.append((yahoo_symbol, market))
    return out


def _fetch_yahoo_candidate(stock: StockInfo, yahoo_symbol: str, market: str, days: int, timeout: float) -> dict | None:
    now = int(time.time())
    start = now - days * 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    params = {"period1": start, "period2": now, "interval": "1d", "events": "history"}
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
    if len(rows) < 30:
        return None
    meta = result.get("meta", {}) or {}
    yahoo_name = _clean_yahoo_name(meta.get("shortName") or meta.get("longName"), stock.symbol, stock.name)
    return {
        "symbol": stock.symbol,
        "name": yahoo_name,
        "market": market,
        "yahoo_symbol": yahoo_symbol,
        "source": "Yahoo Finance",
        "latest_date": rows[-1]["date"],
        "prices": rows[-days:],
        "data_quality": "live_daily",
    }


def fetch_price_series(stock: StockInfo, days: int = 180, timeout: float = 4.0) -> dict:
    """Fetch daily prices from Yahoo chart API.

    v3.1.0 enhancement:
    - Unknown user-entered Taiwan stocks are not blocked by Stock Master.
    - The fetcher tries both .TW and .TWO and returns whichever has valid data.
    - If Yahoo returns a useful name, the payload carries that name so the UI and
      portfolio coach can display the stock better than 自訂個股.
    """
    for yahoo_symbol, market in _candidate_symbols(stock):
        try:
            payload = _fetch_yahoo_candidate(stock, yahoo_symbol, market, days, timeout)
            if payload:
                return payload
        except Exception:
            continue
    return _fallback_series(stock, min(days, 120))
