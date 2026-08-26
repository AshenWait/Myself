from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from statistics import mean

from .models import PriceBar, ScoreResult, StockMetadata, StockSeries
from .tdx import (
    find_day_file,
    is_screening_symbol,
    iter_stock_day_files,
    load_tdx_stock_names,
    read_day_file,
)

WEIGHTS = {
    "trend": 30.0,
    "leader": 20.0,
    "volume": 15.0,
    "new_high": 10.0,
    "market": 10.0,
    "fundamental": 15.0,
}


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return mean(values[-window:])


def pct_change(now: float, then: float | None) -> float:
    if then is None or then == 0:
        return 0.0
    return (now / then - 1.0) * 100.0


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: item[1])
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0][0]: 100.0}
    return {symbol: round(index / (len(ordered) - 1) * 100, 2) for index, (symbol, _) in enumerate(ordered)}


def score_universe(
    tdx_root: Path,
    benchmark_symbol: str = "sh000001",
    metadata: dict[str, StockMetadata] | None = None,
    min_history: int = 220,
    limit_files: int | None = None,
) -> list[ScoreResult]:
    metadata = metadata or {}
    stock_names = load_tdx_stock_names(tdx_root)
    benchmark = read_day_file(find_day_file(tdx_root, benchmark_symbol), benchmark_symbol)
    benchmark_bars = benchmark.bars[-260:]

    series_list: list[StockSeries] = []
    stock_files = (
        (symbol, path)
        for symbol, path in iter_stock_day_files(tdx_root)
        if is_screening_symbol(symbol)
    )
    for index, (symbol, path) in enumerate(stock_files):
        if limit_files is not None and index >= limit_files:
            break
        meta = metadata.get(symbol, StockMetadata(symbol=symbol))
        series = read_day_file(path, symbol=symbol, name=meta.name or stock_names.get(symbol, ""))
        if len(series.bars) >= min_history:
            series_list.append(replace(series, industry=meta.industry))

    momentum_values = {series.symbol: weighted_momentum(series.bars) for series in series_list}
    rs_ranks = percentile_ranks(momentum_values)
    market_score = market_regime_score(benchmark_bars)

    results: list[ScoreResult] = []
    for series in series_list:
        meta = metadata.get(series.symbol, StockMetadata(symbol=series.symbol))
        result = score_series(series, benchmark_bars, rs_ranks.get(series.symbol, 0.0), market_score, meta)
        results.append(result)

    ranked = sorted(results, key=lambda item: item.score, reverse=True)
    return [replace(item, rank=index + 1) for index, item in enumerate(ranked)]


def weighted_momentum(bars: list[PriceBar]) -> float:
    closes = [bar.close for bar in bars]
    now = closes[-1]
    periods = [(63, 0.45), (126, 0.35), (252, 0.20)]
    score = 0.0
    for days, weight in periods:
        then = closes[-days] if len(closes) >= days else closes[0]
        score += pct_change(now, then) * weight
    return score


def score_series(
    series: StockSeries,
    benchmark_bars: list[PriceBar],
    rs_rank: float,
    market_score: float,
    metadata: StockMetadata,
) -> ScoreResult:
    bars = series.bars[-260:]
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    latest = bars[-1]

    trend, trend_reasons = trend_score(closes, highs, lows)
    volume, volume_reasons = volume_score(bars)
    new_high, new_high_reasons = new_high_score(bars)
    fundamental, fundamental_flags = fundamental_score(metadata)

    components = {
        "trend": trend,
        "leader": clamp(rs_rank),
        "volume": volume,
        "new_high": new_high,
        "market": market_score,
        "fundamental": fundamental,
    }
    score = sum(components[key] / 100.0 * weight for key, weight in WEIGHTS.items())
    score = round(score, 2)
    reasons = trend_reasons + volume_reasons + new_high_reasons
    flags = fundamental_flags

    metrics: dict[str, float | str] = {
        "rs_rank": round(rs_rank, 2),
        "return_1m_pct": round(pct_change(closes[-1], closes[-21] if len(closes) >= 21 else closes[0]), 2),
        "return_3m_pct": round(pct_change(closes[-1], closes[-63] if len(closes) >= 63 else closes[0]), 2),
        "distance_to_52w_high_pct": round((closes[-1] / max(highs) - 1.0) * 100.0, 2),
        "benchmark_return_1m_pct": round(
            pct_change(benchmark_bars[-1].close, benchmark_bars[-21].close if len(benchmark_bars) >= 21 else benchmark_bars[0].close),
            2,
        ),
    }

    return ScoreResult(
        rank=0,
        symbol=series.symbol,
        name=series.name or metadata.name,
        industry=series.industry or metadata.industry,
        trade_date=latest.trade_date.isoformat(),
        close=round(latest.close, 3),
        score=score,
        bucket=bucket(score),
        components={key: round(value, 2) for key, value in components.items()},
        metrics=metrics,
        reasons=reasons[:8],
        flags=flags,
    )


def trend_score(closes: list[float], highs: list[float], lows: list[float]) -> tuple[float, list[str]]:
    latest = closes[-1]
    ma50 = moving_average(closes, 50)
    ma150 = moving_average(closes, 150)
    ma200 = moving_average(closes, 200)
    ma200_past = mean(closes[-220:-20]) if len(closes) >= 220 else None
    high_52w = max(highs)
    low_52w = min(lows)

    score = 0.0
    reasons: list[str] = []
    checks = [
        (ma50 is not None and latest > ma50, 15.0, "close_above_ma50"),
        (ma150 is not None and latest > ma150, 10.0, "close_above_ma150"),
        (ma200 is not None and latest > ma200, 10.0, "close_above_ma200"),
        (ma50 is not None and ma150 is not None and ma50 > ma150, 15.0, "ma50_above_ma150"),
        (ma150 is not None and ma200 is not None and ma150 > ma200, 10.0, "ma150_above_ma200"),
        (ma200 is not None and ma200_past is not None and ma200 > ma200_past, 15.0, "ma200_rising"),
        (latest >= low_52w * 1.30, 10.0, "30pct_above_52w_low"),
        (latest >= high_52w * 0.75, 15.0, "within_25pct_of_52w_high"),
    ]
    for passed, points, reason in checks:
        if passed:
            score += points
            reasons.append(reason)
    return clamp(score), reasons


def volume_score(bars: list[PriceBar]) -> tuple[float, list[str]]:
    recent = bars[-50:]
    if len(recent) < 10:
        return 0.0, ["short_volume_history"]

    up_volume = 0
    down_volume = 0
    signed_volume = 0
    for prev, current in zip(recent, recent[1:]):
        if current.close >= prev.close:
            up_volume += current.volume
            signed_volume += current.volume
        else:
            down_volume += current.volume
            signed_volume -= current.volume

    ratio = up_volume / max(down_volume, 1)
    average_volume = mean(bar.volume for bar in recent[:-1])
    latest = recent[-1]
    previous = recent[-2]

    score = 0.0
    reasons: list[str] = []
    if ratio >= 1.5:
        score += 50.0
        reasons.append("up_down_volume_ratio_strong")
    elif ratio >= 1.2:
        score += 35.0
        reasons.append("up_down_volume_ratio_positive")
    if latest.close > previous.close and latest.volume >= average_volume * 1.3:
        score += 25.0
        reasons.append("positive_day_volume_expansion")
    if signed_volume > 0:
        score += 25.0
        reasons.append("positive_obv_proxy")
    return clamp(score), reasons


def new_high_score(bars: list[PriceBar]) -> tuple[float, list[str]]:
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    latest = closes[-1]
    high_52w = max(highs)
    previous_20_high = max(highs[-21:-1]) if len(highs) >= 21 else high_52w

    score = 0.0
    reasons: list[str] = []
    if latest >= high_52w * 0.95:
        score += 60.0
        reasons.append("near_52w_high")
    elif latest >= high_52w * 0.90:
        score += 40.0
        reasons.append("within_10pct_of_52w_high")
    elif latest >= high_52w * 0.80:
        score += 20.0
        reasons.append("within_20pct_of_52w_high")
    if latest >= previous_20_high * 0.99:
        score += 20.0
        reasons.append("near_20d_breakout")
    if len(closes) >= 21 and latest > closes[-21]:
        score += 20.0
        reasons.append("positive_1m_return")
    return clamp(score), reasons


def market_regime_score(bars: list[PriceBar]) -> float:
    closes = [bar.close for bar in bars]
    latest = closes[-1]
    ma50 = moving_average(closes, 50)
    ma200 = moving_average(closes, 200)
    ma200_past = mean(closes[-220:-20]) if len(closes) >= 220 else None

    checks = [
        ma50 is not None and latest > ma50,
        ma200 is not None and latest > ma200,
        ma50 is not None and ma200 is not None and ma50 > ma200,
        ma200 is not None and ma200_past is not None and ma200 > ma200_past,
        len(closes) >= 21 and latest > closes[-21],
    ]
    return sum(20.0 for item in checks if item)


def fundamental_score(metadata: StockMetadata) -> tuple[float, list[str]]:
    if not metadata.metrics:
        return 50.0, ["fundamental_data_missing"]

    rules = [
        ("eps_yoy", 25.0, 30.0),
        ("revenue_yoy", 20.0, 20.0),
        ("eps_3y_cagr", 20.0, 25.0),
        ("roe", 17.0, 25.0),
    ]
    available_weight = 0.0
    earned = 0.0
    missing: list[str] = []
    for key, threshold, weight in rules:
        value = metadata.metrics.get(key)
        if value is None:
            missing.append(key)
            continue
        available_weight += weight
        if value >= threshold:
            earned += weight
        else:
            earned += max(0.0, min(value / threshold, 1.0)) * weight

    if available_weight == 0:
        return 50.0, ["fundamental_data_missing"]
    flags = [f"fundamental_partial_missing:{','.join(missing)}"] if missing else []
    return clamp(earned / available_weight * 100.0), flags


def bucket(score: float) -> str:
    if score >= 80:
        return "A - deeper research candidate"
    if score >= 70:
        return "B - watchlist candidate"
    if score >= 60:
        return "C - screen flag only"
    return "Reject"
