"""Domain models for AI Stock Radar."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    signal: str
    impact: str
    summary: str
    industries: list[str]
    affected_stocks: list[str]


@dataclass(frozen=True)
class RadarCard:
    rank: int
    stock: str
    score: int
    decision: str
    confidence: int
    evidence: list[str]
    risk: str
    action: str


@dataclass(frozen=True)
class DailyDecision:
    market_view: str
    confidence: int
    key_message: str
    top_cards: list[RadarCard]
    risks: list[str]
    actions: list[str]
    news_items: list[NewsItem]
