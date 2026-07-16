"""Strong momentum radar for AI Stock Radar.

This module is intentionally separate from the Teacher buy-list engine.
A stock can be strong without being a good buy right now.  The product should
show both: 波段可買 and 今日強勢 / 已漲不追 / 明日接力觀察.
"""

from __future__ import annotations


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _recent_high(prices: list[dict], days: int = 20) -> float:
    if not prices:
        return 0.0
    recent = prices[-days:] if len(prices) >= days else prices
    highs = []
    for row in recent:
        highs.append(_safe_float(row.get("high") or row.get("close")))
    return max(highs) if highs else 0.0


def _is_recent_high_breakout(card: dict) -> bool:
    prices = card.get("prices") or []
    close = _safe_float(card.get("tech", {}).get("close"))
    high20 = _recent_high(prices[:-1] or prices, 20)
    return bool(high20 and close >= high20 * 0.995)


def classify_strength(card: dict) -> dict:
    """Return momentum classification for one decision card.

    Strength is not equal to Buy.  This separates the question:
    - 市場今天追什麼？
    - 現在還能不能買？
    """
    tech = card.get("tech") or {}
    change_pct = _safe_float(tech.get("change_pct"))
    volume_ratio = _safe_float(tech.get("volume_ratio"), 1.0)
    close = _safe_float(tech.get("close"))
    breakout = _safe_float(tech.get("breakout"))
    rsi = _safe_float(tech.get("rsi"), 50.0)
    ma20 = _safe_float(tech.get("ma20"))
    ma60 = _safe_float(tech.get("ma60"))
    zero_status = str((tech.get("macd") or {}).get("zero_axis_status") or "")
    actionable = bool((card.get("data_trust") or {}).get("actionable", True))
    near_high = _is_recent_high_breakout(card)

    score = 0
    reasons: list[str] = []

    if change_pct >= 8.8:
        score += 34
        reasons.append(f"今日漲幅 {change_pct}% 接近漲停，短線資金明顯集中")
    elif change_pct >= 5:
        score += 26
        reasons.append(f"今日漲幅 {change_pct}% 明顯強於一般波動")
    elif change_pct >= 3:
        score += 18
        reasons.append(f"今日漲幅 {change_pct}% 屬於強勢上漲")
    elif change_pct > 0:
        score += 8
        reasons.append(f"今日上漲 {change_pct}%，動能偏正向")

    if volume_ratio >= 2.2:
        score += 24
        reasons.append(f"量能比 {volume_ratio} 明顯放大，市場關注度升高")
    elif volume_ratio >= 1.5:
        score += 18
        reasons.append(f"量能比 {volume_ratio} 放大，買盤參與度提升")
    elif volume_ratio >= 1.15:
        score += 10
        reasons.append(f"量能比 {volume_ratio} 溫和放大")

    if near_high:
        score += 20
        reasons.append("股價接近或突破近 20 日高點，短線趨勢轉強")

    if close and breakout and close >= breakout:
        score += 16
        reasons.append(f"股價已站上突破價 {breakout:.2f}")
    elif close and breakout and close >= breakout * 0.96:
        score += 8
        reasons.append(f"股價接近突破價 {breakout:.2f}，可列入接力觀察")

    if ma20 and close > ma20:
        score += 6
    if ma60 and close > ma60:
        score += 6

    if zero_status in {"剛從0軸翻正", "0軸上方延續"}:
        score += 10
        reasons.append(f"MACD {zero_status}，波段動能不弱")
    elif zero_status == "即將從0軸翻正":
        score += 8
        reasons.append("MACD DIF 接近 0 軸翻正，屬於提前觀察訊號")

    if rsi >= 78:
        score -= 12
        reasons.append(f"RSI {rsi} 偏熱，強勢但追高風險提高")
    elif 50 <= rsi <= 72:
        score += 8
        reasons.append(f"RSI {rsi} 位階健康，尚未明顯過熱")

    score = max(0, min(100, int(round(score))))

    if not actionable:
        category = "資料不足"
        teacher_view = "資料不足，不列入強勢追蹤。"
        tomorrow_plan = "先補齊資料，不做接力判斷。"
    elif change_pct >= 8.8:
        category = "接近漲停 / 強勢鎖定"
        teacher_view = "很強，但不等於現在可追；若已持有可觀察鎖單與量能，空手者通常等隔日換手或回測再評估。"
        tomorrow_plan = "明日觀察是否開高不爆量、回測不破今日高檔區，若量縮守穩才有接力條件。"
    elif change_pct >= 5 and (rsi >= 72 or volume_ratio >= 2.2):
        category = "已漲不追"
        teacher_view = "短線資金強，但位階或量能偏熱；股市老師不建議追高，改列明日接力觀察。"
        tomorrow_plan = "明日看是否量縮整理、回測不破關鍵支撐；若開高爆量反而要防震盪。"
    elif score >= 68:
        category = "今日強勢"
        teacher_view = "今天量價與技術結構同步轉強，可列為強勢股雷達；是否能買仍要看是否位於合理買點。"
        tomorrow_plan = "明日若不跌破今日轉強區，且族群同步，列為接力觀察。"
    elif score >= 52:
        category = "明日接力觀察"
        teacher_view = "已有轉強跡象但還不是最強，適合觀察明日是否放量突破或回測守穩。"
        tomorrow_plan = "等突破或拉回確認，不提前追價。"
    else:
        category = "一般觀察"
        teacher_view = "今日強度不足，不列入強勢股主名單。"
        tomorrow_plan = "等待更明確量價訊號。"

    if not reasons:
        reasons = ["尚未出現明確強勢訊號"]

    return {
        "symbol": card.get("symbol"),
        "label": card.get("label"),
        "strength_score": score,
        "strength_category": category,
        "strength_reasons": reasons[:6],
        "teacher_view": teacher_view,
        "tomorrow_plan": tomorrow_plan,
        "change_pct": change_pct,
        "volume_ratio": volume_ratio,
        "close": close,
        "rsi": rsi,
        "linked_decision": card.get("decision"),
        "linked_grade": card.get("grade"),
        "card": card,
    }


def build_strength_payload(cards: list[dict]) -> dict:
    rows = [classify_strength(card) for card in cards]
    actionable = [row for row in rows if row["strength_category"] != "資料不足"]
    strong = [row for row in actionable if row["strength_score"] >= 68]
    strong.sort(key=lambda r: (-r["strength_score"], -r["change_pct"], -r["volume_ratio"]))

    limit_watch = [row for row in actionable if row["change_pct"] >= 8.0]
    limit_watch.sort(key=lambda r: (-r["change_pct"], -r["strength_score"]))

    no_chase = [row for row in actionable if row["strength_category"] in {"已漲不追", "接近漲停 / 強勢鎖定"}]
    no_chase.sort(key=lambda r: (-r["change_pct"], -r["volume_ratio"]))

    tomorrow = [row for row in actionable if row["strength_category"] in {"明日接力觀察", "今日強勢", "已漲不追", "接近漲停 / 強勢鎖定"}]
    tomorrow.sort(key=lambda r: (-r["strength_score"], -r["volume_ratio"], -r["change_pct"]))

    return {
        "strong_list": strong[:12],
        "limit_watch": limit_watch[:10],
        "no_chase_list": no_chase[:10],
        "tomorrow_watch": tomorrow[:12],
        "all_strength": sorted(actionable, key=lambda r: (-r["strength_score"], -r["change_pct"]))[:30],
    }


def build_gap_analysis(buy_list: list[dict], strength_payload: dict) -> dict:
    buy_symbols = {c.get("symbol") for c in buy_list}
    strong_rows = strength_payload.get("strong_list", [])
    strong_symbols = {r.get("symbol") for r in strong_rows}
    strong_not_buy = [r for r in strong_rows if r.get("symbol") not in buy_symbols][:8]
    buy_not_strong = [c for c in buy_list if c.get("symbol") not in strong_symbols][:8]
    lines: list[str] = []
    if strong_not_buy:
        names = "、".join(r["label"] for r in strong_not_buy[:5])
        lines.append(f"今日強勢但未列入可買：{names}。原因通常是漲幅已大、離理想買點太遠或需要隔日換手確認。")
    else:
        lines.append("今日可買名單與強勢股重疊度較高，代表波段買點與市場資金方向一致。")
    if buy_not_strong:
        names = "、".join(c["label"] for c in buy_not_strong[:5])
        lines.append(f"今日可買但非最強勢：{names}。這類偏波段買點，不是追漲停邏輯，重點在買點與風險報酬比。")
    if not strong_rows:
        lines.append("目前強勢股雷達沒有明確主線，今日不硬追強勢。")
    return {
        "strong_not_buy": strong_not_buy,
        "buy_not_strong": buy_not_strong,
        "summary": " ".join(lines),
    }
