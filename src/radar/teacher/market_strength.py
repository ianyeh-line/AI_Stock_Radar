"""Full-market strong momentum radar with transparent connector diagnostics.

v3.8.2 fixes the v3.8.0 regression where the UI claimed a full-market scan
but no market rows were parsed in some environments.

Design rule for this module:
- Do not claim a full-market scan unless at least one broad market source was
  actually fetched and parsed.
- Always expose endpoint-level diagnostics so the user can see exactly which
  connector succeeded, failed, or parsed zero rows.
- Prefer official TWSE / TPEx snapshots. If they are unavailable or incomplete,
  use Yahoo quote data built from the official stock master as a transparent
  fallback, not as a hidden success.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from radar.data.stock_master import STOCKS, StockInfo, register_custom_stock
from radar.core.market_data import fetch_price_series

TWSE_STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TWSE_PRICE_CHANGE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT84U"
TWSE_VOLUME_TOP20_URL = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX20"
TWSE_STOCK_MASTER_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

TPEX_DAILY_CLOSE_URLS = [
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
]
TPEX_STRENGTH_URLS = [
    "https://www.tpex.org.tw/openapi/v1/tpex_active_advanced",
    "https://www.tpex.org.tw/openapi/v1/tpex_active_dollar_volume",
    "https://www.tpex.org.tw/openapi/v1/tpex_volume_rank",
    "https://www.tpex.org.tw/openapi/v1/tpex_amount_rank",
]
TPEX_STOCK_MASTER_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_QUOTE_URL_BACKUP = "https://query2.finance.yahoo.com/v7/finance/quote"


@dataclass(frozen=True)
class MarketRow:
    symbol: str
    name: str
    market: str
    source: str
    close: float
    change: float
    change_pct: float
    open: float | None
    high: float | None
    low: float | None
    volume: int
    value: float
    date: str = ""

    @property
    def label(self) -> str:
        return f"{self.symbol} {self.name}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "source": self.source,
            "close": self.close,
            "change": self.change,
            "change_pct": self.change_pct,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "value": self.value,
            "date": self.date,
            "label": self.label,
        }


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    text = (
        text.replace(",", "")
        .replace("%", "")
        .replace("％", "")
        .replace("+", "")
        .replace("▲", "")
        .replace("▼", "-")
        .replace("−", "-")
        .replace("－", "-")
        .replace("–", "-")
    )
    if text in {"", "--", "-", "X", "除權息", "N/A", "nan", "None"}:
        return default
    try:
        return float(text)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(_safe_float(value, float(default))))
    except Exception:
        return default


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().lower().replace(" ", "").replace("_", "")


def _get_any(row: dict[str, Any], *keys: str) -> Any:
    """Get a field by exact key, normalized key, or fuzzy keyword match."""
    for key in keys:
        if key in row:
            return row[key]
    normalized = {_normalize_key(k): v for k, v in row.items()}
    for key in keys:
        nk = _normalize_key(key)
        if nk in normalized:
            return normalized[nk]
    # Fuzzy fallback: useful for official APIs with slightly changing Chinese labels.
    for key in keys:
        nk = _normalize_key(key)
        for rk, value in normalized.items():
            if nk and (nk in rk or rk in nk):
                return value
    return None


def _normalize_symbol(value: Any) -> str:
    text = str(value or "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    # ETF and stocks are 4 digits in our current scope. Keep first 4 to avoid
    # parsing securities names like "2330 台積電" into longer strings.
    return digits[:4] if len(digits) >= 4 else ""


def _parse_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace(".", "/").replace("-", "/")
    parts = [p for p in text.split("/") if p]
    try:
        if len(parts) >= 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 1911:
                y += 1911
            return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        return ""
    return ""


def _calc_change_pct(close: float, change: float) -> float:
    prev = close - change
    if close <= 0 or prev <= 0:
        return 0.0
    return round(change / prev * 100, 2)


def _parse_market_row(row: dict[str, Any], market: str, source: str) -> MarketRow | None:
    symbol = _normalize_symbol(_get_any(row, "Code", "SecuritiesCompanyCode", "證券代號", "股票代號", "有價證券代號", "代號", "公司代號"))
    if not symbol or not symbol.isdigit():
        return None

    name = str(_get_any(row, "Name", "CompanyName", "證券名稱", "股票名稱", "公司名稱", "有價證券名稱", "名稱") or "").strip()
    if not name:
        stock = STOCKS.get(symbol)
        name = stock.name if stock else f"待識別{symbol}"

    close = _safe_float(_get_any(row, "ClosingPrice", "Close", "close", "收盤價", "收盤", "最新價", "最後成交價", "成交價"))
    if close <= 0:
        return None

    change = _safe_float(_get_any(row, "Change", "ChangePrice", "漲跌價差", "漲跌", "漲跌點數", "漲跌(+/-)", "漲跌元"))
    change_pct = _safe_float(_get_any(row, "ChangePercent", "ChangePercentage", "ChangePct", "漲跌幅", "漲跌幅(%)", "漲幅", "漲幅(%)"))
    if change_pct == 0 and change != 0:
        change_pct = _calc_change_pct(close, change)

    open_ = _safe_float(_get_any(row, "OpeningPrice", "Open", "open", "開盤價", "開盤"), 0.0) or None
    high = _safe_float(_get_any(row, "HighestPrice", "High", "high", "最高價", "最高"), 0.0) or None
    low = _safe_float(_get_any(row, "LowestPrice", "Low", "low", "最低價", "最低"), 0.0) or None
    volume = _safe_int(_get_any(row, "TradeVolume", "TradingShares", "Volume", "volume", "成交股數", "成交量", "成交張數"))
    value = _safe_float(_get_any(row, "TradeValue", "TransactionAmount", "Turnover", "成交金額", "成交值", "成交金額(元)"))
    if value <= 0 and close > 0 and volume > 0:
        value = close * volume
    row_date = _parse_date(_get_any(row, "Date", "日期", "資料日期", "交易日期"))

    return MarketRow(
        symbol=symbol,
        name=name,
        market=market,
        source=source,
        close=round(close, 2),
        change=round(change, 2),
        change_pct=round(change_pct, 2),
        open=open_,
        high=high,
        low=low,
        volume=volume,
        value=round(value, 0),
        date=row_date,
    )


def _fetch_json(url: str, timeout: float) -> list[dict[str, Any]]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("data", "result", "items", "rows"):
            rows = data.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _attempt_endpoint(url: str, market: str, source: str, timeout: float) -> tuple[list[MarketRow], dict[str, Any]]:
    attempt: dict[str, Any] = {
        "source": source,
        "url": url,
        "status": "pending",
        "raw_rows": 0,
        "parsed_rows": 0,
        "sample_keys": [],
        "error": "",
    }
    try:
        raw_rows = _fetch_json(url, timeout)
        attempt["raw_rows"] = len(raw_rows)
        if raw_rows:
            attempt["sample_keys"] = list(raw_rows[0].keys())[:18]
        rows = []
        for raw in raw_rows:
            parsed = _parse_market_row(raw, market, source)
            if parsed:
                rows.append(parsed)
        attempt["parsed_rows"] = len(rows)
        attempt["status"] = "ok" if rows else "parsed_zero"
        if raw_rows and not rows:
            attempt["error"] = "API 有回傳資料，但欄位未解析成功；請看 sample_keys。"
        return rows, attempt
    except Exception as exc:
        attempt["status"] = "error"
        attempt["error"] = str(exc)[:500]
        return [], attempt


def _fetch_stock_master(timeout: float) -> tuple[list[StockInfo], list[dict[str, Any]]]:
    """Fetch official stock master for Yahoo quote fallback.

    This is not used to fabricate full-market strength. It is used only when
    official daily snapshot endpoints are unavailable, so the system can still
    scan a broader Taiwan universe via Yahoo quotes and clearly label it.
    """
    stocks: dict[str, StockInfo] = {s.symbol: s for s in STOCKS.values()}
    attempts: list[dict[str, Any]] = []
    for market, url, source in [
        ("TW", TWSE_STOCK_MASTER_URL, "TWSE Stock Master"),
        ("TWO", TPEX_STOCK_MASTER_URL, "TPEx Stock Master"),
    ]:
        attempt = {"source": source, "url": url, "status": "pending", "raw_rows": 0, "parsed_rows": 0, "sample_keys": [], "error": ""}
        try:
            raw_rows = _fetch_json(url, timeout)
            attempt["raw_rows"] = len(raw_rows)
            if raw_rows:
                attempt["sample_keys"] = list(raw_rows[0].keys())[:18]
            parsed_count = 0
            for raw in raw_rows:
                symbol = _normalize_symbol(_get_any(raw, "公司代號", "Code", "SecuritiesCompanyCode", "證券代號", "股票代號"))
                name = str(_get_any(raw, "公司名稱", "Name", "CompanyName", "證券名稱", "股票名稱", "名稱") or "").strip()
                if symbol and name:
                    stocks.setdefault(symbol, StockInfo(symbol, name, market, "全市場"))
                    parsed_count += 1
            attempt["parsed_rows"] = parsed_count
            attempt["status"] = "ok" if parsed_count else "parsed_zero"
            attempts.append(attempt)
        except Exception as exc:
            attempt["status"] = "error"
            attempt["error"] = str(exc)[:500]
            attempts.append(attempt)
    return list(stocks.values()), attempts


def _chunked(items: list[StockInfo], size: int) -> list[list[StockInfo]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _market_time_to_date(ts: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().date().isoformat()
    except Exception:
        return ""


def _row_from_yahoo_quote(quote: dict[str, Any], stock: StockInfo) -> MarketRow | None:
    close = _safe_float(quote.get("regularMarketPrice") or quote.get("postMarketPrice") or quote.get("preMarketPrice"))
    if close <= 0:
        return None
    change = _safe_float(quote.get("regularMarketChange"))
    change_pct = _safe_float(quote.get("regularMarketChangePercent"))
    name = stock.name
    short_name = str(quote.get("shortName") or quote.get("longName") or "").strip()
    if (not name or name.startswith("待識別")) and short_name:
        name = short_name
    volume = _safe_int(quote.get("regularMarketVolume"))
    value = round(close * volume, 0) if volume else 0.0
    return MarketRow(
        symbol=stock.symbol,
        name=name,
        market=stock.market,
        source="Yahoo Finance Quote",
        close=round(close, 2),
        change=round(change, 2),
        change_pct=round(change_pct, 2),
        open=_safe_float(quote.get("regularMarketOpen"), 0.0) or None,
        high=_safe_float(quote.get("regularMarketDayHigh"), 0.0) or None,
        low=_safe_float(quote.get("regularMarketDayLow"), 0.0) or None,
        volume=volume,
        value=value,
        date=_market_time_to_date(quote.get("regularMarketTime")),
    )


def _row_from_price_payload(payload: dict[str, Any], stock: StockInfo, source: str = "Yahoo Finance Chart") -> MarketRow | None:
    """Convert an existing OHLC payload into a market strength row.

    This is the v3.8.2 safety net: when broad official ranking endpoints or
    Yahoo quote endpoint are unavailable, use the same latest price payload that
    powers decision cards and stock charts. This does not pretend to be a full
    market scan; coverage.mode tells the user exactly which fallback was used.
    """
    prices = payload.get("prices") or []
    if not prices:
        return None
    last = prices[-1]
    prev = prices[-2] if len(prices) >= 2 else {}
    close = _safe_float(last.get("close"))
    if close <= 0:
        return None
    prev_close = _safe_float(prev.get("close"), close) or close
    change = round(close - prev_close, 2)
    change_pct = round((change / prev_close * 100), 2) if prev_close > 0 else 0.0
    volume = _safe_int(last.get("volume"))
    name = str(payload.get("name") or stock.name or "").strip() or f"待識別{stock.symbol}"
    market = str(payload.get("market") or stock.market or "TW")
    return MarketRow(
        symbol=stock.symbol,
        name=name,
        market=market,
        source=source if source else str(payload.get("source") or "Yahoo Finance Chart"),
        close=round(close, 2),
        change=change,
        change_pct=change_pct,
        open=_safe_float(last.get("open"), 0.0) or None,
        high=_safe_float(last.get("high"), 0.0) or None,
        low=_safe_float(last.get("low"), 0.0) or None,
        volume=volume,
        value=round(close * volume, 0) if volume else 0.0,
        date=str(last.get("date") or payload.get("latest_date") or ""),
    )


def _rows_from_decision_cards(cards: list[dict[str, Any]]) -> list[MarketRow]:
    rows: list[MarketRow] = []
    for card in cards:
        stock = StockInfo(str(card.get("symbol") or ""), str(card.get("name") or ""), str(card.get("market") or "TW"), "決策股票池")
        payload = {
            "prices": card.get("prices") or [],
            "name": card.get("name"),
            "market": card.get("market") or "TW",
            "source": card.get("price_source") or "Decision Card Price Payload",
            "latest_date": card.get("latest_date"),
        }
        row = _row_from_price_payload(payload, stock, source="Decision Card Price Payload")
        if row:
            rows.append(row)
    return rows


def _fetch_yahoo_chart_rows(stocks: list[StockInfo], timeout: float = 3.0, max_symbols: int = 180) -> tuple[list[MarketRow], list[dict[str, Any]]]:
    """Fetch broad Yahoo chart rows as a transparent fallback.

    It is intentionally summarized as one diagnostic row to avoid flooding the
    UI with hundreds of per-symbol attempts.
    """
    selected = stocks[:max_symbols]
    rows: list[MarketRow] = []
    errors: list[str] = []
    attempt: dict[str, Any] = {
        "source": "Yahoo Chart Broad Scan",
        "url": "query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        "status": "pending",
        "raw_rows": len(selected),
        "parsed_rows": 0,
        "sample_keys": ["date", "open", "high", "low", "close", "volume"],
        "error": "",
    }

    def load(stock: StockInfo) -> MarketRow | None:
        payload = fetch_price_series(stock, days=90, timeout=timeout)
        if str(payload.get("data_quality")) == "fallback":
            return None
        return _row_from_price_payload(payload, stock, source=str(payload.get("source") or "Yahoo Finance Chart"))

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_map = {executor.submit(load, stock): stock for stock in selected}
            for future in as_completed(future_map):
                try:
                    row = future.result()
                    if row:
                        rows.append(row)
                except Exception as exc:
                    if len(errors) < 5:
                        stock = future_map.get(future)
                        errors.append(f"{getattr(stock, 'symbol', '')}: {str(exc)[:120]}")
        attempt["parsed_rows"] = len(rows)
        attempt["status"] = "ok" if rows else "parsed_zero"
        if not rows:
            attempt["error"] = "Yahoo Chart Broad Scan 沒有取得可用資料。" + (" / " + "；".join(errors) if errors else "")
        elif errors:
            attempt["error"] = "部分個股抓取失敗：" + "；".join(errors)
    except Exception as exc:
        attempt["status"] = "error"
        attempt["error"] = str(exc)[:500]
    return rows, [attempt]


def _fetch_yahoo_quotes(stocks: list[StockInfo], timeout: float = 8.0, max_symbols: int = 1400) -> tuple[list[MarketRow], list[dict[str, Any]]]:
    """Fetch broad Yahoo quotes in chunks.

    Yahoo is used as a freshness fallback and a wider quote source. If this
    fails, diagnostics tell the user exactly why the strong momentum radar is
    empty instead of claiming success.
    """
    selected = stocks[:max_symbols]
    out: list[MarketRow] = []
    attempts: list[dict[str, Any]] = []
    stock_by_yahoo = {s.yahoo_symbol: s for s in selected}
    for chunk in _chunked(selected, 60):
        symbols = ",".join(s.yahoo_symbol for s in chunk)
        success = False
        last_error = ""
        for base_url in (YAHOO_QUOTE_URL, YAHOO_QUOTE_URL_BACKUP):
            attempt = {"source": "Yahoo Quote", "url": base_url, "status": "pending", "raw_rows": 0, "parsed_rows": 0, "sample_keys": [], "error": ""}
            try:
                response = requests.get(base_url, params={"symbols": symbols}, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                data = response.json()
                quotes = data.get("quoteResponse", {}).get("result", []) if isinstance(data, dict) else []
                attempt["raw_rows"] = len(quotes)
                if quotes:
                    attempt["sample_keys"] = list(quotes[0].keys())[:18]
                parsed_count = 0
                for quote in quotes:
                    stock = stock_by_yahoo.get(str(quote.get("symbol") or ""))
                    if not stock:
                        continue
                    parsed = _row_from_yahoo_quote(quote, stock)
                    if parsed:
                        out.append(parsed)
                        parsed_count += 1
                attempt["parsed_rows"] = parsed_count
                attempt["status"] = "ok" if parsed_count else "parsed_zero"
                attempts.append(attempt)
                success = True
                break
            except Exception as exc:
                last_error = str(exc)[:500]
                attempt["status"] = "error"
                attempt["error"] = last_error
                attempts.append(attempt)
        if not success and last_error:
            # Continue to next chunk; one chunk failing should not kill the whole radar.
            continue
    return out, attempts


def _dedupe_rows(rows: list[MarketRow]) -> list[MarketRow]:
    by_symbol: dict[str, MarketRow] = {}
    for row in rows:
        current = by_symbol.get(row.symbol)
        if current is None:
            by_symbol[row.symbol] = row
            continue
        # Prefer newer date. If equal or missing, prefer rows with real gain/volume/value.
        cur_date = current.date or ""
        row_date = row.date or ""
        if row_date > cur_date:
            by_symbol[row.symbol] = row
        elif row_date == cur_date:
            current_score = (abs(current.change_pct) > 0, current.value, current.volume)
            row_score = (abs(row.change_pct) > 0, row.value, row.volume)
            if row_score > current_score:
                by_symbol[row.symbol] = row
    return list(by_symbol.values())


def fetch_market_snapshot(timeout: float = 7.0) -> dict[str, Any]:
    """Fetch a broad market snapshot with transparent diagnostics."""
    all_rows: list[MarketRow] = []
    attempts: list[dict[str, Any]] = []

    official_endpoints = [
        (TWSE_STOCK_DAY_ALL_URL, "TW", "TWSE STOCK_DAY_ALL"),
        (TWSE_PRICE_CHANGE_URL, "TW", "TWSE TWT84U"),
        (TWSE_VOLUME_TOP20_URL, "TW", "TWSE MI_INDEX20"),
    ]
    official_endpoints.extend((url, "TWO", "TPEx Daily Close") for url in TPEX_DAILY_CLOSE_URLS)
    official_endpoints.extend((url, "TWO", "TPEx Strength Rank") for url in TPEX_STRENGTH_URLS)

    for url, market, source in official_endpoints:
        rows, attempt = _attempt_endpoint(url, market, source, timeout)
        all_rows.extend(rows)
        attempts.append(attempt)

    official_rows = _dedupe_rows(all_rows)

    stocks, master_attempts = _fetch_stock_master(timeout)
    attempts.extend(master_attempts)
    yahoo_rows: list[MarketRow] = []
    yahoo_attempts: list[dict[str, Any]] = []
    yahoo_chart_rows: list[MarketRow] = []
    yahoo_chart_attempts: list[dict[str, Any]] = []

    # If official rows are too few, fetch Yahoo broad quotes. This is still a
    # broad-market data attempt, not a fabricated result.
    if len(official_rows) < 500:
        yahoo_rows, yahoo_attempts = _fetch_yahoo_quotes(stocks, timeout=timeout)
        attempts.extend(yahoo_attempts[:25])

    rows = _dedupe_rows(official_rows + yahoo_rows)

    # v3.8.2: Yahoo quote sometimes returns zero rows on Streamlit Cloud while
    # the chart endpoint works for individual stocks. In that case, run a
    # transparent broad Yahoo chart scan over the stock master so 強勢股雷達 has
    # real market candidates instead of an empty page.
    if len(rows) < 40:
        yahoo_chart_rows, yahoo_chart_attempts = _fetch_yahoo_chart_rows(stocks, timeout=min(timeout, 3.0))
        attempts.extend(yahoo_chart_attempts)
        rows = _dedupe_rows(rows + yahoo_chart_rows)

    sources = sorted({r.source for r in rows})
    if len(official_rows) >= 500:
        mode = "official_full_market"
        message = "已取得官方全市場快照。"
    elif yahoo_rows:
        mode = "official_plus_yahoo_quote"
        message = "官方全市場快照不足，已補用官方股票主檔 + Yahoo Quote 做較廣市場掃描。"
    elif yahoo_chart_rows:
        mode = "yahoo_chart_broad_scan"
        message = "官方快照與 Yahoo Quote 不足，已使用 Yahoo 日線/最新報價對股票主檔進行較廣市場掃描。"
    elif rows:
        mode = "partial_market_scan"
        message = "取得部分市場資料，強勢股雷達以可解析資料產生候選。"
    else:
        mode = "no_market_data"
        message = "未取得 TWSE / TPEx / Yahoo 可解析市場資料，強勢股雷達不產生假資料。"

    return {
        "rows": rows,
        "total": len(rows),
        "official_rows": len(official_rows),
        "yahoo_rows": len(yahoo_rows),
        "yahoo_chart_rows": len(yahoo_chart_rows),
        "errors": [a for a in attempts if a.get("status") == "error"][:12],
        "endpoint_attempts": attempts,
        "sources": sources,
        "mode": mode,
        "message": message,
    }


def _stock_from_market_row(row: MarketRow) -> StockInfo:
    if row.symbol in STOCKS:
        stock = STOCKS[row.symbol]
        if stock.market == row.market:
            return stock
        return StockInfo(stock.symbol, stock.name, row.market, stock.theme)
    return register_custom_stock(StockInfo(row.symbol, row.name, row.market, "全市場強勢"))


def _recent_high(prices: list[dict], days: int = 20) -> float:
    if not prices:
        return 0.0
    recent = prices[-days:] if len(prices) >= days else prices
    highs = [_safe_float(row.get("high") or row.get("close")) for row in recent]
    return max(highs) if highs else 0.0


def _opening_gap_pct(row: MarketRow) -> float:
    if row.open is None or row.change == 0:
        return 0.0
    prev_close = row.close - row.change
    if prev_close <= 0:
        return 0.0
    return round((row.open - prev_close) / prev_close * 100, 2)


def _rank_rows(rows: list[MarketRow]) -> dict[str, list[dict]]:
    gainers = sorted([r for r in rows if r.change_pct > 0], key=lambda r: (-r.change_pct, -r.value))[:30]
    volume = sorted([r for r in rows if r.volume > 0], key=lambda r: (-r.volume, -r.change_pct))[:30]
    value = sorted([r for r in rows if r.value > 0], key=lambda r: (-r.value, -r.change_pct))[:30]
    limit_like = sorted([r for r in rows if r.change_pct >= 8.5], key=lambda r: (-r.change_pct, -r.value))[:30]
    return {
        "top_gainers": [r.as_dict() for r in gainers],
        "top_volume": [r.as_dict() for r in volume],
        "top_value": [r.as_dict() for r in value],
        "limit_like": [r.as_dict() for r in limit_like],
    }


def _candidate_market_rows(rows: list[MarketRow]) -> list[MarketRow]:
    ranked = _rank_rows(rows)
    wanted: list[str] = []
    for key, take in (("limit_like", 25), ("top_gainers", 40), ("top_value", 30), ("top_volume", 20)):
        wanted.extend([r["symbol"] for r in ranked.get(key, [])[:take]])
    seen = set()
    out: list[MarketRow] = []
    row_map = {r.symbol: r for r in rows}
    for symbol in wanted:
        if symbol in row_map and symbol not in seen:
            seen.add(symbol)
            out.append(row_map[symbol])
    return out[:60]


def _theme_of(row: MarketRow) -> str:
    stock = STOCKS.get(row.symbol)
    return stock.theme if stock else "其他"


def _sector_strength(rows: list[MarketRow]) -> list[dict]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.change_pct <= 0:
            continue
        theme = _theme_of(row)
        b = buckets.setdefault(theme, {"theme": theme, "count": 0, "avg_change_pct": 0.0, "leaders": []})
        b["count"] += 1
        b["avg_change_pct"] += row.change_pct
        if len(b["leaders"]) < 5:
            b["leaders"].append(row.label)
    out = []
    for b in buckets.values():
        if b["count"]:
            b["avg_change_pct"] = round(b["avg_change_pct"] / b["count"], 2)
            out.append(b)
    out.sort(key=lambda x: (-x["avg_change_pct"], -x["count"]))
    return out[:12]


def _classify_market_candidate(row: MarketRow, card: dict | None) -> dict[str, Any]:
    tech = (card or {}).get("tech") or {}
    prices = (card or {}).get("prices") or []
    close = _safe_float(tech.get("close"), row.close) or row.close
    rsi = _safe_float(tech.get("rsi"), 50.0)
    volume_ratio = _safe_float(tech.get("volume_ratio"), 1.0)
    ma20 = _safe_float(tech.get("ma20"), 0.0)
    ma60 = _safe_float(tech.get("ma60"), 0.0)
    breakout = _safe_float(tech.get("breakout"), 0.0)
    high20 = _recent_high(prices[:-1] or prices, 20)
    new_high = bool(high20 and close >= high20 * 0.995)
    opening_gap = _opening_gap_pct(row)
    intraday_range = 0.0
    if row.high and row.low and row.low > 0:
        intraday_range = round((row.high - row.low) / row.low * 100, 2)

    score = 0
    reasons: list[str] = []
    change_pct = row.change_pct
    if change_pct >= 8.8:
        score += 34
        reasons.append(f"漲幅 {change_pct}% 接近漲停，資金強度很高")
    elif change_pct >= 5:
        score += 28
        reasons.append(f"漲幅 {change_pct}% 明顯強於市場")
    elif change_pct >= 3:
        score += 20
        reasons.append(f"漲幅 {change_pct}% 屬強勢上漲")
    elif change_pct > 0:
        score += 8
        reasons.append(f"上漲 {change_pct}%，動能偏正向")

    if volume_ratio >= 2.5:
        score += 22
        reasons.append(f"量能比 {volume_ratio} 明顯放大")
    elif volume_ratio >= 1.5:
        score += 18
        reasons.append(f"量能比 {volume_ratio} 放大")
    elif volume_ratio >= 1.15:
        score += 10
        reasons.append(f"量能比 {volume_ratio} 溫和放大")

    if new_high:
        score += 18
        reasons.append("突破或接近近 20 日高點")
    if breakout and close >= breakout:
        score += 14
        reasons.append(f"已站上突破價 {breakout:.2f}")
    elif breakout and close >= breakout * 0.97:
        score += 8
        reasons.append(f"接近突破價 {breakout:.2f}")
    if ma20 and close > ma20:
        score += 6
    if ma60 and close > ma60:
        score += 6
    if 45 <= rsi <= 72:
        score += 8
        reasons.append(f"RSI {rsi} 尚未明顯過熱")
    elif rsi > 78:
        score -= 14
        reasons.append(f"RSI {rsi} 偏熱，不適合追價")
    if opening_gap >= 3:
        score += 4
        reasons.append(f"開盤跳空 {opening_gap}% ，題材或資金有主動性")

    score = max(0, min(100, int(round(score))))
    card_actionable = bool((card or {}).get("data_trust", {}).get("actionable", True))
    # v3.8.3: 強勢股可追條件要明確，不再單純用 RSI 過熱一刀切。
    # 可追條件：漲幅 2%~8%、量能 1.2~3.8、RSI 45~76、接近或突破短期新高，且資料可操作。
    too_hot = change_pct >= 8.8 or rsi >= 82 or volume_ratio >= 4.5
    chase_setup = (
        2.0 <= change_pct <= 8.0
        and 1.2 <= volume_ratio <= 3.8
        and 45 <= rsi <= 76
        and (new_high or (breakout and close >= breakout * 0.96) or (ma20 and close > ma20))
    )
    chaseable = card_actionable and score >= 68 and chase_setup and not too_hot

    if chaseable:
        category = "可追強勢"
        teacher_view = "今日漲幅、量能與價格位置同時轉強，且尚未到失控過熱區；老師判斷可列為強勢追蹤標的，但仍以回測不破或盤中站穩為執行條件。"
        action_plan = "可用小部位試單；若急拉超過當日轉強區、量能暴衝或跌回突破區下方，改列明日接力觀察。"
    elif change_pct >= 8.2:
        category = "已漲不追"
        teacher_view = "資金很強，但漲幅已大或量價過熱；空手者不追，等隔日換手或回測支撐。"
        action_plan = "明日觀察是否開高不爆量、量縮整理不破今日高檔支撐。"
    elif score >= 68:
        category = "今日強勢"
        teacher_view = "今日量價與價格位置轉強，但尚未同時滿足可追條件；先觀察是否站穩與量能是否延續。"
        action_plan = "若未追高，等回測或突破確認；已持有者觀察量能是否延續。"
    elif score >= 55:
        category = "明日接力觀察"
        teacher_view = "已有轉強跡象但尚未達到可追條件，適合列入隔日追蹤。"
        action_plan = "等放量突破或拉回守穩，不提前追價。"
    else:
        category = "一般觀察"
        teacher_view = "今日強度不足，不列入主名單。"
        action_plan = "等待更明確量價訊號。"

    if not reasons:
        reasons.append("尚未形成明確強勢訊號")

    return {
        "symbol": row.symbol,
        "name": row.name,
        "label": row.label,
        "market": row.market,
        "source": row.source,
        "date": row.date,
        "strength_score": score,
        "strength_category": category,
        "strength_reasons": reasons[:7],
        "teacher_view": teacher_view,
        "action_plan": action_plan,
        "tomorrow_plan": action_plan,
        "change_pct": change_pct,
        "close": row.close,
        "volume": row.volume,
        "value": row.value,
        "volume_ratio": volume_ratio,
        "opening_gap_pct": opening_gap,
        "intraday_range_pct": intraday_range,
        "new_20d_high": new_high,
        "rsi": rsi,
        "linked_decision": (card or {}).get("decision"),
        "linked_grade": (card or {}).get("grade"),
        "card": card,
    }


def build_market_strength_payload(decision_cards: list[dict], status: dict, build_card: Callable[[StockInfo], dict]) -> dict[str, Any]:
    snapshot = fetch_market_snapshot()
    rows: list[MarketRow] = snapshot["rows"]

    # Final safety net: if all market connectors fail, still let the user see a
    # clearly labelled limited-universe strength scan from the same price payload
    # used by today's decision cards. This prevents an empty page while making
    # it explicit that this is not a successful full-market scan.
    limited_universe_used = False
    if not rows and decision_cards:
        rows = _rows_from_decision_cards(decision_cards)
        limited_universe_used = bool(rows)

    rankings = _rank_rows(rows) if rows else {"top_gainers": [], "top_volume": [], "top_value": [], "limit_like": []}
    candidates = _candidate_market_rows(rows) if rows else []
    card_by_symbol = {c.get("symbol"): c for c in decision_cards}
    classified: list[dict] = []

    for row in candidates:
        card = card_by_symbol.get(row.symbol)
        if card is None:
            try:
                stock = _stock_from_market_row(row)
                card = build_card(stock)
            except Exception:
                card = None
        classified.append(_classify_market_candidate(row, card))

    if not rows:
        from radar.teacher.strength import build_strength_payload  # local import avoids cycle
        fallback = build_strength_payload(decision_cards)
        fallback["data_coverage"] = {
            "mode": "no_market_data",
            "total_market_rows": 0,
            "official_rows": snapshot.get("official_rows", 0),
            "yahoo_rows": snapshot.get("yahoo_rows", 0),
            "yahoo_chart_rows": snapshot.get("yahoo_chart_rows", 0),
            "candidate_rows": len(decision_cards),
            "sources": [],
            "errors": snapshot.get("errors", []),
            "endpoint_attempts": snapshot.get("endpoint_attempts", []),
            "message": snapshot.get("message") or "未取得全市場強勢資料；不產生假排行。",
        }
        fallback["chaseable_list"] = []
        fallback["ranking_tables"] = rankings
        fallback["sector_strength"] = []
        return fallback

    strong = [r for r in classified if r["strength_score"] >= 68]
    strong.sort(key=lambda r: (-r["strength_score"], -r["change_pct"], -r["volume_ratio"]))
    chaseable = [r for r in classified if r["strength_category"] == "可追強勢"]
    chaseable.sort(key=lambda r: (-r["strength_score"], -r["volume_ratio"], -r["change_pct"]))
    limit_watch = [r for r in classified if r["change_pct"] >= 8.2]
    limit_watch.sort(key=lambda r: (-r["change_pct"], -r["value"]))
    no_chase = [r for r in classified if r["strength_category"] == "已漲不追"]
    no_chase.sort(key=lambda r: (-r["change_pct"], -r["volume_ratio"]))
    tomorrow = [r for r in classified if r["strength_category"] in {"明日接力觀察", "今日強勢", "已漲不追", "可追強勢"}]
    tomorrow.sort(key=lambda r: (-r["strength_score"], -r["volume_ratio"], -r["change_pct"]))

    return {
        "chaseable_list": chaseable[:10],
        "strong_list": strong[:15],
        "limit_watch": limit_watch[:12],
        "no_chase_list": no_chase[:12],
        "tomorrow_watch": tomorrow[:15],
        "all_strength": sorted(classified, key=lambda r: (-r["strength_score"], -r["change_pct"]))[:40],
        "ranking_tables": rankings,
        "sector_strength": _sector_strength(rows),
        "data_coverage": {
            "mode": "decision_universe_fallback" if limited_universe_used else (snapshot.get("mode") or "full_market_scan"),
            "total_market_rows": len(rows),
            "official_rows": snapshot.get("official_rows", 0),
            "yahoo_rows": snapshot.get("yahoo_rows", 0),
            "yahoo_chart_rows": snapshot.get("yahoo_chart_rows", 0),
            "candidate_rows": len(candidates),
            "classified_rows": len(classified),
            "sources": sorted({r.get("source") for r in classified if r.get("source")}) if limited_universe_used else snapshot.get("sources", []),
            "errors": snapshot.get("errors", []),
            "endpoint_attempts": snapshot.get("endpoint_attempts", []),
            "message": "全市場連接器失敗，已使用今日決策股票池做有限強勢掃描；這不是全市場排行。" if limited_universe_used else (snapshot.get("message") or "已建立強勢股雷達資料。"),
        },
    }


def build_strength_gap_analysis(buy_list: list[dict], strength_payload: dict) -> dict[str, Any]:
    buy_symbols = {c.get("symbol") for c in buy_list}
    chaseable = strength_payload.get("chaseable_list", [])
    strong_rows = strength_payload.get("strong_list", [])
    strong_symbols = {r.get("symbol") for r in strong_rows}
    strong_not_buy = [r for r in strong_rows if r.get("symbol") not in buy_symbols][:8]
    buy_not_strong = [c for c in buy_list if c.get("symbol") not in strong_symbols][:8]
    lines: list[str] = []
    if chaseable:
        names = "、".join(r["label"] for r in chaseable[:5])
        lines.append(f"今日強勢股中可追蹤的候選：{names}。這些不是無條件追高，而是需符合量價延續與回測不破。")
    if strong_not_buy:
        names = "、".join(r["label"] for r in strong_not_buy[:5])
        lines.append(f"今日強勢但未列入波段可買：{names}。原因通常是漲幅已大、離理想買點太遠或需要隔日換手確認。")
    if buy_not_strong:
        names = "、".join(c["label"] for c in buy_not_strong[:5])
        lines.append(f"今日可買但非全市場最強勢：{names}。這類偏波段買點，不是追漲停邏輯。")
    if not lines:
        coverage = strength_payload.get("data_coverage", {})
        lines.append(coverage.get("message") or "目前強勢股雷達沒有明確主線，今日不硬追強勢。")
    return {"strong_not_buy": strong_not_buy, "buy_not_strong": buy_not_strong, "summary": " ".join(lines)}
