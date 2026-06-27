"""Domain models for AI Stock Radar."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    summary: str
    signal: str
    sentiment: str
    tickers: list[str]
    industries: list[str]


@dataclass(frozen=True)
class Evidence:
    label: str
    score: int
    tone: str
    reason: str
    source: str = "system"


@dataclass
class DecisionCard:
    ticker: str
    name: str
    radar_score: int
    decision: str
    confidence: int
    action: str
    reason: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(frozen=True)
class DailyDecision:
    version: str
    market_view: str
    ai_confidence: int
    news_source: str
    news_count: int
    cards: list[DecisionCard]
    risk_alerts: list[str]
    today_action: str
