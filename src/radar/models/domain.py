"""Domain models for AI Stock Radar."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Impact = Literal["positive", "negative", "neutral"]
Decision = Literal["波段買進", "波段觀察", "等待", "減碼/避開"]


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    title_zh: str
    summary_zh: str
    signal: str
    impact: Impact
    industries: list[str]
    affected_stocks: list[str]


@dataclass(frozen=True)
class StockProfile:
    symbol: str
    name: str
    sector: str
    theme: list[str]
    macd_hist_prev: float
    macd_hist: float
    dif: float
    dea: float
    rsi: float
    trend: int
    risk: int
    ma_state: str
    pm_view: str

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"


@dataclass
class Evidence:
    label: str
    direction: Impact
    weight: int
    explanation: str


@dataclass
class ScoreBreakdown:
    base: int
    news_signal: int
    technical: int
    profile_bonus: int
    risk_penalty: int
    final_score: int

    def as_dict(self) -> dict[str, int]:
        return {
            "base": self.base,
            "news_signal": self.news_signal,
            "technical": self.technical,
            "profile_bonus": self.profile_bonus,
            "risk_penalty": self.risk_penalty,
            "final_score": self.final_score,
        }


@dataclass
class DecisionCard:
    symbol: str
    name: str
    sector: str
    radar_score: int
    decision: Decision
    confidence: int
    conviction: str
    swing_view: str
    entry_condition: str
    hold_condition: str
    reduce_condition: str
    invalidation_condition: str
    risk_note: str
    position_guidance: str
    score_breakdown: ScoreBreakdown
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"


@dataclass(frozen=True)
class MacdCandidate:
    symbol: str
    name: str
    sector: str
    score: int
    hist_prev: float
    hist_current: float
    rsi: float
    trend: int
    reason: str


@dataclass(frozen=True)
class PMBrief:
    headline: str
    strategy: str
    capital_allocation: str
    top_actions: list[str]
    avoid_actions: list[str]
    risk_controls: list[str]
    data_quality: dict[str, Any]
