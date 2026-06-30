"""Official Taiwan market data integrations.

v3.4.0 introduces an official-data-first layer for latest daily snapshots.

Design principles:
- TWSE / TPEx official OpenAPI data is used for the latest Taiwan daily close
  snapshot when available.
- Yahoo Finance remains the historical OHLC source for technical indicators and
  chart continuity.
- If official data is unavailable, the product continues to run with Yahoo data
  but data trust will explicitly flag that official confirmation is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import requests

from radar.data.stock_master import StockInfo


TWSE_STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_DAILY_CLOSE_URLS = [
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?response=json",
]


@dataclass(frozen=True)
class OfficialSnapshot:
    symbol: str
    name: str
    market: str
    source: str
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    change: float | None
    ok: bool
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "source": self.source,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "change": self.change,
            "ok": self.ok,
            "message": self.message,
        }


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "-", "X", "除權息"}:
        return None
    # Taiwan exchange data sometimes includes + / - prefixes.
    text = text.replace("+", "")
    try:
        return float(text)
    except Exception:
        return None


def _parse_int(value: Any) -> int | None:
    parsed = _parse_float(value)
    if parsed is None:
        return None
    try:
        return int(parsed)
    except Exception:
        return None


def _get_any(row: dict[str, Any], *keys: str) -> Any:
    # Exact match first.
    for key in keys:
        if key in row:
            return row[key]
    # Case-insensitive / whitespace-insensitive fallback.
    normalized = {str(k).strip().lower().replace(" ", ""): v for k, v in row.items()}
    for key in keys:
        nk = key.strip().lower().replace(" ", "")
        if nk in normalized:
            return normalized[nk]
    return None


def _normalize_symbol(value: Any) -> str:
    text = str(value or "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[:4] if len(digits) >= 4 else text


def _today_string() -> str:
    return date.today().isoformat()


def _snapshot_from_row(row: dict[str, Any], stock: StockInfo, source: str) -> OfficialSnapshot:
    name = str(_get_any(row, "Name", "證券名稱", "公司名稱", "有價證券名稱", "名稱") or stock.name).strip() or stock.name
    raw_date = _get_any(row, "Date", "日期", "資料日期")
    snapshot_date = str(raw_date).strip() if raw_date else _today_string()
    open_ = _parse_float(_get_any(row, "OpeningPrice", "開盤價", "Open", "開盤"))
    high = _parse_float(_get_any(row, "HighestPrice", "最高價", "High", "最高"))
    low = _parse_float(_get_any(row, "LowestPrice", "最低價", "Low", "最低"))
    close = _parse_float(_get_any(row, "ClosingPrice", "收盤價", "Close", "收盤"))
    volume = _parse_int(_get_any(row, "TradeVolume", "成交股數", "成交量", "Volume"))
    change = _parse_float(_get_any(row, "Change", "漲跌價差", "漲跌", "ChangePrice"))
    return OfficialSnapshot(
        symbol=stock.symbol,
        name=name,
        market=stock.market,
        source=source,
        date=snapshot_date,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        change=change,
        ok=close is not None and close > 0,
    )


@lru_cache(maxsize=8)
def _fetch_json_cached(url: str, timeout: float) -> tuple[tuple[tuple[str, Any], ...], ...]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        rows = [row for row in data if isinstance(row, dict)]
    elif isinstance(data, dict):
        rows = []
        # Some APIs wrap data in a named field.
        for key in ("data", "result", "items"):
            maybe_rows = data.get(key)
            if isinstance(maybe_rows, list):
                rows = [row for row in maybe_rows if isinstance(row, dict)]
                break
    else:
        rows = []
    # Return a hashable representation so lru_cache can keep it safely.
    return tuple(tuple(row.items()) for row in rows)


def _fetch_json(url: str, timeout: float) -> list[dict[str, Any]]:
    return [dict(items) for items in _fetch_json_cached(url, timeout)]


def _find_symbol(rows: list[dict[str, Any]], stock: StockInfo) -> dict[str, Any] | None:
    for row in rows:
        code = _normalize_symbol(_get_any(row, "Code", "SecuritiesCompanyCode", "證券代號", "有價證券代號", "代號"))
        if code == stock.symbol:
            return row
    return None


def fetch_official_snapshot(stock: StockInfo, timeout: float = 5.0) -> OfficialSnapshot:
    """Fetch the latest official daily snapshot from TWSE / TPEx.

    The function is intentionally defensive because official OpenAPI field names
    can differ between TWSE and TPEx. If any issue occurs, it returns ok=False
    instead of raising, so the app can fall back to Yahoo Finance.
    """
    if stock.market == "TWO":
        last_message = ""
        for url in TPEX_DAILY_CLOSE_URLS:
            try:
                rows = _fetch_json(url, timeout)
                row = _find_symbol(rows, stock)
                if row:
                    return _snapshot_from_row(row, stock, "TPEx OpenAPI")
                last_message = "TPEx OpenAPI 找不到個股"
            except Exception as exc:
                last_message = str(exc)
        return OfficialSnapshot(stock.symbol, stock.name, stock.market, "TPEx OpenAPI", "", None, None, None, None, None, None, False, last_message)

    try:
        rows = _fetch_json(TWSE_STOCK_DAY_ALL_URL, timeout)
        row = _find_symbol(rows, stock)
        if row:
            return _snapshot_from_row(row, stock, "TWSE OpenAPI")
        return OfficialSnapshot(stock.symbol, stock.name, stock.market, "TWSE OpenAPI", "", None, None, None, None, None, None, False, "TWSE OpenAPI 找不到個股")
    except Exception as exc:
        return OfficialSnapshot(stock.symbol, stock.name, stock.market, "TWSE OpenAPI", "", None, None, None, None, None, None, False, str(exc))


def apply_official_snapshot(price_payload: dict[str, Any], snapshot: OfficialSnapshot) -> dict[str, Any]:
    """Merge official latest snapshot into Yahoo historical payload.

    Yahoo remains useful for historical charting. Official data is used to
    confirm / correct the latest close when available.
    """
    payload = dict(price_payload)
    payload["official_snapshot"] = snapshot.as_dict()
    if not snapshot.ok or snapshot.close is None:
        payload["official_confirmed"] = False
        payload["official_source"] = snapshot.source
        return payload

    rows = [dict(row) for row in payload.get("prices", [])]
    if rows:
        last = rows[-1]
        # Official daily snapshot is treated as the most reliable latest daily
        # close. If its date is unavailable, keep Yahoo date but still confirm
        # close / OHLC fields.
        if snapshot.date:
            last["date"] = snapshot.date
        last["close"] = round(float(snapshot.close), 2)
        if snapshot.open is not None:
            last["open"] = round(float(snapshot.open), 2)
        if snapshot.high is not None:
            last["high"] = round(float(snapshot.high), 2)
        if snapshot.low is not None:
            last["low"] = round(float(snapshot.low), 2)
        if snapshot.volume is not None:
            last["volume"] = int(snapshot.volume)
        rows[-1] = last
        payload["prices"] = rows
    payload["name"] = snapshot.name or payload.get("name")
    payload["source"] = f"{snapshot.source} + Yahoo Finance"
    payload["official_source"] = snapshot.source
    payload["official_confirmed"] = True
    payload["latest_date"] = snapshot.date or payload.get("latest_date")
    payload["data_quality"] = "official_confirmed_daily"
    return payload
