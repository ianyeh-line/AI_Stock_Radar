"""Technical analysis utilities for swing trading."""

from __future__ import annotations

from radar.models.domain import MacdCandidate, StockProfile


def macd_turn_score(stock: StockProfile) -> int:
    """Score MACD candidates that are improving from negative histogram toward positive."""
    improvement = stock.macd_hist - stock.macd_hist_prev
    near_zero_bonus = max(0.0, 1.0 - abs(stock.macd_hist) * 3.5)
    improving_bonus = max(0.0, improvement * 3.0)
    trend_bonus = stock.trend / 100
    rsi_penalty = 0.0
    if stock.rsi > 68:
        rsi_penalty = 0.18
    elif stock.rsi < 45:
        rsi_penalty = 0.10
    raw = 100 * (0.42 * near_zero_bonus + 0.35 * improving_bonus + 0.23 * trend_bonus - rsi_penalty)
    return max(1, min(99, round(raw)))


def rank_macd_turn_candidates(stocks: list[StockProfile], limit: int = 10) -> list[MacdCandidate]:
    candidates: list[MacdCandidate] = []
    for stock in stocks:
        improving = stock.macd_hist > stock.macd_hist_prev
        near_turn = stock.macd_hist <= 0.05
        if not improving or not near_turn:
            continue
        score = macd_turn_score(stock)
        reason = "MACD 柱狀體收斂且趨勢分數改善，具備翻正觀察價值。"
        if stock.macd_hist > 0:
            reason = "MACD 已初步翻正，接下來需確認量能與均線支撐。"
        candidates.append(
            MacdCandidate(
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                score=score,
                hist_prev=stock.macd_hist_prev,
                hist_current=stock.macd_hist,
                rsi=stock.rsi,
                trend=stock.trend,
                reason=reason,
            )
        )
    return sorted(candidates, key=lambda item: item.score, reverse=True)[:limit]


def technical_summary(stock: StockProfile) -> str:
    macd_state = "MACD 已翻正" if stock.macd_hist > 0 else "MACD 接近翻正" if stock.macd_hist > -0.12 else "MACD 仍待收斂"
    rsi_state = "RSI 偏熱" if stock.rsi >= 68 else "RSI 偏弱" if stock.rsi <= 45 else "RSI 健康"
    return f"{stock.ma_state}；{macd_state}；{rsi_state}。"
