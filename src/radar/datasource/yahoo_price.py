"""Real price datasource using Yahoo Finance Chart API with latest quote support.

The product is not a tick-by-tick terminal. The goal is to use the freshest
available Yahoo Finance chart payload at execution time. For daily technical
analysis we fetch 1Y daily bars, then patch the latest bar with Yahoo chart
metadata regularMarketPrice when available. This keeps MACD list, decision
cards, portfolio analysis and charts using one centralized price payload.
"""

from __future__ import annotations

import json
import math
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from radar.models.domain import PriceBar, StockMeta

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_value}&interval=1d&events=history&includeAdjustedClose=true"


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _quote_date(meta: dict) -> str | None:
    ts = meta.get("regularMarketTime") or meta.get("firstTradeDate")
    try:
        if ts:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except Exception:
        return None
    return None


def _patch_latest_bar_with_quote(bars: list[PriceBar], meta: dict) -> list[PriceBar]:
    """Patch final daily bar with Yahoo latest quote metadata when available."""
    if not bars:
        return bars
    latest_price = _to_float(meta.get("regularMarketPrice"), 0.0)
    previous_close = _to_float(meta.get("chartPreviousClose") or meta.get("previousClose"), 0.0)
    quote_dt = _quote_date(meta) or bars[-1].date
    if latest_price <= 0:
        return bars

    # If the chart already contains today's daily row, update it. If it only has
    # the previous trading day but Yahoo exposes a newer quote timestamp, append
    # a synthetic latest bar so all downstream sections use the same latest price.
    last = bars[-1]
    if quote_dt == last.date:
        patched = PriceBar(
            date=last.date,
            open=round(last.open or previous_close or latest_price, 4),
            high=round(max(last.high, latest_price), 4),
            low=round(min(last.low, latest_price), 4),
            close=round(latest_price, 4),
            volume=last.volume,
        )
        return bars[:-1] + [patched]

    if quote_dt > last.date and previous_close > 0:
        synthetic_volume = last.volume
        patched = PriceBar(
            date=quote_dt,
            open=round(previous_close, 4),
            high=round(max(previous_close, latest_price), 4),
            low=round(min(previous_close, latest_price), 4),
            close=round(latest_price, 4),
            volume=synthetic_volume,
        )
        return bars + [patched]

    return bars


def fetch_yahoo_prices(yahoo_symbol: str, range_value: str = "1y") -> list[PriceBar]:
    encoded = urllib.parse.quote(yahoo_symbol, safe="")
    url = YAHOO_CHART_URL.format(symbol=encoded, range_value=range_value)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError(f"No Yahoo chart result for {yahoo_symbol}")

    data = result[0]
    meta = data.get("meta") or {}
    timestamps = data.get("timestamp") or []
    quote = (data.get("indicators", {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: list[PriceBar] = []
    for idx, ts in enumerate(timestamps):
        close = _to_float(closes[idx] if idx < len(closes) else None, default=0.0)
        if close <= 0:
            continue
        dt = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
        open_value = _to_float(opens[idx] if idx < len(opens) else close, close)
        high_value = _to_float(highs[idx] if idx < len(highs) else close, close)
        low_value = _to_float(lows[idx] if idx < len(lows) else close, close)
        volume_value = _to_int(volumes[idx] if idx < len(volumes) else 0, 0)
        bars.append(
            PriceBar(
                date=dt,
                open=round(open_value, 4),
                high=round(high_value, 4),
                low=round(low_value, 4),
                close=round(close, 4),
                volume=volume_value,
            )
        )
    bars = _patch_latest_bar_with_quote(bars, meta)
    if len(bars) < 40:
        raise RuntimeError(f"Insufficient Yahoo bars for {yahoo_symbol}")
    return bars


def generate_fallback_prices(stock: StockMeta, days: int = 260) -> list[PriceBar]:
    seed = sum(ord(char) for char in stock.symbol + stock.name)
    rng = random.Random(seed)
    end = datetime.today().date()
    dates: list[datetime.date] = []
    cursor = end - timedelta(days=days * 2)
    while len(dates) < days:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor += timedelta(days=1)

    base = 40 + seed % 420
    long_trend = (stock.base_priority - 5) * 0.12
    close = base
    bars: list[PriceBar] = []
    for idx, dt in enumerate(dates):
        cycle = math.sin(idx / 14.0) * (1.2 + (seed % 7) * 0.2)
        drift = long_trend + math.sin(idx / 55.0) * 0.08
        shock = rng.gauss(0, 1.5)
        close = max(8.0, close * (1 + (drift + cycle * 0.08 + shock) / 100))
        open_value = close * (1 + rng.gauss(0, 0.006))
        high = max(open_value, close) * (1 + rng.random() * 0.018)
        low = min(open_value, close) * (1 - rng.random() * 0.018)
        volume = int((2500 + rng.random() * 18000 + stock.base_priority * 600) * 1000)
        bars.append(
            PriceBar(
                date=dt.strftime("%Y-%m-%d"),
                open=round(open_value, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
            )
        )
    return bars


def load_price_bars(stock: StockMeta, days: int = 260) -> tuple[list[PriceBar], str]:
    try:
        bars = fetch_yahoo_prices(stock.yahoo_symbol, "1y")
        return bars[-days:], "Yahoo Finance 最新可得報價"
    except Exception:
        time.sleep(0.05)
        return generate_fallback_prices(stock, days), "Fallback Price Model"
