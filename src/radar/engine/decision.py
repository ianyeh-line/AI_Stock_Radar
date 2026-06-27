"""Decision engine: news -> signals -> radar decisions."""

from radar.knowledge.stock_map import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS, STOCK_KNOWLEDGE
from radar.models.domain import DailyDecision, NewsItem, StockRadar


def _text_blob(item: NewsItem) -> str:
    return f"{item.title} {item.summary}".lower()


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.lower() in text]


def _sentiment_score(news_items: list[NewsItem]) -> tuple[int, int]:
    positive = 0
    negative = 0
    for item in news_items:
        text = _text_blob(item)
        positive += len(_keyword_hits(text, POSITIVE_KEYWORDS))
        negative += len(_keyword_hits(text, NEGATIVE_KEYWORDS))
    return positive, negative


def _decision_from_score(score: int) -> str:
    if score >= 82:
        return "🟢 Buy"
    if score >= 72:
        return "🟡 Watch"
    if score >= 55:
        return "⚪ Wait"
    return "🔴 Sell"


def build_decision(news_items: list[NewsItem], live_news: bool) -> DailyDecision:
    positive_count, negative_count = _sentiment_score(news_items)
    stock_scores: list[StockRadar] = []

    for symbol, profile in STOCK_KNOWLEDGE.items():
        evidence: list[str] = []
        risk: list[str] = []
        score = 45

        for item in news_items:
            text = _text_blob(item)
            hits = _keyword_hits(text, profile["keywords"])
            if hits:
                score += min(12, 4 * len(hits))
                evidence.append(f"{item.title}（命中：{', '.join(hits[:3])}）")

            negative_hits = _keyword_hits(text, NEGATIVE_KEYWORDS)
            if negative_hits:
                score -= min(6, 2 * len(negative_hits))
                risk.append(f"{item.title}（風險：{', '.join(negative_hits[:2])}）")

        if not evidence:
            evidence.append("今日真實新聞中未出現高度直接訊號，暫以保守評估處理。")

        score = max(20, min(96, score))
        confidence = max(50, min(94, 58 + len(evidence) * 7 - len(risk) * 3))
        stock_scores.append(
            StockRadar(
                symbol=symbol,
                name=profile["name"],
                score=score,
                decision=_decision_from_score(score),
                confidence=confidence,
                evidence=evidence[:3],
                risks=risk[:2],
            )
        )

    top_stocks = sorted(stock_scores, key=lambda x: (x.score, x.confidence), reverse=True)[:5]
    market_confidence = max(55, min(92, 72 + positive_count * 2 - negative_count))

    if positive_count >= negative_count + 2:
        market_view = "🟢 偏多"
    elif negative_count > positive_count:
        market_view = "🟡 中性偏保守"
    else:
        market_view = "⚪ 中性"

    market_signals = [
        f"資料來源：{'RSS 真實新聞' if live_news else 'Fallback 新聞（RSS 暫時不可用）'}",
        f"正向訊號：{positive_count}",
        f"風險訊號：{negative_count}",
        "AI / 半導體 / AI Server 仍為第一版知識圖譜主軸。",
    ]

    risks = [
        "RSS 標題分析仍屬 v0.4 初版，尚未接入全文與即時報價。",
        "Fed、通膨與高估值科技股波動仍是今日主要風險。",
    ]

    action = "優先檢查 Top 5 是否與盤中量價同步；若開盤急拉，等待回測後再行動。"

    return DailyDecision(
        market_view=market_view,
        confidence=market_confidence,
        top_stocks=top_stocks,
        market_signals=market_signals,
        risks=risks,
        action=action,
        news_items=news_items,
    )
