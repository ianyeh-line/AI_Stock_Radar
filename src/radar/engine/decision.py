"""Decision OS v1 for AI Stock Radar.

v0.8.0 combines:
- News Radar
- Technical Radar
- Risk Radar

The output is an explainable Decision Card, not a raw ranking.
"""

from __future__ import annotations

from radar.engine.technical import build_technical_snapshot
from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import DailyDecision, DecisionCard, Evidence, NewsItem

VERSION = "0.8.0"
BASE_NEWS_SCORE = 50


def _dedupe_evidence(evidence: list[Evidence]) -> list[Evidence]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Evidence] = []
    for item in evidence:
        key = (item.category, item.signal, item.title_zh[:80])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _news_score_for_item(ticker: str, item: NewsItem) -> int:
    profile = WATCHLIST[ticker]
    weight = profile["themes"].get(item.signal, 0.70)

    if item.sentiment == "positive":
        base = 7
    elif item.sentiment == "negative":
        base = -7
    else:
        base = 1

    return round(base * weight)


def _news_evidence(ticker: str, news_items: list[NewsItem]) -> list[Evidence]:
    profile = WATCHLIST[ticker]
    evidence: list[Evidence] = []
    for item in news_items:
        if ticker not in item.tickers:
            continue
        score = _news_score_for_item(ticker, item)
        if score > 0:
            tone = "positive"
            reason = f"{item.signal_zh}支撐 {profile['name']}：{item.title_zh[:90]}"
        elif score < 0:
            tone = "negative"
            reason = f"{item.signal_zh}提高短線風險：{item.title_zh[:90]}"
        else:
            tone = "neutral"
            reason = f"{item.signal_zh}仍需確認：{item.title_zh[:90]}"

        evidence.append(
            Evidence(
                category="新聞",
                signal=item.signal,
                signal_zh=item.signal_zh,
                tone=tone,
                score=score,
                source=item.source,
                reason=reason,
                title=item.title,
                title_zh=item.title_zh,
            )
        )
    return _dedupe_evidence(evidence)


def _technical_evidence(ticker: str) -> tuple[list[Evidence], int, object]:
    technical = build_technical_snapshot(ticker)
    if technical.score >= 70:
        tone = "positive"
        score = 8
    elif technical.score >= 55:
        tone = "neutral"
        score = 2
    else:
        tone = "negative"
        score = -8

    evidence = [
        Evidence(
            category="技術",
            signal="Technical Radar",
            signal_zh="技術面",
            tone=tone,
            score=score,
            source=technical.data_source,
            reason=f"技術面 {technical.trend}：{technical.signal}；收盤 {technical.price}，MA20 {technical.ma20}，RSI {technical.rsi14}",
            title="Technical Snapshot",
            title_zh="技術線圖快照",
        )
    ]
    return evidence, technical.score, technical


def _news_score(evidence: list[Evidence]) -> int:
    positive = [ev for ev in evidence if ev.score > 0]
    negative = [ev for ev in evidence if ev.score < 0]
    unique_signals = {ev.signal for ev in positive}
    raw = BASE_NEWS_SCORE + sum(ev.score for ev in evidence)
    raw += min(8, len(unique_signals) * 2)
    raw -= min(8, len(negative) * 2)
    if not positive:
        raw = min(raw, 52)
    return max(30, min(90, round(raw)))


def _risk_score(news_items: list[NewsItem], ticker: str, technical_score: int) -> int:
    macro_risks = [item for item in news_items if item.signal == "Macro Risk" and ticker in item.tickers]
    score = 82
    score -= min(22, len(macro_risks) * 8)
    if technical_score < 50:
        score -= 12
    elif technical_score > 75:
        score += 4
    return max(35, min(92, score))


def _decision_from_score(score: int) -> tuple[str, str]:
    if score >= 78:
        return "🟢 買進", "Buy"
    if score >= 66:
        return "🟡 觀察", "Watch"
    if score >= 54:
        return "⚪ 等待", "Wait"
    return "🔴 賣出", "Sell"


def _build_action(stance: str, technical_score: int) -> tuple[str, str, str]:
    if stance == "Buy":
        return (
            "列入今日優先清單；只在拉回且量能未失控時分批布局，避免開盤急拉追高。",
            "進場條件：價格維持在 MA20 之上，且同族群至少 2 檔同步強勢。",
            "風險：若美股期貨、半導體或個股技術線圖轉弱，降低進場比例。",
        )
    if stance == "Watch":
        return (
            "主線具備支撐但尚未形成高勝率進場點，先觀察突破或回測確認。",
            "進場條件：站上關鍵均線、量能放大且新聞主線未反轉。",
            "風險：若只有新聞支撐但技術面未確認，容易形成短線假突破。",
        )
    if stance == "Wait":
        return (
            "今日不是最優先標的；等待更明確的新聞催化或技術轉強。",
            "進場條件：Radar Score 回升到 66 以上，且技術面至少轉為中性偏多。",
            "風險：資金可能集中於其他主線，等待期間有機會成本。",
        )
    return (
        "風險大於機會；若已有部位，應檢查停損、減碼或降低曝險條件。",
        "重新評估條件：負面新聞消退，且價格重新站回 MA20 或 MA60。",
        "風險：若忽視負面訊號，可能擴大短線回撤。",
    )


def _card_reason(news_evidence: list[Evidence], technical_score: int, risk_score: int) -> str:
    positives = [ev.signal_zh for ev in news_evidence if ev.score > 0]
    negatives = [ev.signal_zh for ev in news_evidence if ev.score < 0]
    parts: list[str] = []
    if positives:
        parts.append("、".join(dict.fromkeys(positives[:2])))
    if technical_score >= 70:
        parts.append("技術面確認")
    elif technical_score < 55:
        parts.append("技術面偏弱")
    if negatives or risk_score < 65:
        parts.append("需控管總經風險")
    if not parts:
        parts.append("今日缺乏明確主線")
    return "；".join(parts)


def _build_card(ticker: str, news_items: list[NewsItem]) -> DecisionCard:
    profile = WATCHLIST[ticker]
    news_evidence = _news_evidence(ticker, news_items)
    tech_evidence, technical_score, technical = _technical_evidence(ticker)

    news_score = _news_score(news_evidence)
    risk_score = _risk_score(news_items, ticker, technical_score)
    radar_score = round(news_score * 0.45 + technical_score * 0.35 + risk_score * 0.20)
    radar_score = max(30, min(92, radar_score))

    decision, stance = _decision_from_score(radar_score)
    confidence = round(48 + abs(radar_score - 50) * 0.55 + len(news_evidence) * 3)
    confidence = max(50, min(94, confidence))
    reason = _card_reason(news_evidence, technical_score, risk_score)
    action, position_rule, risk_note = _build_action(stance, technical_score)

    evidence = _dedupe_evidence(news_evidence + tech_evidence)
    return DecisionCard(
        ticker=ticker,
        name=profile["name"],
        radar_score=radar_score,
        news_score=news_score,
        technical_score=technical_score,
        risk_score=risk_score,
        decision=decision,
        confidence=confidence,
        reason=reason,
        action=action,
        stance=stance,
        position_rule=position_rule,
        risk_note=risk_note,
        technical=technical,
        evidence=evidence,
    )


def build_decision(news_source: str, news_items: list[NewsItem]) -> DailyDecision:
    cards = [_build_card(ticker, news_items) for ticker in WATCHLIST]
    cards.sort(key=lambda card: (card.radar_score, card.confidence), reverse=True)
    top_cards = cards[:9]

    top5 = top_cards[:5]
    avg_score = round(sum(card.radar_score for card in top5) / len(top5))
    avg_confidence = round(sum(card.confidence for card in top5) / len(top5))
    negative_count = sum(1 for item in news_items if item.sentiment == "negative")
    buy_count = sum(1 for card in top5 if card.stance == "Buy")

    if avg_score >= 74 and buy_count >= 2 and negative_count <= 2:
        market_view = "🟢 偏多"
        today_action = "今日主線偏向 AI 與半導體，但以 Decision Card 高分標的為主，不做全面追價。"
    elif avg_score >= 63:
        market_view = "🟡 中性偏多"
        today_action = "市場有主線但仍有雜訊，優先觀察技術面已確認的個股。"
    elif avg_score >= 52:
        market_view = "🟡 中性偏保守"
        today_action = "訊號分歧，降低追價意願，等待新聞與技術面同步確認。"
    else:
        market_view = "🔴 偏空"
        today_action = "風險高於機會，優先控管部位，暫不主動追多。"

    risk_alerts = []
    if negative_count:
        risk_alerts.append("總經、利率或政策相關新聞仍可能壓抑高估值科技股。")
    risk_alerts.append("v0.8.0 已加入技術線圖與 Technical Radar，但尚未接入外資籌碼與基本面。")
    risk_alerts.append("若個股 Decision 為買進，但 RSI 過熱或開盤急拉，仍應等待拉回確認。")

    return DailyDecision(
        version=VERSION,
        news_source=news_source,
        news_count=len(news_items),
        market_view=market_view,
        ai_confidence=avg_confidence,
        today_action=today_action,
        risk_alerts=risk_alerts,
        cards=top_cards,
        news_items=news_items,
        product_note="Stage 4: Decision OS v1 combines Chinese news, technical chart, risk context and actionable Decision Cards.",
    )
