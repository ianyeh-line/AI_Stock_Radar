"""User workspace helpers for watchlist and portfolio."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from radar.models.domain import DecisionCard, StockMeta, TechnicalProfile

USER_WATCHLIST_PATH = Path("config/user_watchlist.json")
PORTFOLIO_PATH = Path("config/portfolio.json")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_symbol(text: str) -> str:
    cleaned = text.strip().upper().replace(" ", "")
    match = re.search(r"\d{4}", cleaned)
    if match:
        return match.group(0)
    return cleaned


def default_yahoo_symbol(symbol: str) -> str:
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        return symbol
    return f"{symbol}.TW"


def make_custom_stock(symbol: str, name: Optional[str] = None) -> StockMeta:
    clean_symbol = normalize_symbol(symbol)
    clean_name = (name or f"自訂觀察{clean_symbol}").strip()
    return StockMeta(
        symbol=clean_symbol,
        name=clean_name,
        sector="個人觀察",
        theme=["Personal Watchlist", "Swing Trading"],
        yahoo_symbol=default_yahoo_symbol(clean_symbol),
        pm_view="使用者指定觀察個股，AI 以技術面與新聞關聯度進行波段評估。",
        base_priority=5,
        is_custom=True,
    )


def load_user_watchlist() -> list[dict[str, Any]]:
    data = _read_json(USER_WATCHLIST_PATH, [])
    if not isinstance(data, list):
        return []
    return data


def save_user_watchlist(items: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for item in items:
        symbol = normalize_symbol(str(item.get("symbol", "")))
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        normalized.append({"symbol": symbol, "name": str(item.get("name") or f"自訂觀察{symbol}")})
    _write_json(USER_WATCHLIST_PATH, normalized)


def add_user_watchlist_item(symbol: str, name: Optional[str] = None) -> None:
    items = load_user_watchlist()
    stock = make_custom_stock(symbol, name)
    if stock.symbol not in {normalize_symbol(str(item.get("symbol", ""))) for item in items}:
        items.append({"symbol": stock.symbol, "name": stock.name})
    save_user_watchlist(items)


def remove_user_watchlist_item(symbol: str) -> None:
    clean_symbol = normalize_symbol(symbol)
    items = [item for item in load_user_watchlist() if normalize_symbol(str(item.get("symbol", ""))) != clean_symbol]
    save_user_watchlist(items)


def load_portfolio() -> list[dict[str, Any]]:
    data = _read_json(PORTFOLIO_PATH, [])
    if not isinstance(data, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in data:
        symbol = normalize_symbol(str(item.get("symbol", "")))
        if not symbol:
            continue
        try:
            shares = float(item.get("shares", 0) or 0)
            avg_cost = float(item.get("avg_cost", 0) or 0)
        except Exception:
            shares = 0.0
            avg_cost = 0.0
        cleaned.append(
            {
                "symbol": symbol,
                "name": str(item.get("name") or f"自訂觀察{symbol}"),
                "shares": shares,
                "avg_cost": avg_cost,
                "note": str(item.get("note", "")),
            }
        )
    return cleaned


def save_portfolio(items: list[dict[str, Any]]) -> None:
    normalized: dict[str, dict[str, Any]] = {}
    for item in items:
        symbol = normalize_symbol(str(item.get("symbol", "")))
        if not symbol:
            continue
        normalized[symbol] = {
            "symbol": symbol,
            "name": str(item.get("name") or f"自訂觀察{symbol}"),
            "shares": float(item.get("shares", 0) or 0),
            "avg_cost": float(item.get("avg_cost", 0) or 0),
            "note": str(item.get("note", "")),
        }
    _write_json(PORTFOLIO_PATH, list(normalized.values()))


def add_or_update_holding(symbol: str, name: Optional[str], shares: float, avg_cost: float, note: str = "") -> None:
    clean_symbol = normalize_symbol(symbol)
    items = load_portfolio()
    updated = False
    for item in items:
        if normalize_symbol(str(item.get("symbol", ""))) == clean_symbol:
            item.update({"name": name or item.get("name") or f"自訂觀察{clean_symbol}", "shares": shares, "avg_cost": avg_cost, "note": note})
            updated = True
            break
    if not updated:
        items.append({"symbol": clean_symbol, "name": name or f"自訂觀察{clean_symbol}", "shares": shares, "avg_cost": avg_cost, "note": note})
    save_portfolio(items)


def remove_holding(symbol: str) -> None:
    clean_symbol = normalize_symbol(symbol)
    save_portfolio([item for item in load_portfolio() if normalize_symbol(str(item.get("symbol", ""))) != clean_symbol])


def resolve_stock_query(query: str, stocks: list[StockMeta]) -> Optional[StockMeta]:
    text = query.strip()
    if not text:
        return None
    clean_symbol = normalize_symbol(text)
    for stock in stocks:
        if stock.symbol == clean_symbol or stock.name == text or stock.display_name == text:
            return stock
    if re.fullmatch(r"\d{4}", clean_symbol):
        return make_custom_stock(clean_symbol)
    return None


def build_portfolio_analysis(portfolio: list[dict[str, Any]], cards: list[DecisionCard], profiles: dict[str, TechnicalProfile]) -> list[dict[str, Any]]:
    card_map = {card.symbol: card for card in cards}
    rows: list[dict[str, Any]] = []
    for holding in portfolio:
        symbol = normalize_symbol(str(holding.get("symbol", "")))
        card = card_map.get(symbol)
        profile = profiles.get(symbol)
        latest = float(card.latest_close if card else profile.latest_close if profile else 0)
        shares = float(holding.get("shares", 0) or 0)
        avg_cost = float(holding.get("avg_cost", 0) or 0)
        cost_value = shares * avg_cost
        market_value = shares * latest
        pnl = market_value - cost_value
        pnl_pct = 0.0 if cost_value == 0 else pnl / cost_value * 100
        decision = card.decision if card else "等待"
        if decision == "波段買進" and pnl_pct >= 0:
            action = "續抱；若回測支撐不破，可評估分批加碼。"
        elif decision == "波段買進":
            action = "續抱觀察；以成本與 MA60 作為防守線。"
        elif decision == "波段觀察":
            action = "續抱但不追高；等待突破或量能確認。"
        elif decision == "等待":
            action = "不新增部位；用 MA20/MA60 與成本控管。"
        else:
            action = "反彈優先減碼或降低曝險。"
        rows.append(
            {
                "symbol": symbol,
                "name": holding.get("name") or (card.name if card else symbol),
                "display_name": f"{symbol} {holding.get('name') or (card.name if card else symbol)}",
                "sector": card.sector if card else "個人持股",
                "shares": shares,
                "avg_cost": avg_cost,
                "latest_close": round(latest, 2),
                "market_value": round(market_value, 0),
                "cost_value": round(cost_value, 0),
                "pnl": round(pnl, 0),
                "pnl_pct": round(pnl_pct, 2),
                "decision": decision,
                "radar_score": card.radar_score if card else None,
                "confidence": card.confidence if card else None,
                "breakout_price": card.breakout_price if card else None,
                "pullback_low": card.pullback_low if card else None,
                "pullback_high": card.pullback_high if card else None,
                "reduce_price": card.reduce_price if card else None,
                "stop_loss_price": card.stop_loss_price if card else None,
                "entry_condition": card.entry_condition if card else "需重新產生 Radar 後提供進場條件。",
                "reduce_condition": card.reduce_condition if card else "需重新產生 Radar 後提供減碼條件。",
                "invalidation_condition": card.invalidation_condition if card else "需重新產生 Radar 後提供失效條件。",
                "price_source": card.price_source if card else (profile.price_source if profile else "N/A"),
                "latest_date": profile.latest_date if profile else "N/A",
                "action": action,
                "note": holding.get("note", ""),
            }
        )
    return rows



def build_portfolio_coach(portfolio_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a macro portfolio diagnosis in a stock-teacher style."""
    if not portfolio_rows:
        return {
            "headline": "目前尚未建立個人持股，AI 無法提供組合層級建議。",
            "summary": "請先輸入持股股數與成本，系統會從整體損益、部位集中度、持股評級與波段風險產生宏觀建議。",
            "total_market_value": 0,
            "total_cost_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "position_count": 0,
            "risk_level": "N/A",
            "portfolio_style": "尚未建立",
            "capital_policy": "尚未輸入持股，暫以現金與觀察清單為主，不做組合加碼建議。",
            "core_holdings": [],
            "add_candidates": [],
            "reduce_candidates": [],
            "sector_concentration": [],
            "teacher_actions": [],
            "rebalance_plan": [],
            "risk_alerts": [],
            "concentration": [],
        }

    total_market = sum(float(row.get("market_value", 0) or 0) for row in portfolio_rows)
    total_cost = sum(float(row.get("cost_value", 0) or 0) for row in portfolio_rows)
    total_pnl = total_market - total_cost
    total_pct = 0.0 if total_cost == 0 else total_pnl / total_cost * 100
    enriched: list[dict[str, Any]] = []
    for row in portfolio_rows:
        weight = 0.0 if total_market == 0 else float(row.get("market_value", 0) or 0) / total_market * 100
        enriched.append({**row, "portfolio_weight": round(weight, 1)})

    high_weight = [row for row in enriched if row["portfolio_weight"] >= 35]
    weak_names = [row for row in enriched if row.get("decision") == "減碼/避開" or (row.get("radar_score") or 0) < 58]
    strong_names = [row for row in enriched if row.get("decision") in {"波段買進", "波段觀察"} and (row.get("radar_score") or 0) >= 70]

    if high_weight or len(weak_names) >= max(1, len(enriched) // 2):
        risk_level = "偏高"
    elif total_pct <= -8:
        risk_level = "中高"
    else:
        risk_level = "可控"

    if strong_names and not weak_names:
        style = "順勢波段持股，可續抱但仍需設定減碼線。"
        headline = "持股結構偏健康，重點是照價格紀律續抱與分批保護獲利。"
    elif weak_names:
        style = "持股需要汰弱留強，避免資金卡在低效率標的。"
        headline = "持股組合有需要調整的標的，優先處理弱勢與高集中度部位。"
    else:
        style = "中性持股，等待下一個明確買點或減碼點。"
        headline = "持股組合暫無極端風險，但也缺乏高信念主攻標的。"

    teacher_actions: list[str] = []
    if total_pct >= 10:
        teacher_actions.append("整體已有明顯獲利，建議把每檔股票的第一減碼價設為紀律線，避免獲利回吐。")
    elif total_pct <= -8:
        teacher_actions.append("整體虧損擴大，應停止攤平弱勢股，先確認每檔是否仍符合波段假設。")
    else:
        teacher_actions.append("整體損益尚在可控範圍，重點放在汰弱留強與提高資金效率。")

    if high_weight:
        names = "、".join(f"{row['display_name']} {row['portfolio_weight']}%" for row in high_weight[:3])
        teacher_actions.append(f"部位集中度偏高：{names}。單一股票若超過 35%，不宜再加碼，優先用減碼價管理風險。")
    if strong_names:
        names = "、".join(row["display_name"] for row in strong_names[:3])
        teacher_actions.append(f"可續抱觀察：{names}。這些標的仍有波段條件，但加碼需等拉回區或突破確認。")
    if weak_names:
        names = "、".join(row["display_name"] for row in weak_names[:3])
        teacher_actions.append(f"優先檢討：{names}。若反彈無量或跌破失效價，先降低曝險。")

    rebalance_plan: list[str] = []
    for row in sorted(enriched, key=lambda x: (x.get("radar_score") or 0), reverse=True)[:3]:
        rebalance_plan.append(
            f"{row['display_name']}：權重 {row['portfolio_weight']}%，Radar {row.get('radar_score')}，建議：{row.get('action')}"
        )
    for row in weak_names[:3]:
        rebalance_plan.append(
            f"{row['display_name']}：若跌破 {row.get('stop_loss_price')} 或反彈無量，優先減碼；不要用攤平取代停損紀律。"
        )

    risk_alerts = [
        "不要讓單一題材或單一股票決定整體損益。",
        "若大盤或美股科技股轉弱，先降低高 beta AI 概念股曝險。",
        "持股加碼只在高分標的拉回支撐或突破確認時進行，不用虧損攤平當作策略。",
    ]

    concentration = [
        {
            "display_name": row["display_name"],
            "weight": row["portfolio_weight"],
            "decision": row.get("decision"),
            "radar_score": row.get("radar_score"),
        }
        for row in sorted(enriched, key=lambda x: x["portfolio_weight"], reverse=True)
    ]

    sector_weight: dict[str, float] = {}
    for row in enriched:
        sector = str(row.get("sector") or "未分類")
        sector_weight[sector] = sector_weight.get(sector, 0.0) + float(row.get("portfolio_weight", 0) or 0)
    sector_concentration = [
        {"sector": sector, "weight": round(weight, 1)}
        for sector, weight in sorted(sector_weight.items(), key=lambda item: item[1], reverse=True)
    ]

    core_holdings = [row for row in enriched if row.get("decision") in {"波段買進", "波段觀察"} and (row.get("radar_score") or 0) >= 70]
    reduce_candidates = [row for row in enriched if row.get("decision") == "減碼/避開" or (row.get("radar_score") or 0) < 58 or float(row.get("pnl_pct", 0) or 0) <= -8]
    add_candidates = [row for row in core_holdings if row.get("portfolio_weight", 0) < 25 and float(row.get("pnl_pct", 0) or 0) >= -3]

    if risk_level in {"偏高", "中高"}:
        capital_policy = "先降風險再談加碼：新資金暫停追高，優先處理弱勢持股與過度集中部位。"
    elif core_holdings:
        capital_policy = "可保留部分機動資金，僅在強勢持股回測支撐不破或突破確認時分批加碼。"
    else:
        capital_policy = "組合缺乏高信念核心，現金比重宜提高，等待 A/B 級標的出現。"

    return {
        "headline": headline,
        "summary": style,
        "total_market_value": round(total_market, 0),
        "total_cost_value": round(total_cost, 0),
        "total_pnl": round(total_pnl, 0),
        "total_pnl_pct": round(total_pct, 2),
        "position_count": len(portfolio_rows),
        "risk_level": risk_level,
        "portfolio_style": style,
        "capital_policy": capital_policy,
        "core_holdings": [row["display_name"] for row in core_holdings[:5]],
        "add_candidates": [row["display_name"] for row in add_candidates[:5]],
        "reduce_candidates": [row["display_name"] for row in reduce_candidates[:5]],
        "teacher_actions": teacher_actions,
        "rebalance_plan": rebalance_plan,
        "risk_alerts": risk_alerts,
        "concentration": concentration,
        "sector_concentration": sector_concentration,
    }
