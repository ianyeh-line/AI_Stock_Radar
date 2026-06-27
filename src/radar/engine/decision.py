"""Decision engine for AI Stock Radar Stage 5."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from radar.engine.technical import rank_macd_turn_candidates, technical_summary
from radar.models.domain import DecisionCard, Evidence, NewsItem, StockProfile


def _signal_score(stock: StockProfile, news_items: list[NewsItem]) -> tuple[int, list[Evidence]]:
    score = 0
    evidence: list[Evidence] = []
    seen: set[str] = set()

    for item in news_items:
        affected = any(stock.symbol in target or stock.name in target for target in item.affected_stocks)
        theme_hit = any(theme in item.signal for theme in stock.theme)
        sector_hit = any(stock.sector in industry for industry in item.industries)
        if not (affected or theme_hit or sector_hit):
            continue

        key = item.signal
        if key in seen:
            continue
        seen.add(key)

        if item.impact == "positive":
            weight = 10 if item.signal == "AI Infrastructure" else 7
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
            weight = -7
            score += weight
            evidence.append(
                Evidence(
                    label=item.signal,
                    direction="negative",
                    weight=abs(weight),
                    explanation=f"{item.summary_zh}，需降低追高風險。",
                )
            )

    return score, evidence


def _technical_score(stock: StockProfile) -> tuple[int, list[Evidence]]:
    score = round((stock.trend - stock.risk * 0.35) * 0.35)
    evidence: list[Evidence] = [
        Evidence(
            label="均線結構",
            direction="positive" if stock.trend >= 60 else "neutral",
            weight=max(1, round(stock.trend / 12)),
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
                explanation="MACD 已初步翻正，但仍需觀察量能是否延續。",
            )
        )

    if stock.rsi >= 68:
        score -= 8
        evidence.append(
            Evidence(
                label="RSI 偏熱",
                direction="negative",
                weight=8,
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

    return score, evidence


def _decision(score: int, risk: int) -> str:
    if score >= 82 and risk <= 45:
        return "波段買進"
    if score >= 70:
        return "波段觀察"
    if score >= 56:
        return "等待"
    return "減碼/避開"


def _manager_language(stock: StockProfile, score: int, decision: str) -> tuple[str, str, str, str, str]:
    tech = technical_summary(stock)
    if decision == "波段買進":
        swing_view = f"{stock.display_name} 目前同時具備主線題材與技術改善，適合列為波段優先標的。{stock.pm_view}"
        entry = "不追開盤急拉；等待回測 5 日或 20 日均線不破、量縮止穩時分批進場。"
        hold = "只要價格維持在 20 日均線之上，且 MACD 柱狀體持續改善，可續抱波段部位。"
        reduce = "若跌破 20 日均線且 MACD 重新擴大為負值，先降至觀察部位。"
        risk = f"主要風險：短線過熱、外部利率變數與主線退潮。技術狀態：{tech}"
    elif decision == "波段觀察":
        swing_view = f"{stock.display_name} 有波段機會，但還欠缺完整確認，不適合一次重倉。{stock.pm_view}"
        entry = "等待突破近期壓力或拉回支撐後量能回溫，再建立小部位。"
        hold = "若已持有，可續抱觀察，但不建議在未突破前加碼。"
        reduce = "若跌破整理區間低點，代表波段尚未成熟，應降低曝險。"
        risk = f"主要風險：訊號尚未完全一致。技術狀態：{tech}"
    elif decision == "等待":
        swing_view = f"{stock.display_name} 目前風險報酬比尚未達到波段進場標準。"
        entry = "等待 MACD 翻正、站回關鍵均線或出現更明確催化新聞。"
        hold = "若已持有，以小部位續抱，不主動加碼。"
        reduce = "若量縮跌破月線或主線轉弱，可先出場等待下一次訊號。"
        risk = f"主要風險：缺乏明確主線或技術確認不足。技術狀態：{tech}"
    else:
        swing_view = f"{stock.display_name} 目前不符合波段操作條件，資金效率不佳。"
        entry = "暫不建立新部位。"
        hold = "若已有部位，僅保留核心或等待反彈調節。"
        reduce = "若跌破支撐或市場風險升高，優先減碼。"
        risk = f"主要風險：趨勢未確認或下檔風險高於上檔機會。技術狀態：{tech}"
    return swing_view, entry, hold, reduce, risk


def build_decision_cards(news_items: list[NewsItem], stocks: list[StockProfile], profile: dict[str, Any]) -> list[DecisionCard]:
    cards: list[DecisionCard] = []

    for stock in stocks:
        signal_score, signal_evidence = _signal_score(stock, news_items)
        tech_score, tech_evidence = _technical_score(stock)
        base = 42
        profile_bonus = 5 if profile.get("style") == "swing_trading" and stock.macd_hist > stock.macd_hist_prev else 0
        raw_score = base + signal_score + tech_score + profile_bonus - round(stock.risk * 0.12)
        radar_score = max(1, min(96, round(raw_score)))
        decision = _decision(radar_score, stock.risk)
        confidence = max(45, min(95, round(58 + len(signal_evidence) * 7 + stock.trend * 0.22 - stock.risk * 0.18)))
        swing_view, entry, hold, reduce, risk = _manager_language(stock, radar_score, decision)
        evidence = signal_evidence + tech_evidence
        cards.append(
            DecisionCard(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                radar_score=radar_score,
                decision=decision,
                confidence=confidence,
                swing_view=swing_view,
                entry_condition=entry,
                hold_condition=hold,
                reduce_condition=reduce,
                risk_note=risk,
                evidence=evidence,
            )
        )

    return sorted(cards, key=lambda item: (item.radar_score, item.confidence), reverse=True)


def market_view(cards: list[DecisionCard], news_items: list[NewsItem]) -> tuple[str, int, str]:
    positive = sum(1 for item in news_items if item.impact == "positive")
    negative = sum(1 for item in news_items if item.impact == "negative")
    buy_or_watch = sum(1 for card in cards if card.decision in {"波段買進", "波段觀察"})
    confidence = max(50, min(92, round(58 + positive * 6 - negative * 5 + buy_or_watch * 1.2)))
    if confidence >= 82:
        return "🟢 偏多，適合精選波段標的", confidence, "主線明確，但仍以拉回承接與分批布局為主。"
    if confidence >= 68:
        return "🟡 中性偏多，等待確認", confidence, "可觀察 MACD 翻正與均線轉強標的，避免追高。"
    return "⚪ 保守觀望", confidence, "市場訊號不夠一致，先控管部位。"


def build_dashboard_payload(news_items: list[NewsItem], cards: list[DecisionCard], stocks: list[StockProfile], profile: dict[str, Any], news_source: str) -> dict[str, Any]:
    view, confidence, summary = market_view(cards, news_items)
    macd_candidates = rank_macd_turn_candidates(stocks, limit=10)

    def evidence_to_dict(evidence: Evidence) -> dict[str, Any]:
        return {
            "label": evidence.label,
            "direction": evidence.direction,
            "weight": evidence.weight,
            "explanation": evidence.explanation,
        }

    payload = {
        "version": "0.9.0",
        "news_source": news_source,
        "market_view": view,
        "ai_confidence": confidence,
        "market_summary": summary,
        "investor_profile": profile,
        "news": [item.__dict__ for item in news_items],
        "decision_cards": [
            {
                "symbol": card.symbol,
                "name": card.name,
                "sector": card.sector,
                "display_name": card.display_name,
                "radar_score": card.radar_score,
                "decision": card.decision,
                "confidence": card.confidence,
                "swing_view": card.swing_view,
                "entry_condition": card.entry_condition,
                "hold_condition": card.hold_condition,
                "reduce_condition": card.reduce_condition,
                "risk_note": card.risk_note,
                "evidence": [evidence_to_dict(item) for item in card.evidence],
            }
            for card in cards
        ],
        "macd_candidates": [candidate.__dict__ for candidate in macd_candidates],
    }
    return payload


def save_dashboard_payload(payload: dict[str, Any]) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "dashboard_data.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
