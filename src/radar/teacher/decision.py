"""Stock teacher decision engine.

v3.5.0 Data Source Truthfulness:
- Compare official TWSE / TPEx daily snapshot vs Yahoo daily data.
- Use the newest available data source as the price basis.
- Downgrade recommendations when data is stale, fallback, or insufficient.
"""

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


def _previous_trading_day(d: date) -> date:
    cur = d - timedelta(days=1)
    while cur.weekday() >= 5:
        cur -= timedelta(days=1)
    return cur


def expected_latest_trading_date(status: dict | None = None) -> dict:
    """Return the expected latest date for price recommendation.

    This is intentionally simple and weekend-aware. A full holiday calendar can
    be added later, but this already prevents the largest error: using an old
    date as if it were today's trading data.
    """
    status = status or trading_status()
    today = date.fromisoformat(status["date"])
    session = status.get("session", "")
    if not status.get("is_trade_day"):
        expected = _previous_trading_day(today)
        mode = "非交易日，使用前一交易日資料"
    elif session in {"盤前", "盤前集合競價"}:
        expected = _previous_trading_day(today)
        mode = "盤前，使用前一交易日收盤資料"
    else:
        expected = today
        mode = "盤中/盤後，優先使用今天可取得的最新資料；官方未更新時可採用較新的 Yahoo 資料"
    return {"expected_date": expected.isoformat(), "mode": mode, "session": session}


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
    reasons: list[str] = []
    close = tech["close"]
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    macd_info = tech["macd"]
    macd_status = macd_info["hist_status"]
    zero_axis_status = macd_info.get("zero_axis_status", "")
    rsi = tech.get("rsi") or 50
    vr = tech.get("volume_ratio") or 1
    if ma20 and close > ma20:
        score += 10
        reasons.append("股價站上 MA20")
    if ma60 and close > ma60:
        score += 8
        reasons.append("股價站上 MA60")
    if zero_axis_status == "即將從0軸翻正":
        score += 14
        reasons.append("MACD 即將從 0 軸翻正，波段轉強機率提高")
    elif zero_axis_status == "剛從0軸翻正":
        score += 16
        reasons.append("MACD 剛從 0 軸翻正，趨勢正式轉強")
    elif zero_axis_status == "0軸上方延續":
        score += 10
        reasons.append("MACD 站在 0 軸上方延續")
    elif macd_status in {"柱狀體剛翻正", "柱狀體已翻正延續"}:
        score += 8
        reasons.append(f"MACD {macd_status}")
    elif macd_status == "柱狀體即將翻正":
        score += 5
        reasons.append("MACD 柱狀體即將翻正")
    if 45 <= rsi <= 70:
        score += 8
        reasons.append(f"RSI {rsi}，位階合理")
    elif rsi > 78:
        score -= 10
        reasons.append(f"RSI {rsi} 偏熱，不追高")
    elif rsi < 30:
        score -= 3
        reasons.append(f"RSI {rsi} 偏弱，需等待止跌確認")
    if vr and 1.05 <= vr <= 1.8:
        score += 8
        reasons.append(f"量能比 {vr}，量能溫和放大")
    elif vr and vr > 2.2:
        score -= 6
        reasons.append(f"量能比 {vr} 過熱，留意短線震盪")
    if stock.theme in {"AI伺服器", "半導體", "PCB", "散熱", "封測", "IC設計"}:
        score += 6
        reasons.append(f"屬於 {stock.theme} 主題，具產業關注度")
    return max(0, min(100, score)), reasons


def _date_age(latest_date: str) -> int:
    try:
        return (date.today() - date.fromisoformat(latest_date)).days
    except Exception:
        return 999


def _data_trust(prices: dict, sample_size: int, status: dict | None = None) -> dict:
    latest_date = str(prices.get("latest_date") or "")
    source = str(prices.get("source") or "unknown")
    quality = str(prices.get("data_quality") or "unknown")
    policy = expected_latest_trading_date(status)
    expected_date = policy["expected_date"]
    warnings: list[str] = []
    notes: list[str] = []

    official_snapshot = prices.get("official_snapshot") or {}
    source_selection = prices.get("source_selection") or {}
    official_confirmed = bool(prices.get("official_confirmed"))
    official_lagging = bool(prices.get("official_lagging"))
    official_price_anomaly = bool(prices.get("official_price_anomaly"))

    if quality == "fallback" or source == "fallback":
        warnings.append("價格資料為 fallback，禁止列為買進，只能觀察")
    if sample_size < 60:
        warnings.append("日線樣本不足 60 根，技術指標可信度不足")

    try:
        latest_d = date.fromisoformat(latest_date)
        expected_d = date.fromisoformat(expected_date)
        if latest_d < expected_d:
            warnings.append(f"資料基準日 {latest_date} 早於預期最新交易日 {expected_date}，不給強推薦")
        elif latest_d == expected_d:
            notes.append(f"資料基準日符合預期最新交易日 {expected_date}")
        else:
            notes.append(f"資料基準日 {latest_date} 晚於預期交易日 {expected_date}，請確認是否為跨時區或交易日判斷差異")
    except Exception:
        warnings.append("無法判斷資料日期")

    if official_confirmed:
        notes.append("TWSE / TPEx 官方資料已確認最新價")
    elif official_price_anomaly:
        notes.append("官方快照與 Yahoo 最新價差異過大；為避免估值與圖表失真，本次採用 Yahoo 價格")
    elif official_lagging and latest_date:
        notes.append("官方資料尚未更新；已採用日期較新的 Yahoo 資料作為判斷基準")
    elif quality == "yahoo_with_undated_official":
        notes.append("官方資料未提供可驗證日期；保留 Yahoo 最新日線，不讓無日期官方資料覆蓋")
    elif quality != "fallback":
        notes.append("目前使用 Yahoo 最新可得日線，官方確認不足，信心略降")

    actionable = not warnings
    if actionable and official_price_anomaly:
        trust_level = "中"
        status_text = "Yahoo 價格採用，官方價差異常"
    elif actionable and official_lagging:
        trust_level = "中高"
        status_text = "Yahoo 較新，官方尚未更新"
    elif actionable and official_confirmed:
        trust_level = "高"
        status_text = "官方資料已確認，可作為操作參考"
    elif actionable:
        trust_level = "中"
        status_text = "Yahoo 最新資料可參考，但缺官方確認"
    else:
        trust_level = "低"
        status_text = "資料不足，僅能觀察"

    return {
        "status": status_text,
        "trust_level": trust_level,
        "actionable": actionable,
        "expected_latest_date": expected_date,
        "expected_policy": policy["mode"],
        "latest_date": latest_date,
        "source": source,
        "quality": quality,
        "official_confirmed": official_confirmed,
        "official_lagging": official_lagging,
        "official_price_anomaly": official_price_anomaly,
        "official_source": official_snapshot.get("source") or prices.get("official_source") or "未取得",
        "official_date": official_snapshot.get("date") or prices.get("official_date") or "未提供",
        "official_message": official_snapshot.get("message", ""),
        "yahoo_date": prices.get("yahoo_latest_date") or latest_date,
        "source_selection": source_selection,
        "age_days": _date_age(latest_date),
        "warnings": warnings,
        "notes": notes,
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


def build_decision_card(stock: StockInfo, status: dict | None = None) -> dict:
    status = status or trading_status()
    prices = fetch_price_series(stock)
    stock = _stock_with_discovered_name(stock, prices)
    tech = analyze_prices(prices)
    score, reasons = _score(stock, tech)
    trust = _data_trust(prices, len(prices.get("prices", [])), status)

    if not trust["actionable"]:
        score = min(score, 64)
        reasons = trust["warnings"] + reasons
    elif trust.get("official_price_anomaly"):
        score = min(100, max(0, score - 5))
        reasons = ["官方快照價格異常，採用 Yahoo 價格；信心略降"] + reasons
    elif trust.get("official_lagging") or not trust.get("official_confirmed"):
        score = min(100, max(0, score - 3))
        reasons = ["採用較新的 Yahoo 資料，官方尚未完全同步，信心略降"] + reasons

    label, setup, grade = _decision(score, tech)
    if not trust["actionable"] and grade in {"A", "B"}:
        label, setup, grade = "只觀察", "資料不足不給買進", "C"

    confidence_penalty = 0 if trust["actionable"] else -18
    if trust.get("official_price_anomaly"):
        confidence_penalty -= 6
    elif trust.get("official_lagging") or not trust.get("official_confirmed"):
        confidence_penalty -= 4
    confidence = min(96, max(40, score + confidence_penalty))
    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "label": stock.label,
        "theme": stock.theme,
        "price_source": prices["source"],
        "data_quality": prices.get("data_quality", "unknown"),
        "official_confirmed": bool(prices.get("official_confirmed")),
        "official_lagging": bool(prices.get("official_lagging")),
        "official_snapshot": prices.get("official_snapshot", {}),
        "source_selection": prices.get("source_selection", {}),
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

    if not trust.get("actionable"):
        return f"僅能觀察｜目前股價 {close:.2f}，但{trust_note}；若已持有，以跌破 {stop:.2f} 作為風險檢討線，不建議因帳面損益而盲目攤平。若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，可先降低部位風險。"

    if card["score"] >= 78 and pnl_pct >= -5:
        stance = "偏續抱"
        plan = f"目前股價 {close:.2f}，若未跌破失效價 {stop:.2f}，老師看法是續抱優先；若放量突破 {breakout:.2f}，可視為波段轉強訊號。"
    elif pnl_pct < -8 or card["score"] < 55:
        stance = "先檢討"
        plan = f"目前分數或損益結構不佳，若跌破 {stop:.2f}，應先減碼控風險；不建議用攤平取代停損紀律。若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向調節。"
    elif low <= close <= high * 1.04:
        stance = "可觀察加碼"
        plan = f"股價位於可觀察區附近，若 {low:.2f}～{high:.2f} 守穩且量能沒有失控，可小幅加碼；跌破 {stop:.2f} 則停止加碼並檢討。"
    else:
        stance = "等待確認"
        plan = f"現價 {close:.2f} 尚未形成高勝率加碼點，等待突破 {breakout:.2f} 或回測 {low:.2f}～{high:.2f} 守穩再行動。"
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
        strong_symbols = {r["card"]["symbol"] for r in strongest}
        weakest = [r for r in sorted(rows, key=lambda r: r["card"]["score"]) if r["card"]["symbol"] not in strong_symbols][:2]
        top_theme = ""
        if total_value:
            theme, val = max(theme_value.items(), key=lambda kv: kv[1])
            concentration = val / total_value * 100
            top_theme = f"目前最大曝險族群為 {theme}，約占 {concentration:.1f}%。"
        summary = f"持股總教練：目前組合總損益 {total_pnl:.0f}（{total_pnl_pct:.2f}%）。{top_theme} 策略上以汰弱留強為主，分數高且未跌破失效價的部位續抱，分數低或資料可信度不足的部位不加碼。優先續抱：{'、'.join(r['stock'] for r in strongest)}；優先檢討：{('、'.join(r['stock'] for r in weakest) if weakest else '暫無明顯落後持股')}。"
    return {"rows": rows, "total_cost": round(total_cost, 0), "total_value": round(total_value, 0), "total_pnl": round(total_pnl, 0), "total_pnl_pct": round(total_pnl_pct, 2), "summary": summary}


def _macd_zero_axis_candidates(cards: list[dict]) -> list[dict]:
    priority_map = {"剛從0軸翻正": 0, "即將從0軸翻正": 1}
    candidates = [
        c for c in cards
        if c.get("data_trust", {}).get("actionable")
        and c["tech"]["macd"].get("zero_axis_status", "") in priority_map
    ]

    def rank(card: dict) -> tuple[int, float, int]:
        status = card["tech"]["macd"].get("zero_axis_status", "")
        rsi = card["tech"].get("rsi") or 50
        return (priority_map.get(status, 9), abs(rsi - 55), -card["score"])

    return sorted(candidates, key=rank)[:10]


def _data_source_summary(cards: list[dict], status: dict) -> dict:
    latest_dates = [c.get("latest_date") for c in cards if c.get("latest_date")]
    policy = expected_latest_trading_date(status)
    official_count = sum(1 for c in cards if c.get("official_confirmed"))
    yahoo_newer_count = sum(1 for c in cards if c.get("official_lagging"))
    official_anomaly_count = sum(1 for c in cards if c.get("data_trust", {}).get("official_price_anomaly") or c.get("official_price_anomaly"))
    fallback_count = sum(1 for c in cards if c.get("data_quality") == "fallback")
    stale_count = sum(1 for c in cards if c.get("data_trust", {}).get("latest_date") and c.get("data_trust", {}).get("latest_date") < policy["expected_date"])
    yahoo_only_count = sum(1 for c in cards if (not c.get("official_confirmed") and c.get("data_quality") != "fallback" and not c.get("official_lagging") and not c.get("official_price_anomaly")))
    yahoo_selected_count = yahoo_newer_count + yahoo_only_count + official_anomaly_count
    max_date = max(latest_dates) if latest_dates else ""
    min_date = min(latest_dates) if latest_dates else ""
    if stale_count:
        truth_status = f"有 {stale_count} 檔資料早於預期最新交易日，已限制強推薦"
    elif official_anomaly_count:
        truth_status = f"有 {official_anomaly_count} 檔官方快照價格異常，已改採 Yahoo 並降低信心"
    elif yahoo_newer_count:
        truth_status = "官方資料尚未全部同步，已採用較新的 Yahoo 資料作為判斷基準"
    else:
        truth_status = "資料日期符合目前交易狀態"
    return {
        "official_confirmed": official_count,
        "yahoo_newer_than_official": yahoo_newer_count,
        "yahoo_only": yahoo_only_count,
        "yahoo_selected": yahoo_selected_count,
        "official_anomaly": official_anomaly_count,
        "fallback": fallback_count,
        "stale": stale_count,
        "expected_latest_date": policy["expected_date"],
        "expected_policy": policy["mode"],
        "price_date_min": min_date,
        "price_date_max": max_date,
        "truth_status": truth_status,
        "description": "v3.5.1 採用資料新鮮度與價格合理性雙重檢查：TWSE / TPEx 與 Yahoo 比較日期，並避免官方異常快照破壞技術線圖與持股估值。",
    }


def run_teacher_pipeline() -> dict:
    status = trading_status()
    universe = ai_universe()
    cards = [build_decision_card(stock, status=status) for stock in universe]
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    cards.sort(key=lambda x: (grade_order.get(x["grade"], 9), -x["score"]))
    buy = [c for c in cards if c["grade"] == "A"][:5]
    wait = [c for c in cards if c["grade"] == "B"][:8]
    avoid = [c for c in cards if c["grade"] == "D"][:8]
    macd_zero = _macd_zero_axis_candidates(cards)
    cards_by_symbol = {c["symbol"]: c for c in cards}
    watch_items = []
    for item in load_watchlist():
        try:
            stock = resolve_stock(str(item.get("symbol") or item.get("name") or ""))
            watch_items.append(cards_by_symbol.get(stock.symbol) or build_decision_card(stock, status=status))
        except Exception:
            continue
    data_source_summary = _data_source_summary(cards, status)
    return {
        "version": "3.5.1",
        "trading_status": status,
        "market_view": "偏多但不追高" if buy or wait else "中性偏保守",
        "teacher_summary": "股市老師以資料新鮮度為先：TWSE/TPEx 官方與 Yahoo 比較後採用較新的資料；若資料非預期最新交易日、fallback 或樣本不足，直接降級為觀察，不硬給買進。",
        "buy_list": buy,
        "wait_list": wait,
        "avoid_list": avoid,
        "macd_list": macd_zero,
        "macd_zero_axis_list": macd_zero,
        "watchlist_analysis": watch_items,
        "portfolio_coach": _portfolio_coach(cards_by_symbol),
        "data_source_summary": data_source_summary,
        "all_cards": cards,
    }
