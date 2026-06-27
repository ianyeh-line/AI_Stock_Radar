"""Decision engine for AI Stock Radar MVP."""

from radar.knowledge.stock_map import WATCHLIST
from radar.models.domain import DailyDecision, NewsItem, RadarCard


def _score_stock(stock: str, news_items: list[NewsItem]) -> tuple[int, int, list[str], str]:
    score = 55
    evidence: list[str] = []
    risk = "風險可控"

    for item in news_items:
        if stock not in item.affected_stocks:
            continue

        if item.impact == "positive":
            score += 14
            evidence.append(f"{item.signal}: {item.summary}")
        elif item.impact == "negative":
            score -= 9
            risk = item.summary
            evidence.append(f"Risk - {item.signal}: {item.summary}")
        else:
            evidence.append(f"Neutral - {item.signal}: {item.summary}")

    score = max(0, min(score, 98))
    confidence = max(55, min(96, score + 4 if len(evidence) >= 2 else score - 5))
    return score, confidence, evidence, risk


def _decision(score: int) -> str:
    if score >= 85:
        return "🟢 Buy"
    if score >= 70:
        return "🟡 Watch"
    if score >= 50:
        return "⚪ Wait"
    return "🔴 Sell"


def _action(stock: str, decision: str) -> str:
    if "Buy" in decision:
        return f"{stock} 可列入今日優先觀察，等待盤中拉回且量能穩定時分批布局。"
    if "Watch" in decision:
        return f"{stock} 有主題支撐，但需要等待技術面或量能確認。"
    if "Sell" in decision:
        return f"{stock} 風險升高，若已持有應評估減碼或出場。"
    return f"{stock} 今日沒有明確優勢，暫不主動追價。"


def build_daily_decision(news_items: list[NewsItem]) -> DailyDecision:
    cards: list[RadarCard] = []
    for stock in WATCHLIST:
        score, confidence, evidence, risk = _score_stock(stock, news_items)
        decision = _decision(score)
        cards.append(
            RadarCard(
                rank=0,
                stock=stock,
                score=score,
                decision=decision,
                confidence=confidence,
                evidence=evidence or ["今日缺乏直接催化訊號。"],
                risk=risk,
                action=_action(stock, decision),
            )
        )

    cards.sort(key=lambda item: item.score, reverse=True)
    ranked_cards = [
        RadarCard(
            rank=index + 1,
            stock=card.stock,
            score=card.score,
            decision=card.decision,
            confidence=card.confidence,
            evidence=card.evidence,
            risk=card.risk,
            action=card.action,
        )
        for index, card in enumerate(cards)
    ]

    positive_count = sum(1 for item in news_items if item.impact == "positive")
    negative_count = sum(1 for item in news_items if item.impact == "negative")
    market_view = "🟢 偏多" if positive_count > negative_count else "🟡 中性偏謹慎"
    confidence = 88 if positive_count > negative_count else 68

    return DailyDecision(
        market_view=market_view,
        confidence=confidence,
        key_message="AI Infrastructure 是今日最重要主線，半導體與 AI Server 供應鏈優先於航運與非主線族群。",
        top_cards=ranked_cards[:5],
        risks=[
            "Fed 發言若偏鷹，可能壓抑高估值科技股。",
            "若開盤急拉，避免追高，等待回測支撐。",
            "目前仍為 MVP mock data，尚未接入即時市場資料。",
        ],
        actions=[
            "今日優先觀察 2330 台積電、3231 緯創、2382 廣達。",
            "高分股只在拉回且量能穩定時分批布局。",
            "非主線族群暫不主動追價。",
        ],
        news_items=news_items,
    )
