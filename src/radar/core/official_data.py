"""Official Taiwan market data integrations with freshness-aware source selection.

v3.5.3 Data Freshness Rule:
- TWSE / TPEx official data and Yahoo Finance are compared by data date.
- The newest valid data source is selected, regardless of whether it is official or Yahoo.
- Price-source differences are disclosed in source metadata only; they do not
  downgrade recommendations when the selected data is the newest valid data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
    for key in keys:
        if key in row:
            return row[key]
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


def _normalize_snapshot_date(value: Any) -> str:
    """Normalize common exchange date formats to ISO date.

    Accepted examples:
    - 2026-06-30
    - 2026/06/30
    - 20260630
    - 115/06/30 (ROC year)

    Empty / unknown dates intentionally return an empty string. Earlier versions
    used today's date as a fallback, which could make stale official data look
    fresh. v3.5.0 avoids that.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = text.replace("年", "/").replace("月", "/").replace("日", "")
    text = text.replace(".", "/").replace("-", "/")
    digits = "".join(ch for ch in text if ch.isdigit())
    candidates: list[tuple[int, int, int]] = []
    if len(digits) == 8:
        candidates.append((int(digits[:4]), int(digits[4:6]), int(digits[6:8])))
    elif len(digits) == 7:
        # Taiwan ROC year, e.g. 1150630
        candidates.append((int(digits[:3]) + 1911, int(digits[3:5]), int(digits[5:7])))
    parts = [p for p in text.split("/") if p]
    if len(parts) >= 3:
        y = int(parts[0])
        if y < 1911:
            y += 1911
        candidates.append((y, int(parts[1]), int(parts[2])))
    for y, m, d in candidates:
        try:
            return date(y, m, d).isoformat()
        except Exception:
            continue
    return ""


def _date_value(value: str | None) -> date | None:
    try:
        return date.fromisoformat(str(value or ""))
    except Exception:
        return None


def _snapshot_from_row(row: dict[str, Any], stock: StockInfo, source: str) -> OfficialSnapshot:
    name = str(_get_any(row, "Name", "證券名稱", "公司名稱", "有價證券名稱", "名稱") or stock.name).strip() or stock.name
    raw_date = _get_any(row, "Date", "日期", "資料日期", "TradeDate", "交易日期")
    snapshot_date = _normalize_snapshot_date(raw_date)
    open_ = _parse_float(_get_any(row, "OpeningPrice", "開盤價", "Open", "開盤"))
    high = _parse_float(_get_any(row, "HighestPrice", "最高價", "High", "最高"))
    low = _parse_float(_get_any(row, "LowestPrice", "最低價", "Low", "最低"))
    close = _parse_float(_get_any(row, "ClosingPrice", "收盤價", "Close", "收盤"))
    volume = _parse_int(_get_any(row, "TradeVolume", "成交股數", "成交量", "Volume"))
    change = _parse_float(_get_any(row, "Change", "漲跌價差", "漲跌", "ChangePrice"))
    message = "" if snapshot_date else "官方資料未提供可驗證日期，不直接覆蓋 Yahoo 最新日線"
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
        message=message,
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
        for key in ("data", "result", "items"):
            maybe_rows = data.get(key)
            if isinstance(maybe_rows, list):
                rows = [row for row in maybe_rows if isinstance(row, dict)]
                break
    else:
        rows = []
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


def _merge_snapshot_into_rows(rows: list[dict[str, Any]], snapshot: OfficialSnapshot) -> list[dict[str, Any]]:
    out = [dict(row) for row in rows]
    new_row = {
        "date": snapshot.date,
        "open": round(float(snapshot.open if snapshot.open is not None else snapshot.close), 2),
        "high": round(float(snapshot.high if snapshot.high is not None else snapshot.close), 2),
        "low": round(float(snapshot.low if snapshot.low is not None else snapshot.close), 2),
        "close": round(float(snapshot.close or 0), 2),
        "volume": int(snapshot.volume or 0),
    }
    if out and out[-1].get("date") == snapshot.date:
        out[-1].update({k: v for k, v in new_row.items() if v not in {None, 0} or k == "date"})
    else:
        out.append(new_row)
    return out


def _safe_ratio_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    return abs(a - b) / max(min(a, b), 1e-9)


def _latest_row_close(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    try:
        return float(rows[-1].get("close"))
    except Exception:
        return None


def apply_official_snapshot(price_payload: dict[str, Any], snapshot: OfficialSnapshot) -> dict[str, Any]:
    """Select the freshest available price source.

    v3.5.3 Data Freshness Rule:
    - Do not downgrade only because data comes from Yahoo or differs from official.
    - Compare source dates and use the newest valid data.
    - If official and Yahoo have the same date, keep Yahoo as the price basis so
      historical indicators and chart data remain consistent; official is used
      as confirmation metadata.
    - Only fallback, stale date, missing date, or insufficient samples should
      limit recommendations.
    """
    payload = dict(price_payload)
    rows = [dict(row) for row in payload.get("prices", [])]
    yahoo_date_text = str(payload.get("latest_date") or (rows[-1].get("date") if rows else ""))
    yahoo_date = _date_value(_normalize_snapshot_date(yahoo_date_text) or yahoo_date_text)
    official_date_text = _normalize_snapshot_date(snapshot.date) or snapshot.date
    official_date = _date_value(official_date_text)
    snapshot_dict = snapshot.as_dict()
    snapshot_dict["date"] = official_date_text

    payload["yahoo_latest_date"] = yahoo_date.isoformat() if yahoo_date else yahoo_date_text
    payload["official_snapshot"] = snapshot_dict
    payload["official_source"] = snapshot.source
    payload["official_date"] = official_date_text
    payload["official_price_anomaly"] = False
    payload["source_selection"] = {
        "selected": payload.get("source", "Yahoo Finance"),
        "reason": "預設使用 Yahoo Finance 歷史日線與最新報價",
        "yahoo_date": payload["yahoo_latest_date"],
        "official_date": official_date_text,
    }

    if not snapshot.ok or snapshot.close is None:
        payload["official_confirmed"] = False
        payload["official_lagging"] = False
        payload["official_date_verified"] = False
        payload["source_selection"] = {
            "selected": payload.get("source", "Yahoo Finance"),
            "reason": f"官方資料不可用：{snapshot.message or '未取得有效收盤價'}；採用 Yahoo 最新可得資料",
            "yahoo_date": payload["yahoo_latest_date"],
            "official_date": official_date_text,
        }
        return payload

    if official_date is None:
        payload["official_confirmed"] = False
        payload["official_lagging"] = False
        payload["official_date_verified"] = False
        payload["data_quality"] = "yahoo_with_undated_official"
        payload["source_selection"] = {
            "selected": payload.get("source", "Yahoo Finance"),
            "reason": "官方資料有價格但無可驗證日期；依最新資料規則採用 Yahoo 最新可得資料",
            "yahoo_date": payload["yahoo_latest_date"],
            "official_date": "未提供",
        }
        return payload

    # Newest date wins. If dates tie, Yahoo remains the price basis because it
    # provides the full technical series used by the chart and indicators.
    if yahoo_date is not None and official_date <= yahoo_date:
        payload["official_confirmed"] = official_date == yahoo_date
        payload["official_lagging"] = official_date < yahoo_date
        payload["official_date_verified"] = True
        if official_date < yahoo_date:
            payload["data_quality"] = "yahoo_newer_than_official"
            payload["source"] = "Yahoo Finance（較新）"
            reason = "Yahoo 資料日期較官方資料新，依最新資料規則採用 Yahoo 作為今日判斷基準"
        else:
            payload["data_quality"] = "yahoo_same_day_official_confirmed"
            payload["source"] = "Yahoo Finance + 官方同日確認"
            reason = "Yahoo 與官方資料同日；依最新資料規則保留 Yahoo 技術序列，官方作為同日確認"
        payload["latest_date"] = yahoo_date.isoformat() if yahoo_date else yahoo_date_text
        payload["source_selection"] = {
            "selected": payload["source"],
            "reason": reason,
            "yahoo_date": payload["yahoo_latest_date"],
            "official_date": official_date.isoformat(),
        }
        return payload

    # Official date is newer than Yahoo. Append official snapshot as the latest
    # row while preserving Yahoo history for indicators.
    normalized_snapshot = OfficialSnapshot(
        snapshot.symbol, snapshot.name, snapshot.market, snapshot.source,
        official_date.isoformat(), snapshot.open, snapshot.high, snapshot.low,
        snapshot.close, snapshot.volume, snapshot.change, snapshot.ok, snapshot.message,
    )
    payload["prices"] = _merge_snapshot_into_rows(rows, normalized_snapshot)
    payload["name"] = snapshot.name or payload.get("name")
    payload["source"] = f"{snapshot.source}（較新） + Yahoo Finance 歷史線圖"
    payload["official_confirmed"] = True
    payload["official_lagging"] = False
    payload["official_date_verified"] = True
    payload["latest_date"] = official_date.isoformat()
    payload["data_quality"] = "official_newer_than_yahoo"
    payload["source_selection"] = {
        "selected": snapshot.source,
        "reason": "官方資料日期較 Yahoo 新，依最新資料規則採用官方最新快照作為今日判斷基準",
        "yahoo_date": payload["yahoo_latest_date"],
        "official_date": official_date.isoformat(),
    }
    return payload
