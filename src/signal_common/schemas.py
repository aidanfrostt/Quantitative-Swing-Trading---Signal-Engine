"""Pydantic models shared by the API, Kafka payloads, and jobs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Horizon(str, Enum):
    d1 = "1d"
    w1 = "1w"


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionIntent(str, Enum):
    LONG = "long"
    REDUCE_LONG = "reduce_long"
    SHORT = "short"
    FLAT = "flat"


class ConfidenceTier(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvidenceItem(BaseModel):
    label: str
    value: str | float | int | None = None
    as_of: str | None = None


class MoveAttribution(BaseModel):
    """Explanatory 5d attribution vs SPY / sector ETF; not predictive."""

    spy_return_5d: float | None = None
    sector_etf: str | None = None
    sector_etf_return_5d: float | None = None
    beta_spy: float | None = None
    market_explained_5d: float | None = None
    sector_component_5d: float | None = None
    residual_5d: float | None = None
    peer_percentile_sector: float | None = None
    data_quality: str | None = None
    narrative: str = ""


class MarketContext(BaseModel):
    """Broad tape snapshot for the response payload (optional)."""

    spy_return_5d: float | None = None
    qqq_return_5d: float | None = None
    vix_close: float | None = None
    regime_buy_dampening: float | None = None


class SectorSentimentRow(BaseModel):
    """Aggregated news sentiment vs benchmark ETF performance by sector_key (explanatory)."""

    as_of_date: str
    sector_key: str
    benchmark_etf: str | None = None
    article_count: int = 0
    weighted_sentiment_avg: float | None = None
    sentiment_std: float | None = None
    etf_return_5d: float | None = None
    etf_return_20d: float | None = None
    sentiment_z_cross_sector: float | None = None
    performance_sentiment_spread: float | None = None
    divergence_flag: bool | None = None


class SignalRecord(BaseModel):
    ticker: str
    action: SignalAction
    horizon: Horizon
    conviction: float
    master_conviction: float = Field(
        description="Combined score after blending tech, sentiment, fundamentals, regime",
    )
    technical_score: float
    sentiment_score: float
    fundamental_score: float | None = None
    regime_adjustment: float
    position_intent: PositionIntent
    reason_codes: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    thesis: str = ""
    confidence_tier: ConfidenceTier = ConfidenceTier.medium
    evidence: list[EvidenceItem] = Field(default_factory=list)
    move_attribution: MoveAttribution | None = None


class SignalsPayload(BaseModel):
    generated_at: datetime
    universe_version: str
    market_session: dict[str, Any] = Field(
        default_factory=dict,
        description="NYSE calendar context; not a guarantee of liquidity or borrow for shorts.",
    )
    long_candidates: list[SignalRecord] = Field(default_factory=list)
    short_candidates: list[SignalRecord] = Field(default_factory=list)
    watchlist: list[SignalRecord] = Field(
        default_factory=list,
        description="HOLD names with elevated |conviction| for monitoring.",
    )
    signals: list[SignalRecord] = Field(
        default_factory=list,
        description="Flat list: top names by |master_conviction| for backward compatibility.",
    )
    symbols_evaluated: int = Field(
        default=0,
        ge=0,
        description="Count of symbols with latest technical_features rows used to score this response.",
    )
    disclaimer: str = Field(
        default="Signals are model outputs, not investment advice. Past performance does not guarantee future results.",
    )
    market_context: MarketContext | None = Field(
        default=None,
        description="Latest SPY/QQQ/VIX-style context from OHLCV + regime (when available).",
    )
    sector_context: list[SectorSentimentRow] = Field(
        default_factory=list,
        description="Latest sector-level news sentiment vs ETF returns (when sector_sentiment_job has run).",
    )


class SectorSentimentPayload(BaseModel):
    """Response for GET /v1/sector-sentiment."""

    as_of_date: str | None = None
    rows: list[SectorSentimentRow] = Field(default_factory=list)
    disclaimer: str = Field(
        default="Sector aggregates are descriptive; correlation is not causation. News coverage is incomplete.",
    )


class NewsArticleIn(BaseModel):
    article_id: str
    headline: str
    body: str = ""
    published_at: datetime
    author: str = ""
    source: str = ""
    tickers: list[str] = Field(default_factory=list)
    url: str = ""


class OhlcvBar(BaseModel):
    symbol: str
    interval: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float | None = None
