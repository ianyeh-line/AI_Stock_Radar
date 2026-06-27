"""Institutional flow datasource for Taiwan stocks.

This module tries to load the latest available TWSE T86 institutional trading
summary. When the public endpoint is unavailable, it falls back to a deterministic
price-volume based estimate so the product remains executable.

The fallback is explicitly marked as fallback; it is not a replacement for
official institutional trading data.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from radar.models.domain import StockMeta, TechnicalProfile

TWSE_T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86?date={date}&selectType=ALL&response=json"


@dataclass(frozen=True)
class InstitutionalFlowProfile:
    symbol: str
    name: str
    latest_date: str
    source: str
    foreign_net: int
    investment_trust_net: int
    dealer_net: int
    total_net: int
    flow_score: int
    flow_bias: str
    summary: str

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


def _find_idx(fields: list[str], patterns: list[str], exclude: list[str] | None = None) -> int | None:
    exclude = exclude or []
    for idx, field in enumerate(fields):
        text = re.sub(r"\s+", "", str(field))
        if all(pattern in text for pattern in patterns) and not any(pattern in text for pattern in exclude):
            return idx
    return None


def _trading_dates(max_days: int = 6) -> list[str]:
    today = datetime.today().date()
    dates: list[str] = []
    cursor = today
    while len(dates) < max_days:
        if cursor.weekday() < 5:
            dates.append(cursor.strftime("%Y%m%d"))
        cursor -= timedelta(days=1)
    return dates


def _fetch_twse_t86_for_date(date_text: str) -> dict[str, InstitutionalFlowProfile]:
    url = TWSE_T86_URL.format(date=urllib.parse.quote(date_text))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))

    fields = payload.get("fields") or []
    rows = payload.get("data") or []
    if not fields or not rows:
        raise RuntimeError("TWSE T86 returned no data")

    code_idx = _find_idx(fields, ["證券代號"]) or 0
    name_idx = _find_idx(fields, ["證券名稱"]) or 1
    foreign_idx = (
        _find_idx(fields, ["外陸資", "買賣超股數"], exclude=["自營商"])
        or _find_idx(fields, ["外資及陸資", "買賣超股數"], exclude=["自營商"])
        or _find_idx(fields, ["外資", "買賣超股數"], exclude=["自營商"])
    )
    trust_idx = _find_idx(fields, ["投信", "買賣超股數"])
    dealer_idx = _find_idx(fields, ["自營商", "買賣超股數"], exclude=["避險", "自行"])
    total_idx = _find_idx(fields, ["三大法人", "買賣超股數"])

    result: dict[str, InstitutionalFlowProfile] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) <= max(code_idx, name_idx):
            continue
        symbol = str(row[code_idx]).strip()
        name = str(row[name_idx]).strip()
        if not re.fullmatch(r"\d{4}", symbol):
            continue
        foreign = _int_value(row[foreign_idx]) if foreign_idx is not None and foreign_idx < len(row) else 0
        trust = _int_value(row[trust_idx]) if trust_idx is not None and trust_idx < len(row) else 0
        dealer = _int_value(row[dealer_idx]) if dealer_idx is not None and dealer_idx < len(row) else 0
        total = _int_value(row[total_idx]) if total_idx is not None and total_idx < len(row) else foreign + trust + dealer
        profile = _make_profile(symbol, name, date_text, "TWSE T86 三大法人", foreign, trust, dealer, total)
        result[symbol] = profile
    return result


def _flow_score(foreign: int, trust: int, dealer: int, total: int) -> int:
    foreign_lots = foreign / 1000
    trust_lots = trust / 1000
    dealer_lots = dealer / 1000
    total_lots = total / 1000

    # v1.7.1: total net flow must dominate the final bias.
    # A single institution buying cannot be labelled "明顯偏多" when the three
    # institutions combined are net sellers.
    weighted = (foreign_lots / 1800 * 4) + (trust_lots / 450 * 4) + (dealer_lots / 900 * 2) + (total_lots / 2000 * 8)
    score = round(weighted)
    if total_lots < -300 and score > 3:
        score = 3
    if total_lots > 300 and score < -3:
        score = -3
    return max(-18, min(18, score))


def _bias(score: int) -> str:
    if score >= 9:
        return "法人明顯偏多"
    if score >= 4:
        return "法人偏多"
    if score <= -9:
        return "法人明顯偏空"
    if score <= -4:
        return "法人偏空"
    return "法人中性"


def _lots(value: int) -> str:
    return f"{round(value / 1000):,} 張"


def _make_profile(symbol: str, name: str, latest_date: str, source: str, foreign: int, trust: int, dealer: int, total: int) -> InstitutionalFlowProfile:
    score = _flow_score(foreign, trust, dealer, total)
    bias = _bias(score)
    summary = (
        f"{bias}：外資 {_lots(foreign)}、投信 {_lots(trust)}、自營商 {_lots(dealer)}，"
        f"三大法人合計 {_lots(total)}。"
    )
    return InstitutionalFlowProfile(symbol, name, latest_date, source, foreign, trust, dealer, total, score, bias, summary)


def _fallback_profile(stock: StockMeta, technical: TechnicalProfile | None) -> InstitutionalFlowProfile:
    if technical is None:
        return InstitutionalFlowProfile(stock.symbol, stock.name, "N/A", "Fallback Flow Model", 0, 0, 0, 0, 0, "法人資料不足", "未取得正式三大法人資料，暫不對籌碼給分。")
    change = technical.change_pct
    volume_ratio = technical.volume_ratio
    trend = technical.trend_score
    score = 0
    if change > 1.2 and volume_ratio >= 1.15 and trend >= 60:
        score = 5
        bias = "量價推估偏多"
        summary = f"未取得正式三大法人資料；以量價推估，股價上漲 {change:.2f}% 且量能比 {volume_ratio:.2f}，籌碼面暫視為偏多觀察。"
    elif change < -1.2 and volume_ratio >= 1.15:
        score = -5
        bias = "量價推估偏空"
        summary = f"未取得正式三大法人資料；股價下跌 {change:.2f}% 且量能比 {volume_ratio:.2f}，需留意可能有賣壓。"
    else:
        bias = "籌碼中性"
        summary = f"未取得正式三大法人資料；量能比 {volume_ratio:.2f}，暫不將籌碼列為主要加分或扣分。"
    return InstitutionalFlowProfile(stock.symbol, stock.name, technical.latest_date, "Fallback Flow Model", 0, 0, 0, 0, score, bias, summary)


def load_institutional_flows(stocks: list[StockMeta], technical_profiles: dict[str, TechnicalProfile]) -> dict[str, InstitutionalFlowProfile]:
    official: dict[str, InstitutionalFlowProfile] = {}
    for date_text in _trading_dates(max_days=5):
        try:
            official = _fetch_twse_t86_for_date(date_text)
            if official:
                break
        except Exception:
            continue

    result: dict[str, InstitutionalFlowProfile] = {}
    for stock in stocks:
        if stock.symbol in official:
            result[stock.symbol] = official[stock.symbol]
        else:
            result[stock.symbol] = _fallback_profile(stock, technical_profiles.get(stock.symbol))
    return result
