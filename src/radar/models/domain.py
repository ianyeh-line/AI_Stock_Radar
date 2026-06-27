"""Domain models for AI Stock Radar."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    title_zh: str
    summary: str
    summary_zh: str
    signal: str
    signal_zh: str
    sentiment: str
    tickers: list[str]
    industries: list[str]
    url: str = ""
    sentiment_zh: str = ""


@dataclass(frozen=True)
class Evidence:
    category: str
    signal: str
    signal_zh: str
    tone: str
    score: int
    source: str
    reason: str
    title: str = ""
    title_zh: str = ""


@dataclass(frozen=True)
class TechnicalSnapshot:
    ticker: str
    name: str
    price: float
    ma5: float
    ma20: float
    ma60: float
    rsi14: float
    volume: int
    trend: str
    signal: str
    score: int
    confidence: int
    data_source: str
    chart_note: str
    history: list[dict[str, float | int | str]] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionCard:
    ticker: str
    name: str
    radar_score: int
    news_score: int
    technical_score: int
    risk_score: int
    decision: str
    confidence: int
    reason: str
    action: str
    stance: str
    position_rule: str
    risk_note: str
    technical: TechnicalSnapshot
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class DailyDecision:
    version: str
    news_source: str
    news_count: int
    market_view: str
    ai_confidence: int
    today_action: str
    risk_alerts: list[str]
    cards: list[DecisionCard]
    news_items: list[NewsItem]
    product_note: str = ""
