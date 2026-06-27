"""Lightweight historical validation for AI Stock Radar.

This is not a full broker-grade backtesting engine. It is a conservative
signal sanity check that answers one question: when similar technical setups
appeared in the recent historical bars, did the stock tend to work over the
next 20 trading days?
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from radar.models.domain import TechnicalProfile


def _forward_max_drawdown(prices: list[float]) -> float:
    if not prices:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        peak = max(peak, price)
        if peak:
            max_dd = min(max_dd, (price - peak) / peak * 100)
    return round(max_dd, 2)


def _backtest_profile(profile: TechnicalProfile, horizon: int = 20) -> dict[str, Any]:
    history = profile.history or []
    if len(history) < 90:
        return {
            "sample_count": 0,
            "win_rate": None,
            "avg_return": None,
            "avg_max_drawdown": None,
            "confidence_note": "歷史價格樣本不足，暫不納入統計驗證。",
        }

    signals: list[dict[str, float]] = []
    # Avoid the latest horizon because it does not yet have enough future data.
    upper = max(0, len(history) - horizon)
    for idx in range(60, upper):
        row = history[idx]
        close = float(row.get("close") or 0)
        ma20 = row.get("ma20")
        ma60 = row.get("ma60")
        macd_hist = row.get("macd_hist")
        prev_macd = history[idx - 1].get("macd_hist") if idx > 0 else None
        rsi = row.get("rsi")
        volume = float(row.get("volume") or 0)
        volume_ma20 = row.get("volume_ma20")
        if not close or ma20 is None or ma60 is None or macd_hist is None or prev_macd is None or rsi is None:
            continue
        volume_ratio = 1.0 if not volume_ma20 else volume / float(volume_ma20)
        trend_ok = close >= float(ma20) and float(ma20) >= float(ma60) * 0.985
        momentum_ok = float(macd_hist) >= float(prev_macd)
        rsi_ok = 42 <= float(rsi) <= 72
        volume_ok = volume_ratio >= 0.75
        if trend_ok and momentum_ok and rsi_ok and volume_ok:
            future = history[idx + horizon]
            future_close = float(future.get("close") or close)
            ret = 0.0 if close == 0 else (future_close - close) / close * 100
            forward_prices = [float(item.get("close") or close) for item in history[idx : idx + horizon + 1]]
            signals.append({"return": ret, "max_drawdown": _forward_max_drawdown(forward_prices)})

    if not signals:
        return {
            "sample_count": 0,
            "win_rate": None,
            "avg_return": None,
            "avg_max_drawdown": None,
            "confidence_note": "近一年沒有足夠相似波段訊號，推薦需以當前技術與風控為主。",
        }

    returns = [item["return"] for item in signals]
    drawdowns = [item["max_drawdown"] for item in signals]
    wins = sum(1 for value in returns if value > 0)
    return {
        "sample_count": len(signals),
        "win_rate": round(wins / len(signals) * 100, 1),
        "avg_return": round(mean(returns), 2),
        "avg_max_drawdown": round(mean(drawdowns), 2),
        "confidence_note": "以近一年日線資料檢查類似波段訊號的 20 日後表現。樣本數越高越有參考價值。",
    }


def build_backtest_summary(profiles: dict[str, TechnicalProfile], horizon: int = 20) -> dict[str, Any]:
    per_symbol = {symbol: _backtest_profile(profile, horizon=horizon) for symbol, profile in profiles.items()}
    usable = [item for item in per_symbol.values() if item.get("sample_count", 0) > 0]
    if usable:
        avg_win_rate = round(mean(float(item["win_rate"]) for item in usable if item.get("win_rate") is not None), 1)
        avg_return = round(mean(float(item["avg_return"]) for item in usable if item.get("avg_return") is not None), 2)
        avg_drawdown = round(mean(float(item["avg_max_drawdown"]) for item in usable if item.get("avg_max_drawdown") is not None), 2)
    else:
        avg_win_rate = None
        avg_return = None
        avg_drawdown = None

    return {
        "method": "近一年日線、技術相似訊號、20 個交易日後驗證",
        "horizon_days": horizon,
        "validated_symbols": len(usable),
        "total_symbols": len(per_symbol),
        "avg_win_rate": avg_win_rate,
        "avg_return": avg_return,
        "avg_max_drawdown": avg_drawdown,
        "per_symbol": per_symbol,
        "limitations": "此為輕量驗證，不含交易成本、滑價、除權息、停損執行與大盤 regime 分層；用於提升推薦可信度，不是保證績效。",
    }
