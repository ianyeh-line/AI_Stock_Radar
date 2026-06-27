"""Data trust checks and recommendation guardrails."""

from __future__ import annotations

from typing import Any

from radar.models.domain import DecisionCard, TechnicalProfile


def assess_price_quality(profile: TechnicalProfile, latest_reference_date: str) -> dict[str, Any]:
    source = profile.price_source or "N/A"
    is_live = source.startswith("Yahoo Finance")
    is_latest = bool(profile.latest_date and profile.latest_date == latest_reference_date)
    enough_bars = profile.bars_count >= 90
    if is_live and is_latest and enough_bars:
        status = "正常"
        score = 100
        action = "可作為推薦依據"
    elif is_live and enough_bars:
        status = "日期落後"
        score = 68
        action = "可觀察，但不列為 A 級直接買進"
    elif enough_bars:
        status = "Fallback"
        score = 45
        action = "只能觀察，不給買進"
    else:
        status = "樣本不足"
        score = 30
        action = "禁止推薦"
    return {
        "status": status,
        "score": score,
        "action": action,
        "latest_date": profile.latest_date,
        "reference_date": latest_reference_date,
        "source": source,
        "bars_count": profile.bars_count,
    }


def assess_card_guardrails(card: DecisionCard, profile: TechnicalProfile, backtest: dict[str, Any] | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    hard_blocks: list[str] = []
    warnings: list[str] = []

    if not card.price_source.startswith("Yahoo Finance"):
        hard_blocks.append("價格來源為 fallback，不能列為今日可買進。")
    if profile.bars_count < 90:
        hard_blocks.append("日線資料不足 90 根，技術判斷樣本不足。")
    if "偏空" in card.institutional_summary:
        hard_blocks.append("三大法人籌碼偏空，不給 A 級買進。")
    if profile.rsi >= 75:
        hard_blocks.append(f"RSI {profile.rsi:.1f} 過熱，避免追價。")
    if profile.volume_ratio < 0.65:
        hard_blocks.append(f"量能比 {profile.volume_ratio:.2f} 偏低，突破可信度不足。")

    close = float(card.latest_close)
    actionable = False
    if close > 0:
        in_pullback = card.pullback_low <= close <= card.pullback_high
        near_breakout = 0 <= (card.breakout_price - close) / close <= 0.035
        breakout_hold = card.breakout_price <= close <= card.breakout_price * 1.06
        actionable = in_pullback or near_breakout or breakout_hold
        if not actionable:
            warnings.append("價格尚未接近拉回區或突破確認價，較適合列為 B 級等待。")
        if close > card.breakout_price * 1.08:
            hard_blocks.append("距離突破價過遠，今日不追高。")

    if card.radar_score < 78:
        warnings.append("Radar 未達 A 級門檻。")
    if card.confidence < 74:
        warnings.append("AI 信心不足，降級為觀察。")

    if backtest:
        sample_count = int(backtest.get("sample_count") or 0)
        win_rate = backtest.get("win_rate")
        avg_return = backtest.get("avg_return")
        if sample_count >= 3 and win_rate is not None and float(win_rate) < 45:
            warnings.append(f"相似訊號勝率 {win_rate}% 偏低，不宜重倉。")
        if sample_count >= 3 and avg_return is not None and float(avg_return) < 0:
            warnings.append(f"相似訊號平均報酬 {avg_return}% 偏弱，降低信心。")
        if sample_count == 0:
            warnings.append("缺少相似歷史訊號，不列為高信念。")

    if not hard_blocks and actionable and card.radar_score >= 78 and card.confidence >= 74:
        status = "通過"
        reasons.append("符合資料、價格位置、風險與信心的 A 級候選條件。")
    elif hard_blocks:
        status = "禁止買進"
    else:
        status = "降級觀察"

    return {
        "status": status,
        "can_buy_today": status == "通過",
        "hard_blocks": hard_blocks,
        "warnings": warnings,
        "reasons": reasons,
        "actionable_price": actionable,
    }


def build_data_trust_summary(profiles: dict[str, TechnicalProfile], cards: list[DecisionCard], backtest_summary: dict[str, Any]) -> dict[str, Any]:
    latest_dates = sorted({profile.latest_date for profile in profiles.values() if profile.latest_date})
    reference_date = latest_dates[-1] if latest_dates else "N/A"
    price_quality = {symbol: assess_price_quality(profile, reference_date) for symbol, profile in profiles.items()}
    guardrails = {
        card.symbol: assess_card_guardrails(card, profiles[card.symbol], backtest_summary.get("per_symbol", {}).get(card.symbol, {}))
        for card in cards
        if card.symbol in profiles
    }
    normal = sum(1 for item in price_quality.values() if item["status"] == "正常")
    fallback = sum(1 for item in price_quality.values() if item["status"] == "Fallback")
    stale = sum(1 for item in price_quality.values() if item["status"] == "日期落後")
    blocked = sum(1 for item in guardrails.values() if item["status"] == "禁止買進")
    downgraded = sum(1 for item in guardrails.values() if item["status"] == "降級觀察")
    passed = sum(1 for item in guardrails.values() if item["status"] == "通過")
    return {
        "reference_price_date": reference_date,
        "price_normal_count": normal,
        "price_stale_count": stale,
        "price_fallback_count": fallback,
        "guardrail_passed_count": passed,
        "guardrail_downgraded_count": downgraded,
        "guardrail_blocked_count": blocked,
        "price_quality_by_symbol": price_quality,
        "guardrails_by_symbol": guardrails,
        "policy": "A 級推薦必須通過價格資料、技術風險、法人籌碼、價格位置與信心門檻；未通過者自動降級或禁止買進。",
    }
