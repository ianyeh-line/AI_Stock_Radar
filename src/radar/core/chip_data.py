"""Chip / institutional flow foundation for Taiwan stocks.

v3.11.1 scope is intentionally conservative:
- Try to fetch official TWSE T86 three-institution flow for listed stocks.
- Do not fabricate chip conclusions when official data is unavailable.
- Return explicit availability and status so the teacher narrative can say what
  is known and what is not known.

This is a foundation, not the final chip trend engine. v3.12 can extend this to
multi-day consecutive buy/sell, TPEx equivalents, margin trading, and broker
branch data.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

import requests

from radar.data.stock_master import StockInfo

TWSE_T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"


@dataclass(frozen=True)
class ChipFlow:
    symbol: str
    name: str
    available: bool
    source: str
    latest_date: str
    foreign_net_lot: int = 0
    investment_trust_net_lot: int = 0
    dealer_net_lot: int = 0
    total_net_lot: int = 0
    bias: str = "籌碼資料不足"
    message: str = "尚未取得可用三大法人資料"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _int_value(value: object) -> int:
    text = str(value or "").replace(",", "").replace("--", "0").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except Exception:
        return 0


def _lot(value: int) -> int:
    return int(round(value / 1000))


def _find_idx(fields: list[str], include: list[str], exclude: list[str] | None = None) -> int | None:
    exclude = exclude or []
    for idx, field in enumerate(fields):
        text = re.sub(r"\s+", "", str(field))
        if all(token in text for token in include) and not any(token in text for token in exclude):
            return idx
    return None


def _recent_trade_dates(max_days: int = 7) -> list[str]:
    out: list[str] = []
    cursor = date.today()
    while len(out) < max_days:
        if cursor.weekday() < 5:
            out.append(cursor.strftime("%Y%m%d"))
        cursor -= timedelta(days=1)
    return out


def _bias(total_lot: int, foreign_lot: int, trust_lot: int) -> str:
    if total_lot >= 3000 or trust_lot >= 800:
        return "法人明顯偏多"
    if total_lot >= 800 or foreign_lot >= 1200 or trust_lot >= 300:
        return "法人偏多"
    if total_lot <= -3000 or trust_lot <= -800:
        return "法人明顯偏空"
    if total_lot <= -800 or foreign_lot <= -1200 or trust_lot <= -300:
        return "法人偏空"
    return "法人中性"


def _summary(flow: ChipFlow) -> str:
    return (
        f"{flow.bias}：外資 {flow.foreign_net_lot:,} 張、投信 {flow.investment_trust_net_lot:,} 張、"
        f"自營商 {flow.dealer_net_lot:,} 張，三大法人合計 {flow.total_net_lot:,} 張。"
    )


@lru_cache(maxsize=8)
def _fetch_twse_t86(date_text: str) -> tuple[tuple[tuple[str, Any], ...], ...]:
    response = requests.get(
        TWSE_T86_URL,
        params={"date": date_text, "selectType": "ALL", "response": "json"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=4,
    )
    response.raise_for_status()
    payload = response.json()
    fields = payload.get("fields") or []
    rows = payload.get("data") or []
    if not fields or not rows:
        return tuple()

    code_idx = _find_idx(fields, ["證券代號"]) or 0
    name_idx = _find_idx(fields, ["證券名稱"]) or 1
    foreign_idx = (
        _find_idx(fields, ["外陸資", "買賣超股數"], exclude=["自營商"])
        or _find_idx(fields, ["外資", "買賣超股數"], exclude=["自營商"])
    )
    trust_idx = _find_idx(fields, ["投信", "買賣超股數"])
    dealer_idx = _find_idx(fields, ["自營商", "買賣超股數"], exclude=["避險", "自行"])
    total_idx = _find_idx(fields, ["三大法人", "買賣超股數"])

    parsed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(code_idx, name_idx):
            continue
        symbol = str(row[code_idx]).strip()
        if not re.fullmatch(r"\d{4}", symbol):
            continue
        foreign = _int_value(row[foreign_idx]) if foreign_idx is not None and foreign_idx < len(row) else 0
        trust = _int_value(row[trust_idx]) if trust_idx is not None and trust_idx < len(row) else 0
        dealer = _int_value(row[dealer_idx]) if dealer_idx is not None and dealer_idx < len(row) else 0
        total = _int_value(row[total_idx]) if total_idx is not None and total_idx < len(row) else foreign + trust + dealer
        parsed.append({
            "symbol": symbol,
            "name": str(row[name_idx]).strip(),
            "foreign_lot": _lot(foreign),
            "trust_lot": _lot(trust),
            "dealer_lot": _lot(dealer),
            "total_lot": _lot(total),
        })
    return tuple(tuple(item.items()) for item in parsed)


def _load_latest_t86() -> tuple[str, dict[str, dict[str, Any]], str]:
    last_error = ""
    for d in _recent_trade_dates():
        try:
            items = [dict(pairs) for pairs in _fetch_twse_t86(d)]
            if items:
                return d, {item["symbol"]: item for item in items}, "TWSE T86 三大法人"
        except Exception as exc:
            last_error = str(exc)
    return "", {}, last_error or "TWSE T86 未取得資料"


def fetch_chip_flow(stock: StockInfo) -> ChipFlow:
    if stock.market == "TWO":
        return ChipFlow(
            stock.symbol,
            stock.name,
            False,
            "TPEx chip connector pending",
            "",
            message="目前尚未接入上櫃個股完整三大法人資料，本次不以籌碼面加分。",
        )
    latest_date, rows, source = _load_latest_t86()
    row = rows.get(stock.symbol)
    if not row:
        return ChipFlow(stock.symbol, stock.name, False, source, latest_date, message="未在 TWSE T86 取得該股三大法人資料，本次不以籌碼面加分。")
    bias = _bias(int(row["total_lot"]), int(row["foreign_lot"]), int(row["trust_lot"]))
    flow = ChipFlow(
        stock.symbol,
        str(row.get("name") or stock.name),
        True,
        source,
        latest_date,
        int(row["foreign_lot"]),
        int(row["trust_lot"]),
        int(row["dealer_lot"]),
        int(row["total_lot"]),
        bias,
        "",
    )
    return ChipFlow(**{**flow.as_dict(), "message": _summary(flow)})
