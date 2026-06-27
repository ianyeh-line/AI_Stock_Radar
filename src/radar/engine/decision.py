"""Decision OS with PM-style numeric operating levels."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
import json

from radar.datasource.rss_news import fetch_rss_news
from radar.datasource.yahoo_price import load_price_bars
from radar.datasource.institutional_flow import InstitutionalFlowProfile, load_institutional_flows
from radar.engine.backtest import build_backtest_summary
from radar.engine.data_trust import assess_card_guardrails, build_data_trust_summary
from radar.engine.personalization import load_investor_profile
from radar.engine.user_space import build_portfolio_analysis, build_portfolio_coach, load_portfolio, load_user_watchlist
from radar.engine.technical import evaluate_technical, rank_macd_turn_candidates
from radar.knowledge.stock_map import load_stock_universe
from radar.models.domain import DecisionCard, Evidence, NewsItem, PMBrief, ScoreBreakdown, StockMeta, TechnicalProfile

VERSION = "2.3.0"


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


def _stock_related_to_news(stock: StockMeta, item: NewsItem) -> bool:
    affected = " ".join(item.affected_stocks)
    if stock.symbol in affected or stock.name in affected:
        return True
    haystack = " ".join([item.signal, item.title, item.title_zh, item.summary_zh, " ".join(item.industries)]).lower()
    return any(theme.lower() in haystack for theme in stock.theme)


def _news_score(stock: StockMeta, news_items: list[NewsItem]) -> tuple[int, list[Evidence]]:
    score = 0
    evidence: list[Evidence] = []
    for item in news_items:
        if not _stock_related_to_news(stock, item):
            continue
        if item.impact == "positive":
            weight = 9 if item.signal == "AI Infrastructure" else 7 if item.signal == "Semiconductor Momentum" else 4
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
            weight = 8 if item.signal == "Macro Risk" else 5
            score -= weight
            evidence.append(
                Evidence(
                    label=item.signal,
                    direction="negative",
                    weight=weight,
                    explanation=f"{item.summary_zh}，會降低追價意願。",
                )
            )
    return max(-20, min(28, score)), _dedupe_evidence(evidence)


def _technical_component(profile: TechnicalProfile) -> tuple[int, list[Evidence]]:
    component = round((profile.trend_score - 50) * 0.45)
    component = max(-14, min(36, component))
    evidence: list[Evidence] = [
        Evidence(
            label="均線結構",
            direction="positive" if profile.trend_score >= 62 else "neutral" if profile.trend_score >= 48 else "negative",
            weight=max(1, round(profile.trend_score / 12)),
            explanation=profile.ma_state,
        )
    ]
    if profile.macd_hist > 0 and profile.macd_hist > profile.macd_hist_prev:
        evidence.append(Evidence("MACD 動能轉強", "positive", 8, "MACD 位於正值且柱狀體擴大，波段動能延續。"))
    elif profile.macd_hist > profile.macd_hist_prev:
        evidence.append(Evidence("MACD 接近翻正", "positive", 7, "MACD 柱狀體改善，適合列入波段觀察。"))
    else:
        evidence.append(Evidence("MACD 動能轉弱", "negative", 6, "MACD 柱狀體收斂或惡化，追價需保守。"))

    if 45 <= profile.rsi <= 65:
        evidence.append(Evidence("RSI 健康", "positive", 5, "RSI 位於波段可接受區間，尚未明顯過熱。"))
    elif profile.rsi > 70:
        evidence.append(Evidence("RSI 過熱", "negative", 8, "RSI 偏高，開盤急拉不宜追價。"))
    elif profile.rsi < 42:
        evidence.append(Evidence("RSI 偏弱", "negative", 5, "買盤強度不足，需要等待止穩。"))

    volume_note = _volume_ratio_note(profile.volume_ratio)
    if profile.volume_ratio >= 1.2:
        evidence.append(Evidence("量能放大", "positive", 5, volume_note))
    elif profile.volume_ratio < 0.7:
        evidence.append(Evidence("量能不足", "negative", 4, volume_note))
    else:
        evidence.append(Evidence("量能正常", "neutral", 3, volume_note))

    if profile.price_source.startswith("Yahoo Finance"):
        evidence.append(Evidence("真實價格資料", "positive", 4, "技術指標由 Yahoo Finance 日線資料計算。"))
    else:
        evidence.append(Evidence("價格資料限制", "neutral", 3, "真實價格資料暫不可用，已使用 fallback price model。"))
    return component, _dedupe_evidence(evidence)


def _institutional_component(flow: InstitutionalFlowProfile | None) -> tuple[int, list[Evidence]]:
    if flow is None:
        return 0, [Evidence("法人籌碼", "neutral", 1, "尚未取得三大法人資料，籌碼不列入主要評分。")]
    component = max(-16, min(16, int(flow.flow_score)))
    direction = "positive" if component >= 4 else "negative" if component <= -4 else "neutral"
    weight = max(2, min(10, abs(component))) if direction != "neutral" else 2
    return component, [Evidence("三大法人籌碼", direction, weight, flow.summary)]


def _decision(score: int, risk: int) -> str:
    if score >= 82 and risk <= 52:
        return "波段買進"
    if score >= 70:
        return "波段觀察"
    if score >= 56:
        return "等待"
    return "減碼/避開"


def _conviction(score: int, confidence: int, risk: int) -> str:
    if score >= 84 and confidence >= 82 and risk <= 45:
        return "高信念"
    if score >= 72 and confidence >= 70:
        return "中高信念"
    if score >= 58:
        return "低信念觀察"
    return "不具信念"


def _position_guidance(decision: str, conviction: str) -> str:
    if decision == "波段買進" and conviction == "高信念":
        return "可作為今日主攻標的，但採 2 到 3 批布局，避免一次追滿。"
    if decision == "波段買進":
        return "可建立小到中部位，等待拉回支撐時分批。"
    if decision == "波段觀察":
        return "列入觀察清單，等突破或拉回確認後再提高部位。"
    if decision == "等待":
        return "不新增部位；若已持有，依 20 日或 60 日均線管理。"
    return "不建立新部位；既有部位反彈優先調節。"


def _round_price(value: float) -> float:
    if value >= 1000:
        step = 5
    elif value >= 500:
        step = 1
    elif value >= 100:
        step = 0.5
    elif value >= 50:
        step = 0.1
    else:
        step = 0.05
    return round(round(value / step) * step, 2)


def _price_levels(profile: TechnicalProfile) -> dict[str, float]:
    history = profile.history or []
    recent = history[-22:] if len(history) >= 22 else history
    recent_high = max((float(row.get("high") or profile.latest_close) for row in recent), default=profile.latest_close)
    recent_low = min((float(row.get("low") or profile.latest_close) for row in recent), default=profile.latest_close)
    structural_support = profile.ma20 if profile.ma20 > 0 else profile.latest_close * 0.96
    mid_support = profile.ma60 if profile.ma60 > 0 else structural_support * 0.94
    pullback_mid = structural_support if profile.latest_close >= structural_support else max(recent_low, mid_support)
    pullback_low = min(pullback_mid * 0.985, pullback_mid)
    pullback_high = max(pullback_mid * 1.015, pullback_mid)
    breakout = max(recent_high * 1.005, profile.latest_close * 1.018)
    reduce = min(structural_support * 0.985, profile.latest_close * 0.965)
    stop = min(mid_support * 0.975, profile.latest_close * 0.93)
    return {
        "breakout": _round_price(breakout),
        "pullback_low": _round_price(pullback_low),
        "pullback_high": _round_price(pullback_high),
        "reduce": _round_price(reduce),
        "stop": _round_price(stop),
    }


def _volume_ratio_note(ratio: float) -> str:
    if ratio >= 1.25:
        tone = "量能明顯放大，代表今日成交量約為 20 日均量的 {ratio:.0%}，有利突破確認，但也要避免爆量長黑。"
    elif ratio >= 1.05:
        tone = "量能溫和放大，代表今日成交量約為 20 日均量的 {ratio:.0%}；例如 1.07 就是比 20 日均量多 7%，屬於健康確認。"
    elif ratio >= 0.85:
        tone = "量能接近常態，代表今日成交量約為 20 日均量的 {ratio:.0%}，訊號有效但攻擊力普通。"
    else:
        tone = "量能低於常態，代表今日成交量約為 20 日均量的 {ratio:.0%}，突破可信度不足。"
    return f"量能比 {ratio:.2f}：" + tone.format(ratio=ratio)


def _level_context(profile: TechnicalProfile, levels: dict[str, float]) -> dict[str, Any]:
    close = float(profile.latest_close or 0)
    breakout = float(levels["breakout"])
    pullback_low = float(levels["pullback_low"])
    pullback_high = float(levels["pullback_high"])
    reduce_price = float(levels["reduce"])
    stop_price = float(levels["stop"])
    in_pullback_zone = pullback_low <= close <= pullback_high
    below_support = close < pullback_low
    between_support_and_breakout = pullback_high < close < breakout
    above_breakout = close >= breakout
    return {
        "close": close,
        "breakout": breakout,
        "pullback_low": pullback_low,
        "pullback_high": pullback_high,
        "reduce_price": reduce_price,
        "stop_price": stop_price,
        "in_pullback_zone": in_pullback_zone,
        "below_support": below_support,
        "between_support_and_breakout": between_support_and_breakout,
        "above_breakout": above_breakout,
    }


def _entry_text_for_non_buy(ctx: dict[str, Any], required_label: str = "重新評估") -> str:
    close = ctx["close"]
    breakout = ctx["breakout"]
    pullback_low = ctx["pullback_low"]
    pullback_high = ctx["pullback_high"]
    if ctx["below_support"]:
        return (
            f"現價 {close:.2f} 仍低於波段支撐區 {pullback_low:.2f}～{pullback_high:.2f}，"
            f"暫不建立新部位；需先站回 {pullback_high:.2f}，再放量突破 {breakout:.2f} 才{required_label}。"
        )
    if ctx["in_pullback_zone"]:
        return (
            f"現價 {close:.2f} 位於拉回觀察區 {pullback_low:.2f}～{pullback_high:.2f}，"
            f"但整體訊號尚未達買進標準；需量縮守穩此區，或放量突破 {breakout:.2f} 才{required_label}。"
        )
    if ctx["between_support_and_breakout"]:
        return (
            f"現價 {close:.2f} 已高於支撐區 {pullback_low:.2f}～{pullback_high:.2f}，"
            f"但尚未突破關鍵壓力 {breakout:.2f}；不追高，等待突破 {breakout:.2f} 或回測支撐區守穩再{required_label}。"
        )
    return (
        f"現價 {close:.2f} 已站上突破價 {breakout:.2f}，但目前決策分數或風險條件不足；"
        f"等待回測 {pullback_low:.2f}～{pullback_high:.2f} 不破，或量能延續確認後再{required_label}。"
    )


def _manager_language(stock: StockMeta, profile: TechnicalProfile, decision: str, levels: dict[str, float], volume_note: str) -> tuple[str, str, str, str, str, str]:
    ctx = _level_context(profile, levels)
    breakout = ctx["breakout"]
    pullback_low = ctx["pullback_low"]
    pullback_high = ctx["pullback_high"]
    reduce_price = ctx["reduce_price"]
    stop_price = ctx["stop_price"]
    close = ctx["close"]

    if decision == "波段買進":
        swing_view = f"{stock.display_name} 具備主線或技術改善，是今日波段優先標的。{stock.pm_view}"
        if ctx["in_pullback_zone"]:
            entry = f"現價 {close:.2f} 位於建議拉回區 {pullback_low:.2f}～{pullback_high:.2f}，若量縮守穩可分批進場；若放量突破 {breakout:.2f}，可追蹤第二批。"
        elif ctx["below_support"]:
            entry = f"現價 {close:.2f} 仍低於理想拉回區，先等站回 {pullback_low:.2f}～{pullback_high:.2f} 且量能改善，再分批進場；突破確認價為 {breakout:.2f}。"
        elif ctx["between_support_and_breakout"]:
            entry = f"現價 {close:.2f} 已離開拉回區但尚未突破 {breakout:.2f}；不追高，等待回測 {pullback_low:.2f}～{pullback_high:.2f}，或放量突破 {breakout:.2f} 後再小量追蹤。"
        else:
            entry = f"現價 {close:.2f} 已站上突破價 {breakout:.2f}，只適合續抱或等回測不破再加碼，不建議開盤急追。"
        hold = f"只要守住 {pullback_low:.2f}～{pullback_high:.2f} 支撐區且 MACD 未轉弱，可續抱波段部位。"
        reduce = f"若跌破 {reduce_price:.2f} 且 MACD 柱狀體連續轉弱，先降低 30%～50% 部位。"
        invalidation = f"跌破 {stop_price:.2f}、MACD 轉弱且新聞主線降溫，波段假設失效。"
    elif decision == "波段觀察":
        swing_view = f"{stock.display_name} 有波段機會，但訊號尚未完全一致，不適合重倉。{stock.pm_view}"
        if ctx["in_pullback_zone"]:
            entry = f"現價 {close:.2f} 位於觀察支撐區 {pullback_low:.2f}～{pullback_high:.2f}，可等量縮止穩後小部位試單；若突破 {breakout:.2f} 再提高信心。"
        elif ctx["between_support_and_breakout"]:
            entry = f"現價 {close:.2f} 高於支撐但未突破 {breakout:.2f}；先觀察，不追高，等待突破 {breakout:.2f} 或回測 {pullback_low:.2f}～{pullback_high:.2f} 再試單。"
        elif ctx["below_support"]:
            entry = f"現價 {close:.2f} 低於觀察支撐區，先等站回 {pullback_high:.2f}，再看是否突破 {breakout:.2f}。"
        else:
            entry = f"現價 {close:.2f} 已高於突破價 {breakout:.2f}，但訊號尚未完全一致；若已持有可續抱，未持有等回測 {pullback_high:.2f} 附近再評估。"
        hold = f"若已持有，可續抱觀察；未突破 {breakout:.2f} 前不主動加碼。"
        reduce = f"若跌破 {reduce_price:.2f}，代表整理失敗，應降低曝險。"
        invalidation = f"跌破 {stop_price:.2f} 且量能低於 20 日均量，移出優先觀察名單。"
    elif decision == "等待":
        swing_view = f"{stock.display_name} 目前風險報酬比尚未達到波段進場標準。"
        entry = _entry_text_for_non_buy(ctx, "重新評估")
        hold = f"若已持有，以小部位續抱，不主動加碼；防守觀察 {reduce_price:.2f}。"
        reduce = f"若量縮跌破 {reduce_price:.2f} 或主線轉弱，可先出場等待。"
        invalidation = f"跌破 {stop_price:.2f} 且沒有明確主線，持續不列入主攻。"
    else:
        swing_view = f"{stock.display_name} 目前不符合波段操作條件，資金效率不佳。"
        entry = _entry_text_for_non_buy(ctx, "解除減碼觀點")
        hold = f"若已有部位，僅保留核心或等待反彈至 {pullback_high:.2f}～{breakout:.2f} 區間調節。"
        reduce = f"若跌破 {reduce_price:.2f} 或反彈無量，優先減碼。"
        invalidation = f"需重新突破 {breakout:.2f} 並出現 MACD 改善，才可解除減碼觀點。"
    risk = f"主要風險：市場風格切換、利率變數、短線過熱或技術轉弱。技術狀態：{profile.technical_summary}。{volume_note}"
    return swing_view, entry, hold, reduce, invalidation, risk

def build_decision_cards(news_items: list[NewsItem], stocks: list[StockMeta], profiles: dict[str, TechnicalProfile], profile_config: dict[str, Any], institutional_flows: dict[str, InstitutionalFlowProfile] | None = None) -> list[DecisionCard]:
    cards: list[DecisionCard] = []
    for stock in stocks:
        technical = profiles[stock.symbol]
        flow = (institutional_flows or {}).get(stock.symbol)
        news_score, news_evidence = _news_score(stock, news_items)
        technical_score, technical_evidence = _technical_component(technical)
        institutional_score, institutional_evidence = _institutional_component(flow)
        base = 42 + min(6, stock.base_priority // 2)
        profile_bonus = 4 if profile_config.get("style") == "swing_trading" and technical.macd_hist > technical.macd_hist_prev else 0
        price_quality = 4 if technical.price_source.startswith("Yahoo Finance") else -4
        risk_penalty = round(technical.risk_score * 0.16)
        raw = base + news_score + technical_score + institutional_score + profile_bonus + price_quality - risk_penalty
        radar_score = max(1, min(94, round(raw)))
        decision = _decision(radar_score, technical.risk_score)
        evidence = _dedupe_evidence(news_evidence + technical_evidence + institutional_evidence)
        flow_quality_bonus = 5 if flow and flow.source.startswith("TWSE") else -2 if flow else -4
        confidence = max(45, min(94, round(50 + len(evidence) * 4.1 + technical.trend_score * 0.2 - technical.risk_score * 0.16 + (5 if technical.price_source.startswith("Yahoo Finance") else -6) + flow_quality_bonus)))
        conviction = _conviction(radar_score, confidence, technical.risk_score)
        levels = _price_levels(technical)
        volume_note = _volume_ratio_note(technical.volume_ratio)
        swing_view, entry, hold, reduce, invalidation, risk = _manager_language(stock, technical, decision, levels, volume_note)
        breakdown = ScoreBreakdown(base, news_score, technical_score, institutional_score, profile_bonus, price_quality, risk_penalty, radar_score)
        cards.append(
            DecisionCard(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                radar_score=radar_score,
                decision=decision,
                confidence=confidence,
                conviction=conviction,
                latest_close=technical.latest_close,
                change_pct=technical.change_pct,
                price_source=technical.price_source,
                swing_view=swing_view,
                entry_condition=entry,
                hold_condition=hold,
                reduce_condition=reduce,
                invalidation_condition=invalidation,
                risk_note=risk,
                position_guidance=_position_guidance(decision, conviction),
                breakout_price=levels["breakout"],
                pullback_low=levels["pullback_low"],
                pullback_high=levels["pullback_high"],
                reduce_price=levels["reduce"],
                stop_loss_price=levels["stop"],
                volume_ratio_note=volume_note,
                institutional_summary=flow.summary if flow else "尚未取得法人籌碼資料。",
                institutional_source=flow.source if flow else "N/A",
                score_breakdown=breakdown,
                institutional_flow=flow.as_dict() if flow else {},
                evidence=evidence,
            )
        )
    return sorted(cards, key=lambda item: (item.radar_score, item.confidence), reverse=True)


def _market_view(cards: list[DecisionCard], news_items: list[NewsItem]) -> str:
    top_avg = sum(card.radar_score for card in cards[:5]) / max(1, len(cards[:5]))
    positive = sum(1 for item in news_items if item.impact == "positive")
    negative = sum(1 for item in news_items if item.impact == "negative")
    if top_avg >= 76 and positive >= negative:
        return "🟢 偏多"
    if top_avg >= 66:
        return "🟡 中性偏多"
    if negative > positive + 1:
        return "🟠 中性偏保守"
    return "⚪ 中性"


def _ai_confidence(cards: list[DecisionCard], news_items: list[NewsItem], profiles: dict[str, TechnicalProfile]) -> int:
    avg_conf = sum(card.confidence for card in cards[:5]) / max(1, len(cards[:5]))
    live_prices = sum(1 for profile in profiles.values() if profile.price_source.startswith("Yahoo Finance"))
    live_bonus = min(8, live_prices)
    news_bonus = min(6, len(news_items) // 2)
    return max(45, min(94, round(avg_conf * 0.74 + live_bonus + news_bonus)))


def _build_pm_brief(cards: list[DecisionCard], news_items: list[NewsItem], profiles: dict[str, TechnicalProfile], institutional_flows: dict[str, InstitutionalFlowProfile], news_source: str, market_view: str, confidence: int, user_watchlist_count: int, portfolio_count: int) -> PMBrief:
    buys = [card for card in cards if card.decision == "波段買進"]
    watches = [card for card in cards if card.decision == "波段觀察"]
    sells = [card for card in cards if card.decision == "減碼/避開"]
    live_prices = sum(1 for profile in profiles.values() if profile.price_source.startswith("Yahoo Finance"))
    fallback_prices = len(profiles) - live_prices
    price_dates = sorted({profile.latest_date for profile in profiles.values() if profile.latest_date})
    price_latest_date_min = price_dates[0] if price_dates else "N/A"
    price_latest_date_max = price_dates[-1] if price_dates else "N/A"
    positive = sum(1 for item in news_items if item.impact == "positive")
    negative = sum(1 for item in news_items if item.impact == "negative")
    institutional_official = sum(1 for flow in institutional_flows.values() if flow.source.startswith("TWSE"))
    institutional_fallback = len(institutional_flows) - institutional_official

    if buys:
        headline = f"今日主策略：以 {buys[0].display_name} 等高信念標的作為波段主攻，仍採分批進場。"
        strategy = "資金優先集中在同時具備主線題材與技術改善的個股；若開盤急拉，等待回測均線或量縮止穩。"
        allocation = "建議股票曝險 50%～65%，單一股票不超過個人風險上限，保留 35%～50% 現金等待拉回。"
        recommendation_pool = buys[:5]
    elif watches:
        headline = "今日主策略：市場有機會但訊號未完全一致，以觀察與小部位試單為主。"
        strategy = "等待 MACD、均線與量能進一步確認；不在沒有支撐的位置追價。"
        allocation = "建議股票曝險 35%～50%，現金維持 50% 以上。"
        recommendation_pool = watches[:5]
    else:
        headline = "今日主策略：市場缺乏高信念標的，先保護資金效率。"
        strategy = "不強迫交易，等待更明確的價格與新聞催化。"
        allocation = "建議股票曝險 20%～35%，以防禦與現金為主。"
        recommendation_pool = cards[:5]

    recommended_stocks = [
        {
            "symbol": card.symbol,
            "name": card.name,
            "display_name": card.display_name,
            "decision": card.decision,
            "radar_score": card.radar_score,
            "confidence": card.confidence,
            "breakout_price": card.breakout_price,
            "pullback_low": card.pullback_low,
            "pullback_high": card.pullback_high,
            "reason": f"{card.conviction}｜Radar {card.radar_score}｜突破 {card.breakout_price:.2f} 或拉回 {card.pullback_low:.2f}～{card.pullback_high:.2f} 再處理。",
        }
        for card in recommendation_pool
    ]
    if recommended_stocks:
        names = "、".join(item["display_name"] for item in recommended_stocks[:3])
        strategy += f" 今日推薦優先觀察：{names}。"

    top_actions = [
        f"{card.display_name}：突破 {card.breakout_price:.2f} 可追蹤；拉回 {card.pullback_low:.2f}～{card.pullback_high:.2f} 量縮止穩可分批；跌破 {card.reduce_price:.2f} 先降曝險。法人籌碼：{card.institutional_summary}"
        for card in cards[:3]
    ]
    avoid_actions = [
        f"避免追高：{card.display_name} 若未突破 {card.breakout_price:.2f} 且量能比低於 1.00，不做追價；跌破 {card.reduce_price:.2f} 優先減碼。"
        for card in cards if card.confidence < 62 or card.decision == "減碼/避開"
    ][:3]
    if not avoid_actions:
        avoid_actions = ["避免開盤急拉追價；所有波段進場都需等待支撐、突破價與量能確認。"]

    risk_controls = [
        "單一股票不超過預設部位上限，避免 AI 主線過度集中。",
        "若 Fed、利率或美股科技股轉弱，需降低高估值科技曝險。",
        "若個股跌破減碼價且 MACD 轉弱，先降低部位，不與趨勢對作。",
    ]
    quality = {
        "news_source": news_source,
        "news_items": len(news_items),
        "positive_signals": positive,
        "negative_signals": negative,
        "price_live_count": live_prices,
        "price_fallback_count": fallback_prices,
        "confidence": confidence,
        "user_watchlist_count": user_watchlist_count,
        "portfolio_count": portfolio_count,
        "institutional_official_count": institutional_official,
        "institutional_fallback_count": institutional_fallback,
        "institutional_source": "TWSE T86 三大法人（若官方端點不可用則啟用 fallback flow model）",
        "institutional_frequency": "每次重新產生 Radar 時，嘗試抓取 TWSE 最新可得交易日三大法人買賣超；若尚未公布或抓取失敗，改以量價推估並降低信心。",
        "price_frequency": "使用 Yahoo Finance 最新可得日線資料；v2.2.4 採同日快取優先、並行抓取、價格位置語句修正與個人資料永久保存，按『重新抓取最新資料』會更新缺失/過期資料，不是逐筆即時報價。",
        "news_frequency": "RSS 於每次重新產生 Radar 時更新，非付費即時新聞終端。",
        "price_latest_date_min": price_latest_date_min,
        "price_latest_date_max": price_latest_date_max,
        "decision_scope": "目前以抓取當下最新可得日線價格、技術指標、RSS 新聞影響鏈、三大法人籌碼、AI 產業鏈股票池、使用者觀察與持股為主要維度；尚未納入逐筆即時成交、財報估值模型與券商研究報告。",
        "limitation": "目前不是逐筆即時交易系統；價格以執行當下抓取到的日線資料為準，新聞以 RSS 來源更新，法人籌碼以 TWSE 最新可得交易日或 fallback 推估為準。v2.1.0 新增 Phase 5 MVP：資料可信度、防呆、輕量回測與持股總教練：頁面預設讀取已產生的 dashboard_data.json，只有按下重新抓取才會重新拉資料；v2.2.4 使用同日價格快取、並行抓取、價格位置邏輯修正、台股 Stock Master 與個人資料永久保存，避免重新抓取長時間卡住與進場語句不合邏輯；仍屬決策輔助，不是保證報酬的投資指令。若資料源失敗會啟用 fallback，信心指數會下修。",
    }
    return PMBrief(headline, strategy, allocation, recommended_stocks, top_actions, avoid_actions, risk_controls, quality)




def _profit_target_price(base: float, pct: float) -> float:
    return _round_price(base * (1 + pct / 100))


def _is_actionable_setup(card: DecisionCard) -> bool:
    close = float(card.latest_close)
    if close <= 0:
        return False
    in_pullback_zone = card.pullback_low <= close <= card.pullback_high
    near_breakout = 0 <= (card.breakout_price - close) / close <= 0.035
    healthy_breakout_hold = card.breakout_price <= close <= card.breakout_price * 1.06
    return in_pullback_zone or near_breakout or healthy_breakout_hold


def _teacher_grade(card: DecisionCard, guardrail: dict[str, Any] | None = None) -> str:
    # Teacher Buy List focuses on executable swing setups. A means the stock is
    # actionable today, not merely high-score. Phase 5 guardrails prevent the
    # product from issuing A-grade recommendations when data quality or price
    # location is insufficient.
    guardrail = guardrail or {}
    if guardrail.get("status") == "禁止買進":
        return "D" if card.radar_score < 66 else "C"
    if card.decision in {"波段買進", "波段觀察"} and card.radar_score >= 78 and card.confidence >= 74 and guardrail.get("can_buy_today", False):
        return "A"
    if card.decision in {"波段買進", "波段觀察"} and card.radar_score >= 68 and card.confidence >= 62:
        return "B"
    if card.radar_score >= 58 and card.decision != "減碼/避開":
        return "C"
    return "D"


def _teacher_action_type(card: DecisionCard) -> str:
    if card.decision == "減碼/避開":
        return "避開 / 反彈減碼"
    if card.decision == "等待":
        return "等待轉強"
    if card.latest_close >= card.breakout_price:
        return "突破後續抱觀察"
    if card.latest_close >= card.pullback_low and card.latest_close <= card.pullback_high:
        return "拉回買進"
    if card.latest_close < card.pullback_low:
        return "轉強買"
    return "突破買 / 拉回買"


def _primary_reasons(card: DecisionCard) -> list[str]:
    reasons: list[str] = []
    positive = [item for item in card.evidence if item.direction == "positive"]
    neutral = [item for item in card.evidence if item.direction == "neutral"]
    source = positive[:4] + neutral[:2]
    for evidence in source[:5]:
        reasons.append(f"{evidence.label}：{evidence.explanation}")
    if not reasons:
        reasons.append("目前證據不足，不列入主攻名單。")
    return reasons


def _teacher_item(card: DecisionCard, rank: int, guardrail: dict[str, Any] | None = None, backtest: dict[str, Any] | None = None) -> dict[str, Any]:
    guardrail = guardrail or {}
    backtest = backtest or {}
    grade = _teacher_grade(card, guardrail)
    action_type = _teacher_action_type(card)
    first_profit = _profit_target_price(max(card.latest_close, card.breakout_price), 4.2)
    second_profit = _profit_target_price(max(card.latest_close, card.breakout_price), 7.8)
    if grade == "A":
        recommendation = "具備今日可操作條件，可依價格區間分批執行，不追高。"
    elif grade == "B":
        recommendation = "接近可操作，等待突破價或拉回區間確認後再出手。"
    elif grade == "C":
        recommendation = "暫列觀察，不急著買，等待技術或量能更明確。"
    else:
        recommendation = "不列入今日買進名單；若已有部位，反彈優先調節。"

    return {
        "rank": rank,
        "symbol": card.symbol,
        "name": card.name,
        "display_name": card.display_name,
        "grade": grade,
        "action_type": action_type,
        "decision": card.decision,
        "radar_score": card.radar_score,
        "confidence": card.confidence,
        "latest_close": card.latest_close,
        "change_pct": card.change_pct,
        "recommendation": recommendation,
        "suggested_entry_zone": f"{card.pullback_low:.2f}～{card.pullback_high:.2f}",
        "breakout_trigger": card.breakout_price,
        "invalidation_price": card.stop_loss_price,
        "risk_reduce_price": card.reduce_price,
        "first_profit_take": first_profit,
        "second_profit_take": second_profit,
        "volume_condition": card.volume_ratio_note,
        "manager_note": card.swing_view,
        "entry_condition": card.entry_condition,
        "hold_condition": card.hold_condition,
        "reduce_condition": card.reduce_condition,
        "invalidation_condition": card.invalidation_condition,
        "do_not_chase_reason": f"若開盤直接跳空超過突破價 {card.breakout_price:.2f} 且量能無法延續，等待回測 {card.pullback_low:.2f}～{card.pullback_high:.2f}，不追高。",
        "reasons": _primary_reasons(card),
        "guardrail_status": guardrail.get("status", "未檢查"),
        "guardrail_reasons": guardrail.get("reasons", []),
        "guardrail_warnings": guardrail.get("warnings", []),
        "guardrail_blocks": guardrail.get("hard_blocks", []),
        "can_buy_today": bool(guardrail.get("can_buy_today", False)),
        "backtest_sample_count": backtest.get("sample_count", 0),
        "backtest_win_rate": backtest.get("win_rate"),
        "backtest_avg_return": backtest.get("avg_return"),
        "backtest_avg_max_drawdown": backtest.get("avg_max_drawdown"),
        "backtest_note": backtest.get("confidence_note", "尚未建立歷史驗證。"),
    }


def build_teacher_buy_list(cards: list[DecisionCard], portfolio_analysis: list[dict[str, Any]], data_trust: dict[str, Any] | None = None, backtest_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    data_trust = data_trust or {}
    guardrails = data_trust.get("guardrails_by_symbol", {})
    backtests = (backtest_summary or {}).get("per_symbol", {})
    teacher_items = [_teacher_item(card, idx, guardrails.get(card.symbol, {}), backtests.get(card.symbol, {})) for idx, card in enumerate(cards, 1)]
    ready = [item for item in teacher_items if item["grade"] == "A"][:6]
    wait_breakout = [item for item in teacher_items if item["grade"] == "B" and "突破" in item["action_type"]][:8]
    pullback_watch = [item for item in teacher_items if item["grade"] in {"A", "B"} and "拉回" in item["action_type"]][:8]
    observe = [item for item in teacher_items if item["grade"] == "C"][:8]
    avoid = [item for item in teacher_items if item["grade"] == "D"][:8]

    portfolio_actions: list[dict[str, Any]] = []
    for row in portfolio_analysis:
        action = row.get("action", "")
        portfolio_actions.append(
            {
                "symbol": row.get("symbol"),
                "display_name": row.get("display_name"),
                "decision": row.get("decision"),
                "radar_score": row.get("radar_score"),
                "latest_close": row.get("latest_close"),
                "avg_cost": row.get("avg_cost"),
                "pnl_pct": row.get("pnl_pct"),
                "action": action,
            }
        )

    if ready:
        headline = f"今日可買進名單 {len(ready)} 檔，以 {ready[0]['display_name']} 作為第一優先。"
        summary = "今日有可操作標的，但仍以波段價格紀律執行：拉回買、不追高、跌破失效價立即降風險。"
    elif wait_breakout or pullback_watch:
        headline = "今日沒有高信念直接買進標的，等待突破或拉回確認。"
        summary = "市場仍有機會，但價格尚未到老師會出手的位置，先列觀察名單。"
    else:
        headline = "今日不強迫交易，先保護資金。"
        summary = "缺乏可操作條件，等待技術訊號與市場主線更明確。"

    return {
        "headline": headline,
        "summary": summary,
        "ready_to_buy": ready,
        "wait_breakout": wait_breakout,
        "pullback_watch": pullback_watch,
        "observe_only": observe,
        "avoid_or_reduce": avoid,
        "portfolio_actions": portfolio_actions,
        "grading_rule": {
            "A": "可以行動：具備波段可操作條件，但必須照價格區間執行。",
            "B": "接近可買：等待突破價或拉回區間確認。",
            "C": "只觀察：訊號不足，不主動買進。",
            "D": "避免：不碰或既有部位反彈調節。",
        },
    }



def build_ai_teacher_brief(cards: list[DecisionCard], teacher_buy_list: dict[str, Any], data_trust: dict[str, Any], backtest_summary: dict[str, Any], portfolio_coach: dict[str, Any], macd_candidates: list[Any]) -> dict[str, Any]:
    """Build an AI stock-teacher style synthesis.

    This is deterministic, explainable analysis built from the same evidence as
    the dashboard. It does not pretend to be a black-box prediction; it converts
    Radar, guardrails, backtest and portfolio context into a concise teacher
    plan.
    """
    ready = teacher_buy_list.get("ready_to_buy", [])
    b_items = teacher_buy_list.get("wait_breakout", []) + teacher_buy_list.get("pullback_watch", [])
    blocked = data_trust.get("guardrail_blocked_count", 0)
    passed = data_trust.get("guardrail_passed_count", 0)
    stale = data_trust.get("price_stale_count", 0)
    fallback = data_trust.get("price_fallback_count", 0)
    top = cards[0] if cards else None

    if ready:
        posture = "今日可以做，但只做通過資料與價格紀律的 A 級標的。"
    elif b_items:
        posture = "今日不急著買，重點是等突破或拉回到老師願意出手的位置。"
    else:
        posture = "今日先保護資金，不強迫交易。"

    if fallback or stale:
        data_warning = f"資料面仍需保守：Fallback {fallback} 檔、日期落後 {stale} 檔；這些標的不應列為主攻。"
    else:
        data_warning = "資料面可用：主要推薦均使用最新可得 Yahoo 日線，並通過資料防呆。"

    focus_names = [item["display_name"] for item in ready[:3]] or [item["display_name"] for item in b_items[:3]]
    focus_text = "、".join(focus_names) if focus_names else "今日無高信念主攻名單"

    scenario_plan = {
        "開高": "開盤若直接跳空高於突破價，不追高；等 5～15 分鐘量能延續，或回測突破價不破再小部位。",
        "平盤震盪": "優先看 A/B 名單是否回到建議買進區間；沒有到價就不出手。",
        "開低": "若跌到失效價附近且量能放大，先不要接刀；等止跌與 MACD 柱狀體改善。",
    }

    if top:
        teacher_summary = f"第一優先觀察 {top.display_name}，Radar {top.radar_score}、信心 {top.confidence}%，但仍以 {top.pullback_low:.2f}～{top.pullback_high:.2f} 拉回區或 {top.breakout_price:.2f} 突破確認作為交易紀律。"
    else:
        teacher_summary = "今日沒有足夠資料產生第一優先標的。"

    return {
        "headline": "AI 股市老師總評",
        "posture": posture,
        "focus_list": focus_names,
        "focus_text": focus_text,
        "teacher_summary": teacher_summary,
        "data_warning": data_warning,
        "scenario_plan": scenario_plan,
        "portfolio_commentary": portfolio_coach.get("headline", "尚未建立持股，無法提供組合層級建議。"),
        "macd_commentary": f"MACD 名單已排除 fallback 與日期落後資料；目前有效候選 {len(macd_candidates)} 檔。",
        "quality_commentary": f"A 級通過 {passed} 檔，禁止買進 {blocked} 檔。推薦品質優先於數量。",
        "teacher_rules": [
            "只買到價標的，不買情緒。",
            "資料不足的股票不列為 A 級買進。",
            "突破買要有量，拉回買要有守。",
            "跌破失效價先處理風險，不用攤平替代停損。",
        ],
    }

def _load_technical_profiles_parallel(stocks: list[StockMeta], price_days: int) -> dict[str, TechnicalProfile]:
    """Load technical profiles concurrently.

    v2.2.4 keeps the Streamlit refresh hotfix and adds persistent user data by avoiding sequential 100-stock
    downloads. Each symbol uses cache-first Yahoo loading, and network failures
    are converted to fallback/cached profiles without blocking the entire page.
    """
    profiles: dict[str, TechnicalProfile] = {}
    max_workers = min(16, max(4, len(stocks)))

    def _load_one(stock: StockMeta) -> tuple[str, TechnicalProfile]:
        bars, price_source = load_price_bars(stock, days=price_days)
        return stock.symbol, evaluate_technical(stock, bars, price_source)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_load_one, stock): stock for stock in stocks}
        for future in as_completed(futures):
            stock = futures[future]
            try:
                symbol, profile = future.result()
            except Exception:
                bars, price_source = load_price_bars(stock, days=price_days)
                symbol, profile = stock.symbol, evaluate_technical(stock, bars, price_source)
            profiles[symbol] = profile

    return profiles


def run_decision_pipeline(news_limit: int = 12, price_days: int = 160) -> dict[str, Any]:
    news_items, news_source = fetch_rss_news(limit=news_limit)
    stocks = load_stock_universe()
    investor_profile = load_investor_profile()
    technical_profiles = _load_technical_profiles_parallel(stocks, price_days)

    institutional_flows = load_institutional_flows(stocks, technical_profiles)
    cards = build_decision_cards(news_items, stocks, technical_profiles, investor_profile, institutional_flows)
    backtest_summary = build_backtest_summary(technical_profiles, horizon=20)
    data_trust = build_data_trust_summary(technical_profiles, cards, backtest_summary)
    macd_candidates = rank_macd_turn_candidates(stocks, technical_profiles, limit=10)
    market_view = _market_view(cards, news_items)
    confidence = _ai_confidence(cards, news_items, technical_profiles)
    user_watchlist = load_user_watchlist()
    portfolio = load_portfolio()
    portfolio_analysis = build_portfolio_analysis(portfolio, cards, technical_profiles)
    portfolio_coach = build_portfolio_coach(portfolio_analysis)
    pm_brief = _build_pm_brief(cards, news_items, technical_profiles, institutional_flows, news_source, market_view, confidence, len(user_watchlist), len(portfolio))
    teacher_buy_list = build_teacher_buy_list(cards, portfolio_analysis, data_trust, backtest_summary)
    ai_teacher_brief = build_ai_teacher_brief(cards, teacher_buy_list, data_trust, backtest_summary, portfolio_coach, macd_candidates)

    payload = {
        "version": VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "market_view": market_view,
        "ai_confidence": confidence,
        "news_source": news_source,
        "investor_profile": investor_profile,
        "user_watchlist": user_watchlist,
        "portfolio": portfolio,
        "portfolio_analysis": portfolio_analysis,
        "portfolio_coach": portfolio_coach,
        "pm_brief": pm_brief.as_dict(),
        "teacher_buy_list": teacher_buy_list,
        "ai_teacher_brief": ai_teacher_brief,
        "data_trust": data_trust,
        "backtest_summary": backtest_summary,
        "phase_target": "Phase 5+：資料修正、MACD 新鮮度、AI 股市老師總評、持股總教練、快速刷新與價格位置語句修正",
        "decision_cards": [card.as_dict() for card in cards],
        "macd_candidates": [candidate.as_dict() for candidate in macd_candidates],
        "news_items": [item.as_dict() for item in news_items],
        "technical_profiles": {symbol: profile.as_dict() for symbol, profile in technical_profiles.items()},
        "institutional_flows": {symbol: flow.as_dict() for symbol, flow in institutional_flows.items()},
        "stock_index": {stock.symbol: {"symbol": stock.symbol, "name": stock.name, "display_name": stock.display_name, "sector": stock.sector} for stock in stocks},
    }
    return payload


def save_dashboard_payload(payload: dict[str, Any], path: str | Path = "output/dashboard_data.json") -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
