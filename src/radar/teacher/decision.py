"""Stock teacher decision engine."""

from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from radar.core.indicators import analyze_prices
from radar.core.market_data import fetch_price_series
from radar.data.stock_master import StockInfo, ai_universe, register_custom_stock, resolve_stock
from radar.data.user_store import load_portfolio, load_watchlist


GENERIC_NAME_PREFIXES = ("待識別", "自訂個股")


def _taipei_now() -> datetime:
    """Return timezone-aware current time in Taiwan.

    Streamlit Cloud servers do not necessarily run in Taiwan time. Earlier
    versions used server local time, so a Taiwan after-hours session could be
    shown as intraday. This function forces Asia/Taipei for both local and web.
    """
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("Asia/Taipei"))
        except Exception:
            pass
    return datetime.now(timezone.utc) + timedelta(hours=8)


def trading_status(now: datetime | None = None) -> dict:
    now = now or _taipei_now()
    if now.tzinfo is None:
        tw_now = now
    else:
        try:
            tw_now = now.astimezone(ZoneInfo("Asia/Taipei")) if ZoneInfo is not None else now.astimezone(timezone(timedelta(hours=8)))
        except Exception:
            tw_now = now

    weekday = tw_now.weekday()
    is_trade_day = weekday < 5
    hour = tw_now.hour + tw_now.minute / 60

    if not is_trade_day:
        session = "非交易日"
    elif hour < 8.5:
        session = "盤前"
    elif hour < 9:
        session = "盤前集合競價"
    elif hour <= 13.5:
        session = "盤中"
    elif hour <= 14.5:
        session = "收盤後整理"
    else:
        session = "盤後"

    return {
        "date": tw_now.date().isoformat(),
        "time": tw_now.strftime("%H:%M"),
        "timezone": "Asia/Taipei",
        "weekday": "一二三四五六日"[weekday],
        "session": session,
        "is_trade_day": is_trade_day,
    }


def _stock_with_discovered_name(stock: StockInfo, prices: dict) -> StockInfo:
    discovered_name = str(prices.get("name") or stock.name).strip()
    market = str(prices.get("market") or stock.market or "TW")
    if stock.name.startswith(GENERIC_NAME_PREFIXES) and discovered_name and not discovered_name.startswith(GENERIC_NAME_PREFIXES):
        updated = StockInfo(stock.symbol, discovered_name, market, stock.theme or "自動新增")
        return register_custom_stock(updated)
    if stock.market != market and stock.theme == "自動新增":
        updated = StockInfo(stock.symbol, stock.name, market, stock.theme)
        return register_custom_stock(updated)
    return stock


def _score(stock: StockInfo, tech: dict) -> tuple[int, list[str]]:
    score = 50
    reasons = []
    close = tech["close"]
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    macd_info = tech["macd"]
    macd_status = macd_info["hist_status"]
    zero_axis_status = macd_info.get("zero_axis_status", "")
    rsi = tech.get("rsi") or 50
    vr = tech.get("volume_ratio") or 1
    if ma20 and close > ma20:
        score += 10; reasons.append("股價站上 MA20")
    if ma60 and close > ma60:
        score += 8; reasons.append("股價站上 MA60")
    if zero_axis_status == "即將從0軸翻正":
        score += 14; reasons.append("MACD 即將從 0 軸翻正，波段轉強機率提高")
    elif zero_axis_status == "剛從0軸翻正":
        score += 16; reasons.append("MACD 剛從 0 軸翻正，趨勢正式轉強")
    elif zero_axis_status == "0軸上方延續":
        score += 10; reasons.append("MACD 站在 0 軸上方延續")
    elif macd_status in {"柱狀體剛翻正", "柱狀體已翻正延續"}:
        score += 8; reasons.append(f"MACD {macd_status}")
    elif macd_status == "柱狀體即將翻正":
        score += 5; reasons.append("MACD 柱狀體即將翻正")
    if 45 <= rsi <= 70:
        score += 8; reasons.append(f"RSI {rsi}，位階合理")
    elif rsi > 78:
        score -= 10; reasons.append(f"RSI {rsi} 偏熱，不追高")
    elif rsi < 30:
        score -= 3; reasons.append(f"RSI {rsi} 偏弱，需等待止跌確認")
    if vr and 1.05 <= vr <= 1.8:
        score += 8; reasons.append(f"量能比 {vr}，量能溫和放大")
    elif vr and vr > 2.2:
        score -= 6; reasons.append(f"量能比 {vr} 過熱，留意短線震盪")
    if stock.theme in {"AI伺服器", "半導體", "PCB", "散熱", "封測", "IC設計"}:
        score += 6; reasons.append(f"屬於 {stock.theme} 主題，具產業關注度")
    return max(0, min(100, score)), reasons


def _data_trust(prices: dict, sample_size: int) -> dict:
    """Evaluate whether this stock can receive actionable recommendations.

    v3.4.0 upgrades data trust: official TWSE / TPEx confirmation is
    preferred for latest daily close. Yahoo Finance remains the chart/history
    fallback, but if official confirmation is missing, recommendation confidence
    is lowered.
    """
    latest_date = str(prices.get("latest_date") or "")
    source = str(prices.get("source") or "unknown")
    quality = str(prices.get("data_quality") or "unknown")
    warnings: list[str] = []

    official_snapshot = prices.get("official_snapshot") or {}
    official_confirmed = bool(prices.get("official_confirmed"))
    if quality == "fallback" or source == "fallback":
        warnings.append("價格資料為 fallback，僅供觀察")
    elif not official_confirmed:
        warnings.append("尚未取得 TWSE / TPEx 官方盤後確認，僅能降級參考")
    try:
        age_days = (date.today() - date.fromisoformat(latest_date)).days
    except Exception:
        age_days = 999
        warnings.append("無法判斷資料日期")
    if age_days > 7:
        warnings.append(f"價格資料距今 {age_days} 天，禁止列為 A 級買進")
    if sample_size < 60:
        warnings.append("日線樣本不足 60 根，技術指標可信度不足")

    actionable = not warnings
    status = "可作為操作參考" if actionable else "資料不足，僅能觀察"
    return {
        "status": status,
        "actionable": actionable,
        "latest_date": latest_date,
        "source": source,
        "quality": quality,
        "official_confirmed": official_confirmed,
        "official_source": official_snapshot.get("source") or prices.get("official_source") or "未取得",
        "official_message": official_snapshot.get("message", ""),
        "age_days": age_days,
        "warnings": warnings,
    }


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
    stock = _stock_with_discovered_name(stock, prices)
    tech = analyze_prices(prices)
    score, reasons = _score(stock, tech)
    trust = _data_trust(prices, len(prices.get("prices", [])))

    # Data guardrails: do not allow actionable A-grade recommendation when
    # price data is fallback, stale, or too short. This protects the user from
    # wrong recommendation caused by old/invalid data.
    if not trust["actionable"]:
        score = min(score, 64)
        reasons = trust["warnings"] + reasons

    label, setup, grade = _decision(score, tech)
    if not trust["actionable"] and grade in {"A", "B"}:
        label, setup, grade = "只觀察", "資料不足不給買進", "C"

    confidence = min(96, max(40, score + (0 if trust["actionable"] else -15)))
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "label": stock.label,
        "theme": stock.theme,
        "price_source": prices["source"],
        "data_quality": prices.get("data_quality", "unknown"),
        "official_confirmed": bool(prices.get("official_confirmed")),
        "official_snapshot": prices.get("official_snapshot", {}),
        "data_trust": trust,
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


def _portfolio_advice(card: dict, pnl_pct: float) -> str:
    """Teacher-style holding advice with concrete scenarios."""
    tech = card["tech"]
    close = tech["close"]
    low = tech["support_low"]
    high = tech["support_high"]
    breakout = tech["breakout"]
    stop = tech["stop"]
    trim1 = tech["trim1"]
    trim2 = tech["trim2"]
    trust = card.get("data_trust") or {}
    trust_note = "資料可信，可納入今日操作參考" if trust.get("actionable") else "資料可信度不足，先降級為觀察，不做積極加碼"

    if card["score"] >= 78 and pnl_pct >= -5:
        stance = "偏續抱"
        plan = (
            f"目前股價 {close:.2f}，若未跌破失效價 {stop:.2f}，老師看法是續抱優先；"
            f"若放量突破 {breakout:.2f}，可視為波段轉強訊號。"
        )
    elif pnl_pct < -8 or card["score"] < 55:
        stance = "先檢討"
        plan = (
            f"目前分數或損益結構不佳，若跌破 {stop:.2f}，應先減碼控風險；"
            f"不建議用攤平取代停損紀律。若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向調節。"
        )
    elif low <= close <= high * 1.04:
        stance = "可觀察加碼"
        plan = (
            f"股價位於可觀察區附近，若 {low:.2f}～{high:.2f} 守穩且量能沒有失控，"
            f"可小幅加碼；跌破 {stop:.2f} 則停止加碼並檢討。"
        )
    else:
        stance = "等待確認"
        plan = (
            f"現價 {close:.2f} 尚未形成高勝率加碼點，等待突破 {breakout:.2f} 或回測 "
            f"{low:.2f}～{high:.2f} 守穩再行動。"
        )
    return f"{stance}｜{plan}｜{trust_note}。"


def _portfolio_coach(cards_by_symbol: dict[str, dict]) -> dict:
    holdings = load_portfolio()
    rows = []
    total_cost = 0.0
    total_value = 0.0
    theme_value: dict[str, float] = {}
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
        theme_value[card.get("theme", "其他")] = theme_value.get(card.get("theme", "其他"), 0.0) + value
        pnl = value - base
        pnl_pct = pnl / base * 100 if base else 0
        advice = _portfolio_advice(card, pnl_pct)
        rows.append({"stock": card["label"], "shares": shares, "cost": cost, "value": round(value, 0), "pnl": round(pnl, 0), "pnl_pct": round(pnl_pct, 2), "advice": advice, "card": card})
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    summary = "目前尚未建立持股；可先從今日可買與等待突破名單中挑選 1～3 檔觀察。"
    if rows:
        strongest = sorted(rows, key=lambda r: r["card"]["score"], reverse=True)[:2]
        weakest = sorted(rows, key=lambda r: r["card"]["score"])[:2]
        top_theme = ""
        if total_value:
            theme, val = max(theme_value.items(), key=lambda kv: kv[1])
            concentration = val / total_value * 100
            top_theme = f"目前最大曝險族群為 {theme}，約占 {concentration:.1f}%。"
        summary = (
            f"持股總教練：目前組合總損益 {total_pnl:.0f}（{total_pnl_pct:.2f}%）。"
            f"{top_theme} 策略上以汰弱留強為主，分數高且未跌破失效價的部位續抱，"
            f"分數低或資料可信度不足的部位不加碼。優先續抱："
            f"{'、'.join(r['stock'] for r in strongest)}；優先檢討：{'、'.join(r['stock'] for r in weakest)}。"
        )
    return {"rows": rows, "total_cost": round(total_cost, 0), "total_value": round(total_value, 0), "total_pnl": round(total_pnl, 0), "total_pnl_pct": round(total_pnl_pct, 2), "summary": summary}

def _macd_zero_axis_candidates(cards: list[dict]) -> list[dict]:
    """Return only actionable zero-axis MACD turn candidates.

    v3.3.0 product rule:
    The MACD observation list should focus on stocks whose MACD/DIF is moving
    from below zero to above zero. Histogram green-to-red alone is not enough.
    If price data is fallback/stale/too short, the stock is not included.
    """
    priority_map = {
        "剛從0軸翻正": 0,
        "即將從0軸翻正": 1,
    }
    candidates = [
        c for c in cards
        if c.get("data_trust", {}).get("actionable")
        and c["tech"]["macd"].get("zero_axis_status", "") in priority_map
    ]

    def rank(card: dict) -> tuple[int, float, int]:
        status = card["tech"]["macd"].get("zero_axis_status", "")
        # Prefer true fresh zero-axis turns, then higher score, then healthier RSI.
        rsi = card["tech"].get("rsi") or 50
        return (priority_map.get(status, 9), abs(rsi - 55), -card["score"])

    return sorted(candidates, key=rank)[:10]


def run_teacher_pipeline() -> dict:
    universe = ai_universe()
    cards = [build_decision_card(stock) for stock in universe]
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    cards.sort(key=lambda x: (grade_order.get(x["grade"], 9), -x["score"]))
    buy = [c for c in cards if c["grade"] == "A"][:5]
    wait = [c for c in cards if c["grade"] == "B"][:8]
    avoid = [c for c in cards if c["grade"] == "D"][:8]
    macd_zero = _macd_zero_axis_candidates(cards)
    # v3.3.0: MACD observation is unified with zero-axis MACD.
    macd = macd_zero
    cards_by_symbol = {c["symbol"]: c for c in cards}
    watch_items = []
    for item in load_watchlist():
        try:
            stock = resolve_stock(str(item.get("symbol") or item.get("name") or ""))
            watch_items.append(cards_by_symbol.get(stock.symbol) or build_decision_card(stock))
        except Exception:
            continue
    official_count = sum(1 for c in cards if c.get("official_confirmed"))
    yahoo_count = sum(1 for c in cards if c.get("price_source") == "Yahoo Finance")
    fallback_count = sum(1 for c in cards if c.get("data_quality") == "fallback")
    data_source_summary = {
        "official_confirmed": official_count,
        "yahoo_only": yahoo_count,
        "fallback": fallback_count,
        "description": "TWSE / TPEx 官方盤後資料優先確認最新價；Yahoo Finance 提供歷史線圖與 fallback。",
    }
    return {
        "version": "3.4.0",
        "trading_status": trading_status(),
        "market_view": "偏多但不追高" if buy or wait else "中性偏保守",
        "teacher_summary": "今天先找可執行買點，不追情緒單；優先使用 TWSE / TPEx 官方盤後資料確認最新價，Yahoo 作為歷史線圖與 fallback；MACD 只看 DIF 從 0 軸下方即將或剛轉強。",
        "buy_list": buy,
        "wait_list": wait,
        "avoid_list": avoid,
        "macd_list": macd,
        "macd_zero_axis_list": macd_zero,
        "watchlist_analysis": watch_items,
        "portfolio_coach": _portfolio_coach(cards_by_symbol),
        "data_source_summary": data_source_summary,
        "all_cards": cards,
    }
