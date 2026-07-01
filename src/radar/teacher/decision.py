"""Stock teacher decision engine.

v3.8.2 Data Freshness Rule:
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


def _breakout_context(tech: dict) -> str:
    close = tech["close"]
    breakout = tech["breakout"]
    vr = tech.get("volume_ratio") or 0
    if close >= breakout:
        if vr >= 1.2:
            return f"股價已站上關鍵突破價 {breakout:.2f}，且量能比 {vr} 有配合，波段結構已轉強；持股者可續抱，空手者不追價，等待回測不破再評估。"
        return f"股價已站上關鍵突破價 {breakout:.2f}，但量能比 {vr} 未明顯放大，先視為試探突破；持股者可續抱，空手者不追價。"
    return f"尚未突破關鍵壓力 {breakout:.2f}，需等收盤或盤中量價確認，不提前把觀察股當成強勢股。"


def _action_text(label: str, tech: dict) -> str:
    close = tech["close"]
    low = tech["support_low"]
    high = tech["support_high"]
    breakout = tech["breakout"]
    stop = tech["stop"]
    trim1 = tech["trim1"]
    trim2 = tech["trim2"]
    breakout_context = _breakout_context(tech)
    if label == "今日可買":
        if close >= breakout:
            return f"{breakout_context} 若已有持股可續抱；若尚未持有，不追高，等回測 {breakout:.2f} 附近或 {low:.2f}～{high:.2f} 支撐區再找買點。跌破 {stop:.2f} 代表本次波段假突破或結構轉弱。"
        if low <= close <= high * 1.04:
            return f"可在 {low:.2f}～{high:.2f} 分批，跌破 {stop:.2f} 失效；若後續放量突破 {breakout:.2f}，持股者可續抱，不建議開盤急拉追價。"
        return f"分數達標但現價 {close:.2f} 不在理想買點，等回測 {low:.2f}～{high:.2f} 或放量突破 {breakout:.2f}；未到價不硬買。"
    if label == "等待突破":
        if close >= breakout:
            return f"{breakout_context} 由等待突破轉為觀察站穩；若量能不足，不追價加碼，等回測突破價附近確認。"
        if close > high:
            return f"現價 {close:.2f} 已高於支撐區 {low:.2f}～{high:.2f}，但尚未突破 {breakout:.2f}；等待突破確認或回測支撐區守穩。"
        return f"等待站上 {breakout:.2f}，或回測 {low:.2f}～{high:.2f} 守穩再評估。"
    if label == "只觀察":
        return f"尚未形成高勝率買點；站回 {high:.2f} 並量能改善才提高評級，跌破 {stop:.2f} 轉弱。"
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
        tone = "DIF 仍在 0 軸附近但接近翻正，屬於提前觀察訊號；還沒正式確認前，不適合無條件追價。"
    elif status == "0軸上方延續":
        tone = "DIF 位於 0 軸上方延續，趨勢仍偏多，但要搭配價格是否仍在合理買點。"
    elif status == "0軸下方偏弱":
        tone = "DIF 仍在 0 軸下方，波段尚未正式轉強，應以觀察與等待確認為主。"
    else:
        tone = f"MACD 狀態為「{status}」，需搭配股價位置與量能判斷。"
    return f"{tone}（DIF {_format_num(dif)}、DEA {_format_num(dea)}、柱狀體 {_format_num(hist)}）"


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
    theme = stock.theme or "未分類"

    if close >= breakout:
        if (tech.get("volume_ratio") or 0) >= 1.2:
            position_sentence = f"今日股價 {close:.2f} 已站上突破價 {breakout:.2f}，且量能有配合，波段結構偏向轉強。"
        else:
            position_sentence = f"今日股價 {close:.2f} 已站上突破價 {breakout:.2f}，但量能尚未明顯放大，先視為試探突破。"
    elif low <= close <= high * 1.04:
        position_sentence = f"今日股價 {close:.2f} 位在 {low:.2f}～{high:.2f} 支撐觀察區附近，屬於可規劃分批的位置。"
    elif close < stop:
        position_sentence = f"今日股價 {close:.2f} 已跌破失效價 {stop:.2f}，原本波段劇本失效，不能用攤平取代停損紀律。"
    elif close > high:
        position_sentence = f"今日股價 {close:.2f} 高於理想拉回區 {low:.2f}～{high:.2f}，但尚未形成有效突破，空手不追高。"
    else:
        position_sentence = f"今日股價 {close:.2f} 低於理想支撐區，需先觀察是否止跌轉強。"

    trend_parts = []
    if ma20:
        trend_parts.append("站上 MA20" if close > ma20 else "低於 MA20")
    if ma60:
        trend_parts.append("站上 MA60" if close > ma60 else "低於 MA60")
    trend_text = "、".join(trend_parts) if trend_parts else "均線資料不足"

    technical = (
        f"{position_sentence} 均線結構顯示股價目前{trend_text}。"
        f"{_macd_teacher_sentence(macd)} {_rsi_teacher_sentence(rsi)} {_volume_teacher_sentence(vr)}"
    )

    chip = (
        "籌碼面目前以量能與價量結構作為可觀察代理，尚未將完整連續法人買賣超與分點主力納入本卡加分。"
        f"{_volume_teacher_sentence(vr)} 若後續外資 / 投信同步買超，才會把籌碼面提升為波段加分；若價漲量縮或法人轉賣，則不追高。"
    )

    news = (
        f"產業 / 消息面：{_theme_teacher_context(stock)} 本次不因題材本身直接給買進，仍要求價格位置、量能與 MACD 結構同時支持。"
    )

    support = (
        f"支撐觀察區 {low:.2f}～{high:.2f}；突破確認價 {breakout:.2f}；"
        f"失效價 {stop:.2f}；第一減碼區 {trim1:.2f}；第二減碼區 {trim2:.2f}。"
    )

    base_action = _action_text(card["decision"], tech)
    if card.get("decision") == "今日可買":
        teacher_judgement = f"老師判斷：可列入今日可操作名單，但不是無條件追價。{base_action}"
    elif card.get("decision") == "等待突破":
        teacher_judgement = f"老師判斷：目前是等待確認，不是立刻追價。{base_action}"
    elif card.get("decision") == "只觀察":
        teacher_judgement = f"老師判斷：條件尚未完整，只適合觀察。{base_action}"
    else:
        teacher_judgement = f"老師判斷：目前不適合建立新部位。{base_action}"

    if close >= breakout:
        scenario_a = f"A 劇本：股價已突破 {breakout:.2f} 且量能維持，持股續抱，空手等回測突破價附近不破再找第二買點。"
        scenario_b = f"B 劇本：突破後量能無法延續，股價回測 {breakout:.2f}，若守住可觀察，跌回則降低評等。"
    else:
        scenario_a = f"A 劇本：拉回 {low:.2f}～{high:.2f} 守穩，量能不失控，分批買進或續抱。"
        scenario_b = f"B 劇本：直接挑戰 {breakout:.2f}，必須量能同步放大才視為有效突破；量能不足不追。"
    scenario_c = f"C 劇本：跌破 {stop:.2f}，代表波段結構轉弱，停止加碼並檢討部位。"

    if close >= breakout:
        no_position = f"未持有者：不在突破後急追，等待回測 {breakout:.2f} 附近守穩，或回到 {low:.2f}～{high:.2f} 再規劃。"
    elif low <= close <= high * 1.04:
        no_position = f"未持有者：可在 {low:.2f}～{high:.2f} 區間分批，單筆不重壓，跌破 {stop:.2f} 停止加碼。"
    else:
        no_position = f"未持有者：現價不在理想買點，等拉回 {low:.2f}～{high:.2f} 或突破 {breakout:.2f} 後再評估。"
    holding = f"已持有者：未跌破 {stop:.2f} 前，以續抱或小幅調節為主；若進入 {trim1:.2f}～{trim2:.2f} 且量能轉弱，可分批減碼。"
    risk = f"風險提醒：跌破 {stop:.2f} 就不是原本的波段劇本；若族群轉弱、量價背離或 MACD 轉弱，不要用攤平取代紀律。"

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
        "conclusion": teacher_judgement,
        "summary_reasons": [technical, chip, news][:3],
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

    label, setup, grade = _decision(score, tech)
    if not trust["actionable"] and grade in {"A", "B"}:
        label, setup, grade = "只觀察", "資料不足不給買進", "C"

    confidence_penalty = 0 if trust["actionable"] else -18
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
        "reasons": reasons,
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

    if score >= 78 and pnl_pct >= -5:
        stance = "偏續抱"
        plan = (
            f"目前股價 {close:.2f}，Radar {score}（等級 {grade}）。"
            f"只要沒有跌破 {stop:.2f}，老師看法是續抱優先；"
            f"若放量突破 {breakout:.2f}，可視為波段轉強訊號，持股者可續抱，空手者不追高、等回測再看。"
        )
    elif pnl_pct < -8 or score < 55:
        stance = "先檢討"
        plan = (
            f"目前股價 {close:.2f}，Radar {score}（等級 {grade}），部位不是優先加碼標的。"
            f"若跌破 {stop:.2f}，代表波段結構轉弱，應先減碼控風險；"
            f"若反彈到 {trim1:.2f}～{trim2:.2f} 但量能不足，偏向調節而不是加碼。"
        )
    elif low <= close <= high * 1.04:
        stance = "可觀察加碼"
        plan = (
            f"目前股價 {close:.2f} 靠近支撐觀察區 {low:.2f}～{high:.2f}。"
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
            f"老師會先做三件事：第一，保留趨勢仍在、未跌破失效價的強勢部位；第二，對反彈無量或跌破風險線的部位降低曝險；第三，不因帳面損益而盲目攤平。"
            f"目前優先續抱：{strongest_text}；優先檢討：{weakest_text}。"
            f"加碼原則：只有兩種情況值得做，一是回測支撐區守穩，二是放量突破關鍵壓力；其他情況以續抱或觀察為主。"
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
        "description": "v3.8.2 Data Freshness Rule：只要資料是目前交易狀態下可取得的最新有效資料，就不因來源或來源不同步而降等；僅在資料過舊、fallback、缺失或樣本不足時限制強推薦。",
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
    return {
        "version": "3.8.2",
        "trading_status": status,
        "market_view": "偏多但不追高" if buy or wait else "中性偏保守",
        "teacher_summary": "股市老師先給今天怎麼做，再補技術面、籌碼面、產業消息、支撐壓力與劇本推演；強勢股雷達會先掃描全市場，再挑出可追、已漲不追與明日接力觀察。",
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
