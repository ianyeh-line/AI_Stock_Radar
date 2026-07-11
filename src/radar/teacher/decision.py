"""Stock teacher decision engine.

v3.10.0 Daily Decision Loop + Decision Quality Gate Rule:
- Compare official TWSE / TPEx daily snapshot vs Yahoo daily data.
- Use the newest valid data source as the price basis.
- Do not downgrade solely because the source is Yahoo or because official data is unavailable.
- Downgrade only when data is truly stale for the current trading state, fallback, missing, or insufficient.
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
from radar.teacher.market_strength import build_market_strength_payload, build_strength_gap_analysis
from radar.teacher.decision_loop import build_decision_loop


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
        mode = "盤中/盤後，優先使用目前交易狀態下可取得的最新有效資料"
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

    if quality == "fallback" or source == "fallback":
        warnings.append("價格資料為 fallback，禁止列為買進，只能觀察")
    if sample_size < 60:
        warnings.append("日線樣本不足 60 根，技術指標可信度不足")

    try:
        latest_d = date.fromisoformat(latest_date)
        expected_d = date.fromisoformat(expected_date)
        if latest_d < expected_d:
            warnings.append(f"資料基準日 {latest_date} 早於目前交易狀態應有的最新資料日 {expected_date}，不給強推薦")
        elif latest_d == expected_d:
            notes.append(f"資料基準日 {latest_date} 符合目前交易狀態的最新資料要求")
        else:
            notes.append(f"資料基準日 {latest_date} 晚於預期交易日 {expected_date}；依最新資料規則採用")
    except Exception:
        warnings.append("無法判斷資料日期")

    if official_confirmed and not official_lagging:
        notes.append("官方資料與採用資料同日或官方資料較新")
    elif official_lagging and latest_date:
        notes.append("已採用目前交易狀態下最新有效資料")
    elif quality == "yahoo_with_undated_official":
        notes.append("已採用目前交易狀態下最新有效資料")
    elif quality != "fallback":
        notes.append("已採用目前交易狀態下最新有效資料")

    actionable = not warnings
    if not actionable:
        trust_level = "低"
        status_text = "資料不足，僅能觀察"
    elif quality == "official_newer_than_yahoo":
        trust_level = "高"
        status_text = "官方資料較新，可作為操作參考"
    elif official_confirmed and not official_lagging:
        trust_level = "高"
        status_text = "資料為目前交易狀態下的最新有效資料"
    elif official_lagging:
        trust_level = "高"
        status_text = "採用目前交易狀態下最新有效資料"
    else:
        trust_level = "高"
        status_text = "採用目前交易狀態下最新可得資料，可作為操作參考"

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
        "official_price_anomaly": False,
        "official_source": official_snapshot.get("source") or prices.get("official_source") or "未取得",
        "official_date": official_snapshot.get("date") or prices.get("official_date") or "未提供",
        "official_message": official_snapshot.get("message", ""),
        "yahoo_date": prices.get("yahoo_latest_date") or latest_date,
        "source_selection": source_selection,
        "age_days": _date_age(latest_date),
        "warnings": warnings,
        "notes": notes,
    }


def _price_context(tech: dict) -> dict:
    close = float(tech["close"])
    low = float(tech["support_low"])
    high = float(tech["support_high"])
    breakout = float(tech["breakout"])
    stop = float(tech["stop"])
    change_pct = float(tech.get("change_pct") or 0.0)
    prev_close = close / (1 + change_pct / 100) if change_pct > -99 else close
    today_limit_up = prev_close * 1.1
    volume_ratio = float(tech.get("volume_ratio") or 0.0)
    in_buy_zone = low <= close <= high
    near_buy_zone = low <= close <= high * 1.015
    extended_above_buy_zone = close > high * 1.015 and close < breakout
    breakout_reached = close >= breakout
    breakout_unreachable_today = breakout > today_limit_up * 1.002
    return {
        "close": close,
        "low": low,
        "high": high,
        "breakout": breakout,
        "stop": stop,
        "change_pct": change_pct,
        "prev_close": prev_close,
        "today_limit_up": today_limit_up,
        "volume_ratio": volume_ratio,
        "in_buy_zone": in_buy_zone,
        "near_buy_zone": near_buy_zone,
        "extended_above_buy_zone": extended_above_buy_zone,
        "breakout_reached": breakout_reached,
        "breakout_unreachable_today": breakout_unreachable_today,
    }


def _decision(score: int, tech: dict) -> tuple[str, str, str]:
    ctx = _price_context(tech)
    close = ctx["close"]
    breakout = ctx["breakout"]
    # A 級今日可買只給「仍在合理買點附近」或「有效突破且未過熱」的個股。
    # 若現價已明顯高於拉回區但尚未突破，不能再硬列今日可買。
    if score >= 78 and ctx["near_buy_zone"]:
        return "今日可買", "拉回買進", "A"
    if score >= 82 and ctx["breakout_reached"] and ctx["volume_ratio"] >= 1.15:
        return "今日可買", "突破後回測買", "A"
    if score >= 78 and (close < breakout or ctx["breakout_reached"]):
        return "等待突破", "等待確認買", "B"
    if score >= 65:
        return "只觀察", "等待拉回或轉強", "C"
    return "避免", "暫不操作", "D"


def _breakout_context(tech: dict) -> str:
    ctx = _price_context(tech)
    close = ctx["close"]
    breakout = ctx["breakout"]
    vr = ctx["volume_ratio"]
    limit_up = ctx["today_limit_up"]
    if ctx["breakout_reached"]:
        if vr >= 1.2:
            return f"股價 {close:.2f} 已站上關鍵突破價 {breakout:.2f}，且量能比 {vr:.2f} 有配合，波段結構轉強；持股者可續抱，未持有者等回測突破價附近不破再評估。"
        return f"股價 {close:.2f} 已站上關鍵突破價 {breakout:.2f}，但量能比 {vr:.2f} 尚未明顯放大，先視為試探突破；持股者可續抱，未持有者不追價。"
    if ctx["breakout_unreachable_today"]:
        return f"關鍵突破價 {breakout:.2f} 高於今日漲停附近 {limit_up:.2f}，今日不能把突破當成可執行條件；本日重點改看是否站穩現價區與隔日是否延續。"
    return f"尚未突破關鍵壓力 {breakout:.2f}，需等量價確認，不提前把觀察股當成強勢股。"


def _action_text(label: str, tech: dict) -> str:
    """Return an executable teacher action.

    Decision Quality Gate rule:
    - If price has already moved above the pullback buy zone, never say the
      user can still buy inside that lower zone.
    - If breakout is already reached, wording must say it is already reached.
    - If breakout is unreachable today, do not use it as today's action.
    """
    ctx = _price_context(tech)
    close = ctx["close"]
    low = ctx["low"]
    high = ctx["high"]
    breakout = ctx["breakout"]
    stop = ctx["stop"]
    trim1 = tech["trim1"]
    trim2 = tech["trim2"]
    vr = ctx["volume_ratio"]

    if label == "今日可買":
        if ctx["breakout_reached"]:
            if vr >= 1.2:
                return (
                    f"股價已站上 {breakout:.2f}，量能比 {vr:.2f} 有配合；已持有者可續抱。"
                    f"空手者不追高，等回測 {breakout:.2f} 附近守穩，或量縮回到 {low:.2f}～{high:.2f} 再評估。"
                    f"跌破 {stop:.2f} 則波段劇本失效。"
                )
            return (
                f"股價已站上 {breakout:.2f}，但量能比 {vr:.2f} 尚未確認；持股可看，不建議空手追價。"
                f"若回測 {breakout:.2f} 仍守住，再評估第二買點；跌破 {stop:.2f} 轉弱。"
            )
        if ctx["near_buy_zone"]:
            return (
                f"股價仍在老師規劃的拉回買點附近，可在 {low:.2f}～{high:.2f} 以分批方式布局；"
                f"跌破 {stop:.2f} 停止加碼並檢討。"
            )
        return (
            f"分數雖達標，但今日股價 {close:.2f} 已高於理想買點 {low:.2f}～{high:.2f}；"
            f"今日不追價，等待回測支撐或重新站穩新的整理平台。"
        )

    if label == "等待突破":
        if ctx["breakout_reached"]:
            if vr >= 1.2:
                return (
                    f"股價已突破 {breakout:.2f}，但尚未通過今日可買的完整條件；先觀察能否站穩，"
                    f"不要在第一時間追高加碼。"
                )
            return f"股價雖已碰到突破區，但量能比 {vr:.2f} 不足；先視為試探突破，等待站穩。"
        if ctx["extended_above_buy_zone"]:
            return (
                f"今日股價 {close:.2f} 已高於拉回買點 {low:.2f}～{high:.2f}，但尚未突破 {breakout:.2f}；"
                f"此處風險報酬比不佳，等回測或下一根確認。"
            )
        if ctx["breakout_unreachable_today"]:
            return (
                f"關鍵突破價 {breakout:.2f} 今日不可作為執行條件；"
                f"先看股價能否守住 {low:.2f}～{high:.2f} 或建立新的整理平台。"
            )
        return f"等待站上 {breakout:.2f}，或回測 {low:.2f}～{high:.2f} 守穩再評估。"

    if label == "只觀察":
        if close > high:
            return (
                f"股價 {close:.2f} 高於拉回區但缺少足夠轉強條件，不追；"
                f"等回測 {low:.2f}～{high:.2f} 或放量站上 {breakout:.2f}。"
            )
        return f"尚未形成高勝率買點；必須站回 {high:.2f} 且量能改善才提高評級，跌破 {stop:.2f} 轉弱。"

    return f"暫不建立新部位；若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向減碼或避開。"

def _format_num(value) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "--"


def _theme_teacher_context(stock: StockInfo) -> str:
    theme = stock.theme or "未分類"
    mapping = {
        "半導體": "屬於半導體核心供應鏈，觀察重點在大盤電子權值、SOX 氣氛與台股資金是否持續留在電子族群。",
        "IC設計": "屬於 IC 設計族群，股價常受產品週期、庫存循環與外資風險偏好影響；若族群輪動轉弱，不宜只看單一技術買點。",
        "PCB": "屬於 PCB / 載板鏈，通常要搭配 AI 伺服器、網通與高階材料需求觀察；若同族群同步轉強，波段可信度會提高。",
        "AI伺服器": "屬於 AI 伺服器供應鏈，重點是 AI CapEx、伺服器出貨與法人是否願意追價。題材強時也要避免追在短線過熱區。",
        "散熱": "屬於 AI 散熱受惠鏈，波段常看高階散熱需求與 AI Server 題材延續性；若量能退潮，容易回測均線。",
        "封測": "屬於半導體封測鏈，通常跟晶圓代工、先進封裝與電子族群資金同步性有關。",
    }
    return mapping.get(theme, f"目前系統歸類為「{theme}」，消息面不做無根據加分；若沒有直接催化，仍以價格、量能與技術結構為主。")


def _rsi_teacher_sentence(rsi) -> str:
    try:
        r = float(rsi)
    except Exception:
        return "RSI 資料不足，無法作為位階判斷依據。"
    if r >= 78:
        return f"RSI {r:.1f} 已偏熱，老師不建議追高，較適合等拉回或量縮整理。"
    if r >= 65:
        return f"RSI {r:.1f} 位階偏高但尚未失控，若量價仍健康可續抱，但加碼要更挑價格。"
    if r >= 45:
        return f"RSI {r:.1f} 位於中性偏健康區，代表股價仍有操作空間，不屬於明顯過熱。"
    if r >= 30:
        return f"RSI {r:.1f} 偏弱，若要買進必須等價量轉強，不適合只因跌深就接。"
    return f"RSI {r:.1f} 明顯弱勢，除非出現止跌與量能確認，否則不列為積極買點。"


def _volume_teacher_sentence(vr) -> str:
    try:
        v = float(vr)
    except Exception:
        return "量能資料不足，不能用量能確認買點。"
    if v >= 2.2:
        return f"量能比 {v:.2f} 明顯放大，代表市場關注度升高，但也要留意短線換手與震盪。"
    if v >= 1.2:
        return f"量能比 {v:.2f} 溫和放大，是波段轉強較健康的量能型態。"
    if v >= 0.8:
        return f"量能比 {v:.2f} 接近均量，代表買盤尚可，但還不到強勢確認。"
    return f"量能比 {v:.2f} 偏低，代表追價力道不足，買點應更保守。"


def _macd_teacher_sentence(macd: dict) -> str:
    dif = macd.get("macd")
    dea = macd.get("signal")
    hist = macd.get("hist")
    status = macd.get("zero_axis_status") or macd.get("hist_status") or "未知"
    if status == "剛從0軸翻正":
        tone = "DIF 剛站上 0 軸，這是波段轉強初期訊號，若 DEA 同步上彎且量能不縮，可提高觀察優先度。"
    elif status == "即將從0軸翻正":
        tone = "DIF 仍在 0 軸附近但接近翻正，屬於提前觀察訊號；還沒正式確認前，先用觀察或小部位試單，不做情緒性追價。"
    elif status == "0軸上方延續":
        tone = "DIF 位於 0 軸上方延續，趨勢仍偏多，但要搭配價格是否仍在合理買點。"
    elif status == "0軸下方偏弱":
        tone = "DIF 仍在 0 軸下方，波段尚未正式轉強，應以觀察與等待確認為主。"
    else:
        tone = f"MACD 狀態為「{status}」，需搭配股價位置與量能判斷。"
    return f"{tone}（DIF {_format_num(dif)}、DEA {_format_num(dea)}、柱狀體 {_format_num(hist)}）"


def _chip_teacher_sentence(card: dict) -> str:
    """Explain chip/fund-flow honestly without fabricating data."""
    flow = card.get("institutional_flow") or card.get("flow") or {}
    if flow:
        summary = flow.get("summary") or flow.get("teacher_summary") or ""
        if summary:
            return f"籌碼 / 法人面：{summary}"
    return (
        "籌碼 / 法人面：本卡目前沒有足夠的連續法人買賣超資料，"
        "所以不把籌碼面列為買進加分。老師只會把它視為待補資料；若後續看到外資、投信連續買超且換手健康，才會提高追價信心。"
    )


def _quality_gate(score: int, tech: dict, trust: dict) -> dict:
    """Hard gate before a stock can be shown as actionable buy.

    This is the core of v3.9.0. It prevents the most common trust-breaking
    mistakes: recommending a lower buy zone after price has already moved away,
    using unreachable breakout prices as today's condition, or pretending a
    weak data card is an A-grade recommendation.
    """
    ctx = _price_context(tech)
    failures: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    rsi = tech.get("rsi") or 50
    vr = tech.get("volume_ratio") or 0

    if not trust.get("actionable", True):
        failures.append("資料不足或資料失效，不可列為今日可買。")
    if score < 78:
        failures.append(f"Radar {score} 未達 A 級推薦門檻。")
    if ctx["extended_above_buy_zone"] and not ctx["breakout_reached"]:
        failures.append("現價已高於拉回買點且尚未突破，不能列為今日可買。")
    if ctx["breakout_reached"] and vr < 1.15:
        failures.append("雖已突破，但量能不足，不列為追價買點。")
    if rsi >= 78:
        failures.append("RSI 過熱，不列為追價買點。")
    if vr >= 4.5:
        failures.append("量能過度爆量，容易是短線換手高風險區。")
    if ctx["breakout_unreachable_today"]:
        warnings.append("突破價高於今日可執行範圍，本日不把突破視為操作條件。")
    if ctx["near_buy_zone"]:
        notes.append("現價仍接近拉回買點，可規劃分批。")
    if ctx["breakout_reached"]:
        notes.append("股價已突破，重點轉為是否站穩與量能是否支持。")
    return {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "notes": notes,
    }


def _teacher_narrative(stock: StockInfo, card: dict) -> dict:
    tech = card["tech"]
    close = float(tech["close"])
    low = float(tech["support_low"])
    high = float(tech["support_high"])
    stop = float(tech["stop"])
    breakout = float(tech["breakout"])
    trim1 = float(tech["trim1"])
    trim2 = float(tech["trim2"])
    rsi = tech.get("rsi")
    vr = tech.get("volume_ratio")
    ma20 = tech.get("ma20")
    ma60 = tech.get("ma60")
    macd = tech.get("macd", {})
    ctx = _price_context(tech)
    gate = card.get("quality_gate") or {}

    trend_parts = []
    if ma20:
        trend_parts.append("站上 MA20" if close > ma20 else "跌破 MA20")
    if ma60:
        trend_parts.append("站上 MA60" if close > ma60 else "跌破 MA60")
    trend_text = "、".join(trend_parts) if trend_parts else "均線資料不足"

    if ctx["breakout_reached"]:
        if (vr or 0) >= 1.2:
            price_state = f"今日股價 {close:.2f} 已突破 {breakout:.2f}，量能比 {float(vr or 0):.2f} 有配合，重點是能否站穩，而不是追高。"
        else:
            price_state = f"今日股價 {close:.2f} 已突破 {breakout:.2f}，但量能尚未確認，先視為試探突破。"
    elif ctx["near_buy_zone"]:
        price_state = f"今日股價 {close:.2f} 仍在 {low:.2f}～{high:.2f} 拉回買點附近，屬於可以規劃分批的位置。"
    elif close < stop:
        price_state = f"今日股價 {close:.2f} 已跌破失效價 {stop:.2f}，原本波段劇本失效。"
    elif ctx["extended_above_buy_zone"]:
        price_state = f"今日股價 {close:.2f} 已高於拉回買點 {low:.2f}～{high:.2f}，但尚未突破 {breakout:.2f}；這裡不是好的追價位置。"
    else:
        price_state = f"今日股價 {close:.2f} 尚未落在老師定義的高勝率買點，等待價量重新轉強。"

    technical = (
        f"技術面：{price_state} 均線結構為{trend_text}。"
        f"{_macd_teacher_sentence(macd)} {_rsi_teacher_sentence(rsi)} {_volume_teacher_sentence(vr)}"
    )
    chip = _chip_teacher_sentence(card)
    news = (
        f"產業 / 消息面：{_theme_teacher_context(stock)} "
        "若未偵測到直接催化消息，本次不把消息面作為買進加分，而是以價量、支撐壓力與趨勢位置決定操作。"
    )
    support = (
        f"支撐 / 壓力：拉回觀察區 {low:.2f}～{high:.2f}；突破確認價 {breakout:.2f}；"
        f"失效價 {stop:.2f}；第一減碼區 {trim1:.2f}；第二減碼區 {trim2:.2f}。"
    )

    action = _action_text(card["decision"], tech)
    if card.get("decision") == "今日可買" and gate.get("passed", True):
        teacher_judgement = f"老師判斷：{action}"
    elif card.get("decision") == "今日可買" and not gate.get("passed", True):
        teacher_judgement = f"老師判斷：分數達標但未通過可執行檢查；{action}"
    elif card.get("decision") == "等待突破":
        teacher_judgement = f"老師判斷：目前以等待為主，不急著買；{action}"
    elif card.get("decision") == "只觀察":
        teacher_judgement = f"老師判斷：條件尚未完整，只適合觀察；{action}"
    else:
        teacher_judgement = f"老師判斷：目前不適合建立新部位；{action}"

    if ctx["breakout_reached"]:
        scenario_a = f"A 劇本：股價站穩 {breakout:.2f} 且量能不縮，持股續抱，空手等待回測突破價附近再找第二買點。"
        scenario_b = f"B 劇本：突破後量能退潮，股價回測 {breakout:.2f}；守住可觀察，跌回則視為假突破。"
    elif ctx["extended_above_buy_zone"]:
        scenario_a = f"A 劇本：不追價，等待回測 {low:.2f}～{high:.2f} 守穩後再規劃。"
        scenario_b = f"B 劇本：若後續挑戰 {breakout:.2f}，必須量能同步放大；若突破價今日不可及，就留到下一交易日評估。"
    elif ctx["near_buy_zone"]:
        scenario_a = f"A 劇本：拉回 {low:.2f}～{high:.2f} 守穩，量能不失控，分批布局或續抱。"
        scenario_b = f"B 劇本：未拉回直接上攻，等站上 {breakout:.2f} 且量能確認，不提前追。"
    else:
        scenario_a = f"A 劇本：重新站回 {high:.2f} 並形成量價改善，再恢復觀察。"
        scenario_b = f"B 劇本：股價在現價附近震盪但量能不足，持續觀察不急著買。"
    scenario_c = f"C 劇本：跌破 {stop:.2f}，代表波段結構轉弱，停止加碼並檢討部位。"

    if ctx["breakout_reached"]:
        no_position = f"未持有者：不追高，等回測 {breakout:.2f} 守穩，或回到 {low:.2f}～{high:.2f} 才重新規劃。"
    elif ctx["near_buy_zone"]:
        no_position = f"未持有者：可在 {low:.2f}～{high:.2f} 分批，不重壓；跌破 {stop:.2f} 停止加碼。"
    elif ctx["extended_above_buy_zone"]:
        no_position = f"未持有者：現價已高於拉回區，不追；等回測 {low:.2f}～{high:.2f} 或下一次有效突破。"
    else:
        no_position = f"未持有者：還不是理想買點，等拉回 {low:.2f}～{high:.2f} 或量價站上 {breakout:.2f} 後再評估。"

    if ctx["breakout_reached"]:
        holding = f"已持有者：已突破者以續抱為主，但若跌回 {breakout:.2f} 且量能轉弱，先減碼觀察；跌破 {stop:.2f} 則波段失效。"
    else:
        holding = f"已持有者：未跌破 {stop:.2f} 前可續抱；若反彈到 {trim1:.2f}～{trim2:.2f} 但量能背離，可分批調節。"
    risk = f"風險提醒：跌破 {stop:.2f} 或量價背離時，不能用攤平取代停損紀律；若缺少籌碼與消息支持，部位要更保守。"

    return {
        "teacher_judgement": teacher_judgement,
        "technical": technical,
        "chip": chip,
        "news": news,
        "support_resistance": support,
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "scenario_c": scenario_c,
        "no_position_strategy": no_position,
        "holding_strategy": holding,
        "risk": risk,
        "quality_gate": gate,
        "conclusion": teacher_judgement,
        "summary_reasons": [technical, chip, news],
    }

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

    gate = _quality_gate(score, tech, trust)
    label, setup, grade = _decision(score, tech)

    # v3.9.0 Recommendation Quality Gate:
    # Any stock that does not pass the execution gate cannot remain A-grade
    # even if the numeric score is high.
    if grade == "A" and not gate["passed"]:
        label, setup, grade = "等待突破", "未通過可執行檢查", "B"
    if not trust["actionable"] and grade in {"A", "B"}:
        label, setup, grade = "只觀察", "資料不足不給買進", "C"

    confidence_penalty = 0 if trust["actionable"] else -18
    if not gate["passed"]:
        confidence_penalty -= 6
    confidence = min(96, max(40, score + confidence_penalty))
    card = {
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
        "reasons": [r for r in reasons if "Yahoo" not in r and "官方" not in r and "信心略降" not in r],
        "quality_gate": gate,
        "action": _action_text(label, tech),
        "risk": f"跌破 {tech['stop']:.2f} 代表波段結構轉弱，不建議用攤平取代停損紀律。",
    }
    card["teacher_narrative"] = _teacher_narrative(stock, card)
    return card


def _portfolio_advice(card: dict, pnl_pct: float) -> str:
    tech = card["tech"]
    close = tech["close"]
    low = tech["support_low"]
    high = tech["support_high"]
    breakout = tech["breakout"]
    stop = tech["stop"]
    trim1 = tech["trim1"]
    trim2 = tech["trim2"]
    score = card.get("score", 0)
    grade = card.get("grade", "-")
    reasons = "、".join(card.get("reasons", [])[:4]) or "目前缺少明確轉強理由"
    macd_status = tech.get("macd", {}).get("zero_axis_status", "未明確")
    volume_ratio = tech.get("volume_ratio", "-")
    trust = card.get("data_trust") or {}

    if not trust.get("actionable"):
        return (
            f"僅能觀察｜目前股價 {close:.2f}，資料狀態不足以支持積極動作。"
            f"A劇本：重新站回 {high:.2f} 且量能改善，再評估是否續抱或加碼。"
            f"B劇本：在 {low:.2f}～{high:.2f} 區間震盪，先以原部位觀察，不急著加碼。"
            f"C劇本：跌破 {stop:.2f}，波段結構轉弱，先控風險，不用攤平取代紀律。"
        )

    ctx = _price_context(tech)
    if score >= 78 and pnl_pct >= -5:
        stance = "偏續抱"
        if ctx["breakout_reached"]:
            plan = (
                f"目前股價 {close:.2f}，Radar {score}（等級 {grade}），已站上關鍵突破價 {breakout:.2f}。"
                f"只要沒有跌破 {stop:.2f}，老師看法是續抱優先；若量能轉弱或跌回突破價下方，才考慮分批調節。"
            )
        elif ctx["breakout_unreachable_today"]:
            plan = (
                f"目前股價 {close:.2f}，Radar {score}（等級 {grade}）。"
                f"關鍵突破價 {breakout:.2f} 高於今日漲停附近 {ctx['today_limit_up']:.2f}，今天不把突破當成操作條件；已持有者先看是否守住 {stop:.2f} 與現價區量能。"
            )
        else:
            plan = (
                f"目前股價 {close:.2f}，Radar {score}（等級 {grade}）。"
                f"只要沒有跌破 {stop:.2f}，老師看法是續抱優先；若後續放量突破 {breakout:.2f}，可視為波段轉強訊號。"
            )
    elif pnl_pct < -8 or score < 55:
        stance = "先檢討"
        plan = (
            f"目前股價 {close:.2f}，Radar {score}（等級 {grade}），部位不是優先加碼標的。"
            f"若跌破 {stop:.2f}，代表波段結構轉弱，應先減碼控風險；"
            f"若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向調節而不是加碼。"
        )
    elif ctx["near_buy_zone"]:
        stance = "可觀察加碼"
        plan = (
            f"目前股價 {close:.2f} 接近支撐觀察區 {low:.2f}～{high:.2f}。"
            f"若量能比維持在合理區間且不跌破 {stop:.2f}，可採小部位試單；"
            f"若跌破 {stop:.2f}，立刻停止加碼並重新檢討。"
        )
    else:
        stance = "等待確認"
        plan = (
            f"目前股價 {close:.2f} 尚未落在老師喜歡的高勝率加碼區。"
            f"上方等突破 {breakout:.2f}，下方等回測 {low:.2f}～{high:.2f} 守穩；"
            f"沒有到價就不硬買，避免把持股管理變成情緒交易。"
        )
    return (
        f"{stance}｜{plan}"
        f" 技術重點：MACD {macd_status}、量能比 {volume_ratio}。"
        f" 判斷依據：{reasons}。"
        f" 老師結論：持股先看價位與紀律，未到突破或支撐條件前，不因短線震盪任意加碼。"
    )


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
        strongest_text = '、'.join(f"{r['stock']}（Radar {r['card']['score']}）" for r in strongest)
        weakest_text = '、'.join(f"{r['stock']}（Radar {r['card']['score']}）" for r in weakest) if weakest else '暫無明顯落後持股'
        summary = (
            f"持股總教練：目前組合總損益 {total_pnl:.0f}（{total_pnl_pct:.2f}%）。{top_theme}"
            f"目前優先續抱：{strongest_text}；優先檢討：{weakest_text}。"
            f"操作上，強勢持股只要未跌破各自失效價，先以續抱為主；若股價已離加碼區太遠，等回測或下一次有效突破，不用為了帳面獲利而追價加碼。"
        )
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
    official_count = sum(1 for c in cards if c.get("data_quality") == "official_newer_than_yahoo")
    official_same_day_count = sum(1 for c in cards if c.get("data_quality") == "yahoo_same_day_official_confirmed")
    yahoo_newer_count = sum(1 for c in cards if c.get("official_lagging"))
    fallback_count = sum(1 for c in cards if c.get("data_quality") == "fallback")
    stale_count = sum(1 for c in cards if c.get("data_trust", {}).get("latest_date") and c.get("data_trust", {}).get("latest_date") < policy["expected_date"])
    yahoo_only_count = sum(1 for c in cards if (not c.get("official_confirmed") and c.get("data_quality") != "fallback" and not c.get("official_lagging")))
    yahoo_selected_count = yahoo_newer_count + yahoo_only_count + official_same_day_count
    max_date = max(latest_dates) if latest_dates else ""
    min_date = min(latest_dates) if latest_dates else ""
    if stale_count:
        truth_status = f"有 {stale_count} 檔資料早於目前交易狀態應有的最新資料，已限制強推薦"
    elif yahoo_newer_count:
        truth_status = "已採用目前交易狀態下最新有效資料作為判斷基準"
    else:
        truth_status = "資料日期符合目前交易狀態，依最新資料規則採用"
    return {
        "official_confirmed": official_count + official_same_day_count,
        "official_newer": official_count,
        "official_same_day": official_same_day_count,
        "yahoo_newer_than_official": yahoo_newer_count,
        "yahoo_only": yahoo_only_count,
        "yahoo_selected": yahoo_selected_count,
        "official_anomaly": 0,
        "fallback": fallback_count,
        "stale": stale_count,
        "expected_latest_date": policy["expected_date"],
        "expected_policy": policy["mode"],
        "price_date_min": min_date,
        "price_date_max": max_date,
        "truth_status": truth_status,
        "description": "v3.10.0 Daily Decision Loop + Decision Quality Gate Rule：只要資料是目前交易狀態下可取得的最新有效資料，就不因來源或來源不同步而降等；僅在資料過舊、fallback、缺失或樣本不足時限制強推薦。",
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
    strength_payload = build_market_strength_payload(cards, status, lambda stock: build_decision_card(stock, status=status))
    strength_gap = build_strength_gap_analysis(buy, strength_payload)
    cards_by_symbol = {c["symbol"]: c for c in cards}
    watch_items = []
    for item in load_watchlist():
        try:
            stock = resolve_stock(str(item.get("symbol") or item.get("name") or ""))
            watch_items.append(cards_by_symbol.get(stock.symbol) or build_decision_card(stock, status=status))
        except Exception:
            continue
    data_source_summary = _data_source_summary(cards, status)
    payload = {
        "version": "3.10.0",
        "trading_status": status,
        "market_view": "偏多但不追高" if buy or wait else "中性偏保守",
        "teacher_summary": "股市老師先給今天怎麼做，再依交易狀態切換盤前計畫、盤中觀察、盤後檢討與明日準備；每次執行會建立決策紀錄，讓下一次可以檢討推薦表現。",
        "buy_list": buy,
        "wait_list": wait,
        "avoid_list": avoid,
        "macd_list": macd_zero,
        "macd_zero_axis_list": macd_zero,
        "strong_momentum": strength_payload,
        "strength_gap_analysis": strength_gap,
        "watchlist_analysis": watch_items,
        "portfolio_coach": _portfolio_coach(cards_by_symbol),
        "data_source_summary": data_source_summary,
        "all_cards": cards,
    }
    payload["decision_loop"] = build_decision_loop(payload)
    return payload
