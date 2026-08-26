from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class PriceBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    amount: float
    volume: int


@dataclass(frozen=True)
class StockSeries:
    symbol: str
    name: str
    bars: list[PriceBar]
    industry: str = ""


@dataclass(frozen=True)
class StockMetadata:
    symbol: str
    name: str = ""
    industry: str = ""
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreResult:
    rank: int
    symbol: str
    name: str
    industry: str
    trade_date: str
    close: float
    score: float
    bucket: str
    components: dict[str, float]
    metrics: dict[str, float | str]
    reasons: list[str]
    flags: list[str]
