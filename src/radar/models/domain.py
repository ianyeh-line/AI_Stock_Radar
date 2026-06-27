"""Domain models for AI Stock Radar."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    link: str = ""
    summary: str = ""
    published: str = ""


@dataclass(frozen=True)
class StockRadar:
    symbol: str
    name: str
    score: int
    decision: str
    confidence: int
    evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DailyDecision:
    market_view: str
    confidence: int
    top_stocks: list[StockRadar]
    market_signals: list[str]
    risks: list[str]
    action: str
    news_items: list[NewsItem]
