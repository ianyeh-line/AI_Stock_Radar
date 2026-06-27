"""Real price datasource using Yahoo Finance Chart API with symbol auto-resolution.

The product is not a tick-by-tick terminal. It fetches the freshest available
Yahoo Finance daily chart payload at execution time. Taiwan tickers sometimes
use .TW or .TWO inconsistently across data providers, so v2.2.1 tries both
suffixes and chooses the freshest valid series. This directly prevents stale
MACD / latest-price issues such as a wrong suffix returning old data.
"""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from dataclasses import dataclass

from radar.models.domain import PriceBar, StockMeta

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_value}&interval=1d&events=history&includeAdjustedClose=true"


@dataclass(frozen=True)
class PriceFetchResult:
    bars: list[PriceBar]
    yahoo_symbol: str
    source: str


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


def _fetch_yahoo_prices_single(yahoo_symbol: str, range_value: str = "1y") -> list[PriceBar]:
    encoded = urllib.parse.quote(yahoo_symbol, safe="")
    url = YAHOO_CHART_URL.format(symbol=encoded, range_value=range_value)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=2) as response:
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


def _candidate_yahoo_symbols(stock: StockMeta) -> list[str]:
    """Return candidate Yahoo symbols, correcting common .TW/.TWO mistakes."""
    base = stock.symbol
    candidates = [stock.yahoo_symbol]
    if not stock.yahoo_symbol.endswith(".TW"):
        candidates.append(f"{base}.TW")
    if not stock.yahoo_symbol.endswith(".TWO"):
        candidates.append(f"{base}.TWO")
    # Preserve order, remove duplicates.
    result: list[str] = []
    for item in candidates:
        if item and item not in result:
            result.append(item)
    return result


def fetch_yahoo_prices(yahoo_symbol: str, range_value: str = "1y") -> list[PriceBar]:
    """Backward-compatible single-symbol fetch."""
    return _fetch_yahoo_prices_single(yahoo_symbol, range_value)


def fetch_best_yahoo_prices(stock: StockMeta, range_value: str = "1y") -> PriceFetchResult:
    """Try configured Yahoo symbol and alternative Taiwan suffixes.

    Selection policy:
    1. Latest available date wins.
    2. If dates tie, more bars wins.
    3. If still tied, the configured symbol keeps priority.
    """
    candidates: list[tuple[str, list[PriceBar], int]] = []
    for priority, symbol in enumerate(_candidate_yahoo_symbols(stock)):
        try:
            bars = _fetch_yahoo_prices_single(symbol, range_value)
            candidates.append((symbol, bars, priority))
        except Exception:
            continue
    if not candidates:
        raise RuntimeError(f"No valid Yahoo price series for {stock.symbol}")

    def _sort_key(item: tuple[str, list[PriceBar], int]) -> tuple[str, int, int]:
        symbol, bars, priority = item
        return (bars[-1].date, len(bars), -priority)

    symbol, bars, _ = max(candidates, key=_sort_key)
    if symbol != stock.yahoo_symbol:
        source = f"Yahoo Finance 最新可得報價 ({symbol}，自動修正來源代碼)"
    else:
        source = f"Yahoo Finance 最新可得報價 ({symbol})"
    return PriceFetchResult(bars=bars, yahoo_symbol=symbol, source=source)


def generate_fallback_prices(stock: StockMeta, days: int = 260) -> list[PriceBar]:
    seed = sum(ord(char) for char in stock.symbol + stock.name)
    rng = random.Random(seed)
    end = datetime.today().date()
    dates: list[datetime.date] = []
    cursor = end
    while len(dates) < days:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= timedelta(days=1)
    dates.reverse()

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



PRICE_CACHE_DIR = Path("data/cache/prices")
CACHE_TTL_HOURS = 18


def _cache_path(stock: StockMeta) -> Path:
    return PRICE_CACHE_DIR / f"{stock.symbol}.json"


def _bars_to_dicts(bars: list[PriceBar]) -> list[dict[str, Any]]:
    return [bar.as_dict() for bar in bars]


def _bars_from_dicts(rows: list[dict[str, Any]]) -> list[PriceBar]:
    result: list[PriceBar] = []
    for row in rows:
        try:
            result.append(
                PriceBar(
                    date=str(row.get("date", "")),
                    open=float(row.get("open", 0) or 0),
                    high=float(row.get("high", 0) or 0),
                    low=float(row.get("low", 0) or 0),
                    close=float(row.get("close", 0) or 0),
                    volume=int(row.get("volume", 0) or 0),
                )
            )
        except Exception:
            continue
    return [bar for bar in result if bar.date and bar.close > 0]


def _load_price_cache(stock: StockMeta, allow_stale: bool = False) -> tuple[list[PriceBar], str] | None:
    path = _cache_path(stock)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        generated_at = float(payload.get("generated_at_epoch", 0) or 0)
        age_hours = (time.time() - generated_at) / 3600 if generated_at else 9999
        if not allow_stale and age_hours > CACHE_TTL_HOURS:
            return None
        bars = _bars_from_dicts(payload.get("bars", []))
        if len(bars) < 40:
            return None
        source = str(payload.get("source") or "Yahoo Finance 快取日線")
        suffix = "今日快取" if age_hours <= CACHE_TTL_HOURS else "過期快取"
        return bars, f"{source}（{suffix}）"
    except Exception:
        return None


def _save_price_cache(stock: StockMeta, bars: list[PriceBar], source: str) -> None:
    try:
        PRICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "symbol": stock.symbol,
            "name": stock.name,
            "source": source,
            "generated_at_epoch": time.time(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "latest_date": bars[-1].date if bars else "",
            "bars": _bars_to_dicts(bars),
        }
        _cache_path(stock).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        # Cache must never break the product.
        return

def load_price_bars(stock: StockMeta, days: int = 260, use_cache: bool = True) -> tuple[list[PriceBar], str]:
    """Load price bars with cache-first freshness protection.

    Taiwan daily prices update once per trading day. A same-day cache avoids
    forcing the Streamlit refresh button to download 100+ Yahoo series every
    time, while still keeping the latest available daily bar from the last
    successful fetch. If the network is slow or unavailable, a stale cache is
    safer than a synthetic fallback and is explicitly labelled.
    """
    if use_cache:
        cached = _load_price_cache(stock, allow_stale=False)
        if cached:
            bars, source = cached
            return bars[-days:], source
    try:
        result = fetch_best_yahoo_prices(stock, "1y")
        _save_price_cache(stock, result.bars, result.source)
        return result.bars[-days:], result.source
    except Exception:
        cached = _load_price_cache(stock, allow_stale=True)
        if cached:
            bars, source = cached
            return bars[-days:], source
        time.sleep(0.02)
        return generate_fallback_prices(stock, days), "Fallback Price Model"
