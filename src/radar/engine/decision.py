"""Decision Engine for AI Stock Radar.

v1.0.0 introduces the Investment Manager Layer:
- score breakdown
- conviction labels
- position guidance
- invalidation conditions
- PM morning brief
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from radar.engine.technical import rank_macd_turn_candidates, technical_summary
from radar.models.domain import DecisionCard, Evidence, NewsItem, PMBrief, ScoreBreakdown, StockProfile


def _stock_related_to_news(stock: StockProfile, item: NewsItem) -> bool:
    if stock.symbol in " ".join(item.affected_stocks):
        return True
    if stock.name in " ".join(item.affected_stocks):
        return True
    return any(theme in item.signal or theme in " ".join(item.industries) for theme in stock.theme)


def _dedupe_evidence(items: list[Evidence]) -> list[Evidence]:
    merged: dict[tuple[str, str], Evidence] = {}
    for item in items:
        key = (item.label, item.direction)
        if key not in merged:
            merged[key] = item
            continue
        old = merged[key]
        merged[key] = Evidence(
            label=old.label,
            direction=old.direction,
            weight=max(old.weight, item.weight),
            explanation=old.explanation if len(old.explanation) >= len(item.explanation) else item.explanation,
        )
    order = {"positive": 0, "neutral": 1, "negative": 2}
    return sorted(merged.values(), key=lambda item: (order.get(item.direction, 1), -item.weight))


def _signal_score(stock: StockProfile, news_items: list[NewsItem]) -> tuple[int, list[Evidence]]:
    score = 0
    evidence: list[Evidence] = []

    for item in news_items:
        if not _stock_related_to_news(stock, item):
            continue
        if item.impact == "positive":
            if item.signal == "AI Infrastructure":
                weight = 9
            elif item.signal == "Semiconductor Momentum":
                weight = 7
            else:
                weight = 5
            score += weight
            evidence.append(
                Evidence(
                    label=item.signal,
                    direction="positive",
                    weight=weight,
                    explanation=f"{item.summary_zh} 關聯個股包含 {stock.display_name}。",
                )
            )
        elif item.impact == "negative":
            weight = -8 if item.signal == "Macro Risk" else -5
            score += weight
            evidence.append(
                Evidence(
                    label=item.signal,
                    direction="negative",
                    weight=abs(weight),
                    explanation=f"{item.summary_zh}，會壓抑波段追價意願。",
                )
            )

    return max(-18, min(26, score)), _dedupe_evidence(evidence)


def _technical_score(stock: StockProfile) -> tuple[int, list[Evidence]]:
    score = round((stock.trend - stock.risk * 0.35) * 0.32)
    evidence: list[Evidence] = [
        Evidence(
            label="均線結構",
            direction="positive" if stock.trend >= 62 else "neutral",
            weight=max(1, round(stock.trend / 13)),
            explanation=stock.ma_state,
        )
    ]

    if stock.macd_hist > stock.macd_hist_prev and stock.macd_hist <= 0.05:
        score += 8
        evidence.append(
            Evidence(
                label="MACD 即將翻正",
                direction="positive",
                weight=8,
                explanation="MACD 柱狀體由負值收斂，適合列入波段觀察清單。",
            )
        )
    elif stock.macd_hist > 0:
        score += 6
        evidence.append(
            Evidence(
                label="MACD 已翻正",
                direction="positive",
                weight=6,
                explanation="MACD 已初步翻正，但仍需確認量能與均線支撐。",
            )
        )

    if stock.rsi >= 68:
        score -= 9
        evidence.append(
            Evidence(
                label="RSI 偏熱",
                direction="negative",
                weight=9,
                explanation="短線漲幅偏大，不適合開盤追價。",
            )
        )
    elif 50 <= stock.rsi < 65:
        score += 4
        evidence.append(
            Evidence(
                label="RSI 健康",
                direction="positive",
                weight=4,
                explanation="RSI 位於波段可接受區間，尚未明顯過熱。",
            )
        )
    elif stock.rsi < 45:
        score -= 5
        evidence.append(
            Evidence(
                label="RSI 偏弱",
                direction="negative",
                weight=5,
                explanation="買盤強度仍不足，需等待止穩確認。",
            )
        )

    return max(-10, min(34, score)), _dedupe_evidence(evidence)


def _decision(score: int, risk: int) -> str:
    if score >= 82 and risk <= 42:
        return "波段買進"
    if score >= 70:
        return "波段觀察"
    if score >= 56:
        return "等待"
    return "減碼/避開"


def _conviction(score: int, confidence: int, risk: int) -> str:
    if score >= 84 and confidence >= 82 and risk <= 38:
        return "高信念"
    if score >= 72 and confidence >= 70:
        return "中高信念"
    if score >= 58:
        return "低信念觀察"
    return "不具信念"


def _position_guidance(decision: str, conviction: str) -> str:
    if decision == "波段買進" and conviction == "高信念":
        return "可作為今日主攻標的，但仍採 2 到 3 批布局，單日不追滿部位。"
    if decision == "波段買進":
        return "可建立小到中部位，優先等待拉回承接。"
    if decision == "波段觀察":
        return "列入觀察名單，小部位試單或等待突破確認。"
    if decision == "等待":
        return "不新增部位，若已持有則以關鍵均線作為續抱依據。"
    return "不建立新部位，既有部位反彈優先調節。"


def _manager_language(stock: StockProfile, score: int, decision: str) -> tuple[str, str, str, str, str, str]:
    tech = technical_summary(stock)
    if decision == "波段買進":
        swing_view = f"{stock.display_name} 同時具備主線題材與技術改善，是今日波段優先標的。{stock.pm_view}"
        entry = "不追開盤急拉；等待回測 5 日或 20 日均線不破、量縮止穩時分批進場。"
        hold = "只要價格維持在 20 日均線之上，且 MACD 柱狀體持續改善，可續抱波段部位。"
        reduce = "若跌破 20 日均線且 MACD 重新擴大為負值，先降至觀察部位。"
        invalidation = "跌破月線、MACD 轉弱且主線新聞降溫，原波段假設失效。"
        risk = f"主要風險：短線過熱、外部利率變數與主線退潮。技術狀態：{tech}"
    elif decision == "波段觀察":
        swing_view = f"{stock.display_name} 有波段機會，但訊號尚未完全一致，不適合一次重倉。{stock.pm_view}"
        entry = "等待突破近期壓力或拉回支撐後量能回溫，再建立小部位。"
        hold = "若已持有，可續抱觀察，但不建議在未突破前加碼。"
        reduce = "若跌破整理區間低點，代表波段尚未成熟，應降低曝險。"
        invalidation = "跌破整理區間低點且 MACD 改善失敗，移出優先觀察名單。"
        risk = f"主要風險：訊號尚未完全一致。技術狀態：{tech}"
    elif decision == "等待":
        swing_view = f"{stock.display_name} 目前風險報酬比尚未達到波段進場標準。"
        entry = "等待 MACD 翻正、站回關鍵均線或出現更明確催化新聞。"
        hold = "若已持有，以小部位續抱，不主動加碼。"
        reduce = "若量縮跌破月線或主線轉弱，可先出場等待下一次訊號。"
        invalidation = "沒有明確主線且技術指標未改善，持續不列入主攻名單。"
        risk = f"主要風險：缺乏明確主線或技術確認不足。技術狀態：{tech}"
    else:
        swing_view = f"{stock.display_name} 目前不符合波段操作條件，資金效率不佳。"
        entry = "暫不建立新部位。"
        hold = "若已有部位，僅保留核心或等待反彈調節。"
        reduce = "若跌破支撐或市場風險升高，優先減碼。"
        invalidation = "需重新站回月線並出現 MACD 改善，才可重新評估。"
        risk = f"主要風險：趨勢未確認或下檔風險高於上檔機會。技術狀態：{tech}"
    return swing_view, entry, hold, reduce, invalidation, risk


def build_decision_cards(news_items: list[NewsItem], stocks: list[StockProfile], profile: dict[str, Any]) -> list[DecisionCard]:
    cards: list[DecisionCard] = []

    for stock in stocks:
        signal_score, signal_evidence = _signal_score(stock, news_items)
        technical_score, tech_evidence = _technical_score(stock)
        base = 40
        profile_bonus = 4 if profile.get("style") == "swing_trading" and stock.macd_hist > stock.macd_hist_prev else 0
        risk_penalty = round(stock.risk * 0.16)
        raw_score = base + signal_score + technical_score + profile_bonus - risk_penalty
        radar_score = max(1, min(94, round(raw_score)))
        decision = _decision(radar_score, stock.risk)
        evidence = _dedupe_evidence(signal_evidence + tech_evidence)
        confidence = max(45, min(93, round(54 + len(evidence) * 5.5 + stock.trend * 0.18 - stock.risk * 0.2)))
        conviction = _conviction(radar_score, confidence, stock.risk)
        swing_view, entry, hold, reduce, invalidation, risk = _manager_language(stock, radar_score, decision)
        breakdown = ScoreBreakdown(
            base=base,
            news_signal=signal_score,
            technical=technical_score,
            profile_bonus=profile_bonus,
            risk_penalty=risk_penalty,
            final_score=radar_score,
        )
        cards.append(
            DecisionCard(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                radar_score=radar_score,
                decision=decision,
                confidence=confidence,
                conviction=conviction,
                swing_view=swing_view,
                entry_condition=entry,
                hold_condition=hold,
                reduce_condition=reduce,
                invalidation_condition=invalidation,
                risk_note=risk,
                position_guidance=_position_guidance(decision, conviction),
                score_breakdown=breakdown,
                evidence=evidence,
            )
        )

    return sorted(cards, key=lambda item: (item.radar_score, item.confidence), reverse=True)


def market_view(cards: list[DecisionCard], news_items: list[NewsItem]) -> tuple[str, int, str]:
    positive = sum(1 for item in news_items if item.impact == "positive")
    negative = sum(1 for item in news_items if item.impact == "negative")
    buy_or_watch = sum(1 for card in cards if card.decision in {"波段買進", "波段觀察"})
    confidence = max(50, min(92, round(56 + positive * 5 - negative * 5 + buy_or_watch * 1.1)))
    if confidence >= 82:
        return "🟢 偏多，適合精選波段標的", confidence, "主線明確，但仍以拉回承接與分批布局為主。"
    if confidence >= 68:
        return "🟡 中性偏多，等待確認", confidence, "可觀察 MACD 翻正與均線轉強標的，避免追高。"
    return "⚪ 保守觀望", confidence, "市場訊號不夠一致，先控管部位。"


def _build_pm_brief(cards: list[DecisionCard], news_items: list[NewsItem], news_source: str, confidence: int) -> PMBrief:
    buys = [card for card in cards if card.decision == "波段買進"]
    watches = [card for card in cards if card.decision == "波段觀察"]
    avoids = [card for card in cards if card.decision == "減碼/避開"]
    positives = sum(1 for item in news_items if item.impact == "positive")
    negatives = sum(1 for item in news_items if item.impact == "negative")
    top = buys[:2] + watches[: max(0, 3 - len(buys[:2]))]
    if buys:
        headline = f"今日主策略：聚焦 {buys[0].sector} 主線，但用拉回承接取代追高。"
        strategy = "偏多操作，但以波段分批布局為主；先挑高信念標的，不擴大到弱勢股。"
        capital = "建議新資金投入 30% 到 45%，保留現金等待盤中回測；單一個股不超過計畫資金 15%。"
    elif watches:
        headline = "今日主策略：訊號偏多但未完全確認，優先建立觀察清單。"
        strategy = "以小部位試單或等待突破確認為主，不做重倉追價。"
        capital = "建議新資金投入 10% 到 25%，以技術轉強股為主，保留大部分現金。"
    else:
        headline = "今日主策略：市場缺乏高信念標的，保守等待。"
        strategy = "不急於進場，先保護資金效率與下檔風險。"
        capital = "建議新資金投入 0% 到 10%，以觀察為主。"

    top_actions = [f"{card.display_name}：{card.decision}；{card.position_guidance}" for card in top[:3]] or ["今日沒有高信念波段買進標的。"]
    avoid_actions = [f"{card.display_name}：{card.risk_note}" for card in avoids[:3]] or ["沒有明確需要主動避開的核心標的，但仍避免追高。"]
    risk_controls = [
        "任何標的若跌破月線且 MACD 轉弱，先降部位而不是加碼攤平。",
        "開盤急拉不追；只在拉回支撐且量能健康時分批布局。",
        "若總經新聞轉鷹或美股科技股轉弱，當日新部位降低一半。",
    ]
    data_quality = {
        "news_source": news_source,
        "news_items": len(news_items),
        "positive_signals": positives,
        "negative_signals": negatives,
        "confidence": confidence,
        "limitation": "目前新聞與技術資料仍屬 MVP；正式交易前需再確認即時價格、成交量與法人籌碼。",
    }
    return PMBrief(
        headline=headline,
        strategy=strategy,
        capital_allocation=capital,
        top_actions=top_actions,
        avoid_actions=avoid_actions,
        risk_controls=risk_controls,
        data_quality=data_quality,
    )


def _evidence_to_dict(evidence: Evidence) -> dict[str, Any]:
    return {
        "label": evidence.label,
        "direction": evidence.direction,
        "weight": evidence.weight,
        "explanation": evidence.explanation,
    }


def _card_to_dict(card: DecisionCard) -> dict[str, Any]:
    return {
        "symbol": card.symbol,
        "name": card.name,
        "sector": card.sector,
        "display_name": card.display_name,
        "radar_score": card.radar_score,
        "decision": card.decision,
        "confidence": card.confidence,
        "conviction": card.conviction,
        "swing_view": card.swing_view,
        "entry_condition": card.entry_condition,
        "hold_condition": card.hold_condition,
        "reduce_condition": card.reduce_condition,
        "invalidation_condition": card.invalidation_condition,
        "risk_note": card.risk_note,
        "position_guidance": card.position_guidance,
        "score_breakdown": card.score_breakdown.as_dict(),
        "evidence": [_evidence_to_dict(item) for item in card.evidence],
    }


def _pm_brief_to_dict(brief: PMBrief) -> dict[str, Any]:
    return {
        "headline": brief.headline,
        "strategy": brief.strategy,
        "capital_allocation": brief.capital_allocation,
        "top_actions": brief.top_actions,
        "avoid_actions": brief.avoid_actions,
        "risk_controls": brief.risk_controls,
        "data_quality": brief.data_quality,
    }


def build_dashboard_payload(news_items: list[NewsItem], cards: list[DecisionCard], stocks: list[StockProfile], profile: dict[str, Any], news_source: str) -> dict[str, Any]:
    view, confidence, summary = market_view(cards, news_items)
    macd_candidates = rank_macd_turn_candidates(stocks, limit=10)
    brief = _build_pm_brief(cards, news_items, news_source, confidence)
    payload = {
        "version": "1.0.0",
        "stage": "Investment Manager Release",
        "news_source": news_source,
        "market_view": view,
        "ai_confidence": confidence,
        "market_summary": summary,
        "investor_profile": profile,
        "pm_brief": _pm_brief_to_dict(brief),
        "news": [item.__dict__ for item in news_items],
        "decision_cards": [_card_to_dict(card) for card in cards],
        "macd_candidates": [candidate.__dict__ for candidate in macd_candidates],
    }
    return payload


def save_dashboard_payload(payload: dict[str, Any]) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "dashboard_data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
