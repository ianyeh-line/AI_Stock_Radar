"""Domain models for AI Stock Radar."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    published: str = ""
    source_url: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StockMeta:
    symbol: str
    name: str
    sector: str
    theme: list[str]
    yahoo_symbol: str
    pm_view: str
    base_priority: int = 5
    is_custom: bool = False

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"


@dataclass(frozen=True)
class PriceBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TechnicalProfile:
    symbol: str
    name: str
    yahoo_symbol: str
    price_source: str
    bars_count: int
    latest_close: float
    change_pct: float
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    ma120: float
    volume_ma5: float
    volume_ma20: float
    bb_upper: float
    bb_lower: float
    dif: float
    dea: float
    macd_hist: float
    macd_hist_prev: float
    rsi: float
    volume_ratio: float
    trend_score: int
    risk_score: int
    ma_state: str
    technical_summary: str
    latest_date: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    label: str
    direction: Impact
    weight: int
    explanation: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreBreakdown:
    base: int
    news_signal: int
    technical: int
    institutional_flow: int
    profile_bonus: int
    price_quality: int
    risk_penalty: int
    final_score: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class DecisionCard:
    symbol: str
    name: str
    sector: str
    radar_score: int
    decision: Decision
    confidence: int
    conviction: str
    latest_close: float
    change_pct: float
    price_source: str
    swing_view: str
    entry_condition: str
    hold_condition: str
    reduce_condition: str
    invalidation_condition: str
    risk_note: str
    position_guidance: str
    breakout_price: float
    pullback_low: float
    pullback_high: float
    reduce_price: float
    stop_loss_price: float
    volume_ratio_note: str
    institutional_summary: str
    institutional_source: str
    score_breakdown: ScoreBreakdown
    institutional_flow: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["display_name"] = self.display_name
        return data


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
    latest_close: float
    latest_date: str
    price_source: str
    macd_status: str
    reason: str

    @property
    def display_name(self) -> str:
        return f"{self.symbol} {self.name}"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["display_name"] = self.display_name
        return data


@dataclass(frozen=True)
class PMBrief:
    headline: str
    strategy: str
    capital_allocation: str
    recommended_stocks: list[dict[str, Any]]
    top_actions: list[str]
    avoid_actions: list[str]
    risk_controls: list[str]
    data_quality: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
