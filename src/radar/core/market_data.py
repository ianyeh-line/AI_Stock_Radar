"""Market data provider with Yahoo Finance and deterministic fallback."""

from __future__ import annotations

import math
import time
from datetime import date, timedelta

import requests

from radar.data.stock_master import StockInfo
from radar.core.official_data import apply_official_snapshot, fetch_official_snapshot


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


def _safe_meta_price(meta: dict) -> float | None:
    for key in ("regularMarketPrice", "postMarketPrice", "preMarketPrice"):
        value = meta.get(key)
        try:
            price = float(value)
            if price > 0:
                return price
        except Exception:
            continue
    return None


def _safe_meta_time(meta: dict) -> int | None:
    for key in ("regularMarketTime", "postMarketTime", "preMarketTime"):
        value = meta.get(key)
        try:
            ts = int(value)
            if ts > 0:
                return ts
        except Exception:
            continue
    return None


def _merge_yahoo_latest_quote(rows: list[dict], meta: dict) -> tuple[list[dict], bool]:
    """Merge Yahoo chart meta latest quote into daily OHLC rows.

    Yahoo's daily OHLC rows are the primary historical series, but the chart
    meta can contain a fresher regularMarketPrice / regularMarketTime. v3.5.2
    uses this quote when it is same-day or newer, so the product follows the
    newest available Yahoo data instead of waiting for a daily candle refresh.
    """
    if not rows:
        return rows, False
    latest_price = _safe_meta_price(meta)
    latest_ts = _safe_meta_time(meta)
    if latest_price is None or latest_ts is None:
        return rows, False
    latest_date = date.fromtimestamp(latest_ts).isoformat()
    out = [dict(row) for row in rows]
    latest_volume = int(meta.get("regularMarketVolume") or meta.get("postMarketVolume") or out[-1].get("volume") or 0)
    open_ = float(meta.get("regularMarketOpen") or out[-1].get("open") or latest_price)
    high = float(meta.get("regularMarketDayHigh") or max(open_, latest_price, float(out[-1].get("high") or latest_price)))
    low = float(meta.get("regularMarketDayLow") or min(open_, latest_price, float(out[-1].get("low") or latest_price)))
    new_row = {
        "date": latest_date,
        "open": round(open_, 2),
        "high": round(max(high, latest_price), 2),
        "low": round(min(low, latest_price), 2),
        "close": round(latest_price, 2),
        "volume": latest_volume,
    }
    if latest_date == out[-1].get("date"):
        old_close = out[-1].get("close")
        out[-1].update(new_row)
        try:
            return out, abs(float(old_close) - latest_price) > 1e-9
        except Exception:
            return out, True
    if latest_date > str(out[-1].get("date")):
        out.append(new_row)
        return out, True
    return out, False


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
    rows, quote_merged = _merge_yahoo_latest_quote(rows, meta)
    yahoo_name = _clean_yahoo_name(meta.get("shortName") or meta.get("longName"), stock.symbol, stock.name)
    return {
        "symbol": stock.symbol,
        "name": yahoo_name,
        "market": market,
        "yahoo_symbol": yahoo_symbol,
        "source": "Yahoo Finance 最新報價" if quote_merged else "Yahoo Finance",
        "latest_date": rows[-1]["date"],
        "prices": rows[-days:],
        "data_quality": "yahoo_latest_quote" if quote_merged else "live_daily",
        "yahoo_quote_merged": quote_merged,
    }


def fetch_price_series(stock: StockInfo, days: int = 180, timeout: float = 4.0) -> dict:
    """Fetch daily prices with official latest snapshot confirmation.

    v3.4.0 Data Source Upgrade:
    - Yahoo Finance remains the historical OHLC source for indicators/charts.
    - TWSE / TPEx OpenAPI is queried for the latest official daily close.
    - When official data is available, the latest row is confirmed / corrected
      by TWSE / TPEx and data_quality becomes official_confirmed_daily.
    - When official data is unavailable, Yahoo/fallback still works but data
      trust will clearly flag the missing official confirmation.
    """
    yahoo_payload: dict | None = None
    for yahoo_symbol, market in _candidate_symbols(stock):
        try:
            payload = _fetch_yahoo_candidate(stock, yahoo_symbol, market, days, timeout)
            if payload:
                yahoo_payload = payload
                break
        except Exception:
            continue

    if yahoo_payload is None:
        yahoo_payload = _fallback_series(stock, min(days, 120))

    try:
        # Use the market discovered by Yahoo when possible. This helps dynamic
        # user-entered stocks that were initially assumed to be listed (.TW) but
        # actually trade on TPEx (.TWO).
        market = str(yahoo_payload.get("market") or stock.market or "TW")
        confirmed_stock = StockInfo(stock.symbol, str(yahoo_payload.get("name") or stock.name), market, stock.theme)
        snapshot = fetch_official_snapshot(confirmed_stock, timeout=timeout)
        return apply_official_snapshot(yahoo_payload, snapshot)
    except Exception:
        yahoo_payload.setdefault("official_confirmed", False)
        yahoo_payload.setdefault("official_snapshot", {"ok": False, "message": "官方資料抓取失敗"})
        return yahoo_payload
