"""Explainable decision engine for AI Stock Radar."""

from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import DailyDecision, DecisionCard, Evidence, NewsItem

VERSION = "0.5.0"

POSITIVE_SIGNALS = {"AI Infrastructure", "Semiconductor Momentum"}
NEGATIVE_SIGNALS = {"Macro Risk"}


def _evidence_from_news(ticker: str, news_items: list[NewsItem]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for item in news_items:
        if ticker not in item.tickers:
            continue

        if item.sentiment == "positive":
            score = 8 if item.signal == "AI Infrastructure" else 6
            tone = "positive"
            reason = f"{item.signal} 對該股主題具支撐：{item.title[:80]}"
        elif item.sentiment == "negative":
            score = -7
            tone = "negative"
            reason = f"{item.signal} 增加短線不確定性：{item.title[:80]}"
        else:
            score = 1
            tone = "neutral"
            reason = f"訊號混合，需觀察後續確認：{item.title[:80]}"

        evidence.append(Evidence(label=item.signal, score=score, tone=tone, reason=reason, source=item.source))

    return evidence


def _add_theme_evidence(ticker: str, evidence: list[Evidence]) -> None:
    themes = WATCHLIST[ticker]["themes"]
    labels = {item.label for item in evidence}
    if "AI Infrastructure" in labels and "AI Server" in themes:
        evidence.append(Evidence("Theme Fit", 6, "positive", "該股與 AI Server / AI Infrastructure 主線高度相關"))
    if "Semiconductor Momentum" in labels and "Semiconductor" in themes:
        evidence.append(Evidence("Theme Fit", 5, "positive", "半導體族群氣氛有利於該股評價支撐"))
    if not evidence:
        evidence.append(Evidence("No Strong Signal", -4, "negative", "今日新聞主線與該股關聯度不足"))


def _decision(score: int, confidence: int) -> tuple[str, str]:
    if score >= 80 and confidence >= 78:
        return "🟢 Buy", "可列為今日優先標的；若盤中拉回且量能穩定，可分批布局。"
    if score >= 68:
        return "🟡 Watch", "具備機會但仍需確認；等待突破或回測支撐後再行動。"
    if score >= 55:
        return "⚪ Wait", "暫無足夠優勢，不建議追價；保持觀望。"
    return "🔴 Sell", "風險高於機會；若已持有可評估減碼或停損。"


def build_decision(news_source: str, news_items: list[NewsItem]) -> DailyDecision:
    cards: list[DecisionCard] = []

    for ticker, profile in WATCHLIST.items():
        evidence = _evidence_from_news(ticker, news_items)
        _add_theme_evidence(ticker, evidence)

        score = profile["base_score"] + sum(item.score for item in evidence)
        score = max(0, min(100, score))

        positive_count = sum(1 for item in evidence if item.tone == "positive")
        negative_count = sum(1 for item in evidence if item.tone == "negative")
        confidence = 58 + positive_count * 7 + negative_count * 4
        confidence = max(45, min(96, confidence))

        decision, action = _decision(score, confidence)
        top_positive = [item.label for item in evidence if item.tone == "positive"][:2]
        top_negative = [item.label for item in evidence if item.tone == "negative"][:2]
        reason = "、".join(top_positive + top_negative) or "今日缺乏明確主線"

        cards.append(
            DecisionCard(
                ticker=ticker,
                name=profile["name"],
                radar_score=score,
                decision=decision,
                confidence=confidence,
                action=action,
                reason=reason,
                evidence=evidence,
            )
        )

    cards.sort(key=lambda card: (card.radar_score, card.confidence), reverse=True)
    top_cards = cards[:5]

    avg_score = round(sum(card.radar_score for card in top_cards) / len(top_cards))
    avg_confidence = round(sum(card.confidence for card in top_cards) / len(top_cards))

    if avg_score >= 75:
        market_view = "🟢 偏多"
    elif avg_score >= 60:
        market_view = "🟡 中性偏多"
    elif avg_score >= 50:
        market_view = "🟡 中性偏保守"
    else:
        market_view = "🔴 偏空"

    risk_alerts = []
    macro_count = sum(1 for item in news_items if item.signal == "Macro Risk")
    if macro_count:
        risk_alerts.append(f"總經風險訊號 {macro_count} 則：若 Fed / 利率訊息偏鷹，高估值科技股可能承壓。")
    risk_alerts.append("若開盤急拉，避免追高；優先等待量能確認與回測支撐。")

    best = top_cards[0]
    today_action = f"今日優先關注 {best.ticker} {best.name}。{best.action}"

    return DailyDecision(
        version=VERSION,
        market_view=market_view,
        ai_confidence=avg_confidence,
        news_source=news_source,
        news_count=len(news_items),
        cards=top_cards,
        risk_alerts=risk_alerts,
        today_action=today_action,
    )
