"""Stock teacher decision engine."""

from __future__ import annotations

from datetime import datetime

from radar.core.indicators import analyze_prices
from radar.core.market_data import fetch_price_series
from radar.data.stock_master import StockInfo, ai_universe, resolve_stock
from radar.data.user_store import load_portfolio, load_watchlist


def trading_status(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    weekday = now.weekday()
    is_trade_day = weekday < 5
    hour = now.hour + now.minute / 60
    if not is_trade_day:
        session = "非交易日"
    elif hour < 9:
        session = "盤前"
    elif hour <= 13.5:
        session = "盤中"
    else:
        session = "盤後"
    return {"date": now.date().isoformat(), "weekday": "一二三四五六日"[weekday], "session": session, "is_trade_day": is_trade_day}


def _score(stock: StockInfo, tech: dict) -> tuple[int, list[str]]:
    score = 50
    reasons = []
    close = tech["close"]
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    macd_status = tech["macd"]["status"]
    rsi = tech.get("rsi") or 50
    vr = tech.get("volume_ratio") or 1
    if ma20 and close > ma20:
        score += 10; reasons.append("股價站上 MA20")
    if ma60 and close > ma60:
        score += 8; reasons.append("股價站上 MA60")
    if macd_status in {"剛翻正", "已翻正延續"}:
        score += 12; reasons.append(f"MACD {macd_status}")
    elif macd_status == "即將翻正":
        score += 8; reasons.append("MACD 即將翻正")
    if 45 <= rsi <= 70:
        score += 8; reasons.append(f"RSI {rsi}，位階合理")
    elif rsi > 78:
        score -= 10; reasons.append(f"RSI {rsi} 偏熱，不追高")
    if vr and 1.05 <= vr <= 1.8:
        score += 8; reasons.append(f"量能比 {vr}，量能溫和放大")
    elif vr and vr > 2.2:
        score -= 6; reasons.append(f"量能比 {vr} 過熱，留意短線震盪")
    if stock.theme in {"AI伺服器", "半導體", "PCB", "散熱", "封測", "IC設計"}:
        score += 6; reasons.append(f"屬於 {stock.theme} 主題，具產業關注度")
    return max(0, min(100, score)), reasons


def _decision(score: int, tech: dict) -> tuple[str, str, str]:
    close = tech["close"]
    low = tech["support_low"]
    high = tech["support_high"]
    breakout = tech["breakout"]
    if score >= 78 and low <= close <= high * 1.04:
        return "今日可買", "拉回買進", "A"
    if score >= 78 and close < breakout:
        return "等待突破", "突破確認買", "B"
    if score >= 65:
        return "只觀察", "等待拉回或轉強", "C"
    return "避免", "暫不操作", "D"


def _action_text(label: str, tech: dict) -> str:
    close = tech["close"]
    low = tech["support_low"]
    high = tech["support_high"]
    breakout = tech["breakout"]
    stop = tech["stop"]
    trim1 = tech["trim1"]
    trim2 = tech["trim2"]
    if label == "今日可買":
        return f"可在 {low:.2f}～{high:.2f} 分批，跌破 {stop:.2f} 失效；若放量突破 {breakout:.2f} 可續抱。"
    if label == "等待突破":
        if close > high:
            return f"現價 {close:.2f} 已高於支撐區 {low:.2f}～{high:.2f}，不追高；等突破 {breakout:.2f} 或回測支撐區守穩。"
        return f"等待站上 {breakout:.2f}，或回測 {low:.2f}～{high:.2f} 守穩再評估。"
    if label == "只觀察":
        return f"尚未形成高勝率買點；站回 {high:.2f} 並量能改善才提高評級，跌破 {stop:.2f} 轉弱。"
    return f"暫不建立新部位；若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向減碼或避開。"


def build_decision_card(stock: StockInfo) -> dict:
    prices = fetch_price_series(stock)
    tech = analyze_prices(prices)
    score, reasons = _score(stock, tech)
    label, setup, grade = _decision(score, tech)
    confidence = min(96, max(45, score + (0 if prices["source"] == "Yahoo Finance" else -12)))
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "label": stock.label,
        "theme": stock.theme,
        "price_source": prices["source"],
        "latest_date": prices["latest_date"],
        "prices": prices["prices"],
        "tech": tech,
        "score": score,
        "decision": label,
        "setup": setup,
        "grade": grade,
        "confidence": confidence,
        "reasons": reasons,
        "action": _action_text(label, tech),
        "risk": f"跌破 {tech['stop']:.2f} 代表波段結構轉弱，不建議用攤平取代停損紀律。",
    }


def _portfolio_coach(cards_by_symbol: dict[str, dict]) -> dict:
    holdings = load_portfolio()
    rows = []
    total_cost = 0.0
    total_value = 0.0
    for item in holdings:
        try:
            stock = resolve_stock(str(item.get("symbol") or item.get("name") or ""))
        except Exception:
            continue
        card = cards_by_symbol.get(stock.symbol) or build_decision_card(stock)
        shares = float(item.get("shares", 0) or 0)
        cost = float(item.get("cost", 0) or 0)
        value = shares * card["tech"]["close"]
        base = shares * cost
        total_cost += base
        total_value += value
        pnl = value - base
        pnl_pct = pnl / base * 100 if base else 0
        if card["score"] >= 75 and pnl_pct >= -5:
            advice = "可續抱，若回測不破失效價仍可觀察加碼。"
        elif pnl_pct < -8 or card["score"] < 55:
            advice = "需檢討部位，若跌破失效價應先減碼，不建議攤平。"
        else:
            advice = "維持觀察，等待轉強或量能確認。"
        rows.append({"stock": card["label"], "shares": shares, "cost": cost, "value": round(value, 0), "pnl": round(pnl, 0), "pnl_pct": round(pnl_pct, 2), "advice": advice, "card": card})
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    summary = "目前尚未建立持股；可先從今日可買與等待突破名單中挑選 1～3 檔觀察。"
    if rows:
        summary = "持股總教練：以汰弱留強為主，續抱強勢且未跌破失效價的部位，弱勢股不建議用攤平取代停損。"
    return {"rows": rows, "total_cost": round(total_cost, 0), "total_value": round(total_value, 0), "total_pnl": round(total_pnl, 0), "total_pnl_pct": round(total_pnl_pct, 2), "summary": summary}


def run_teacher_pipeline() -> dict:
    universe = ai_universe()
    cards = [build_decision_card(stock) for stock in universe]
    cards.sort(key=lambda x: (x["grade"], -x["score"]))
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    cards.sort(key=lambda x: (grade_order.get(x["grade"], 9), -x["score"]))
    buy = [c for c in cards if c["grade"] == "A"][:5]
    wait = [c for c in cards if c["grade"] == "B"][:8]
    avoid = [c for c in cards if c["grade"] == "D"][:8]
    macd = sorted(cards, key=lambda x: (0 if x["tech"]["macd"]["status"] in {"即將翻正", "剛翻正"} else 1, -x["score"]))[:10]
    cards_by_symbol = {c["symbol"]: c for c in cards}
    watch_items = []
    for item in load_watchlist():
        try:
            stock = resolve_stock(str(item.get("symbol") or item.get("name") or ""))
            watch_items.append(cards_by_symbol.get(stock.symbol) or build_decision_card(stock))
        except Exception:
            continue
    return {
        "version": "3.0.1",
        "trading_status": trading_status(),
        "market_view": "偏多但不追高" if buy or wait else "中性偏保守",
        "teacher_summary": "今天先找可執行買點，不追情緒單；只買到價標的，沒有到價就等待。",
        "buy_list": buy,
        "wait_list": wait,
        "avoid_list": avoid,
        "macd_list": macd,
        "watchlist_analysis": watch_items,
        "portfolio_coach": _portfolio_coach(cards_by_symbol),
        "all_cards": cards,
    }
