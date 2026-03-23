"""Pure helpers for sector-level sentiment vs performance analytics."""

from __future__ import annotations

import statistics


def cross_sectional_z(values: dict[str, float]) -> dict[str, float | None]:
    """Z-score each key's value against the cross-sectional mean/std of all values."""
    xs = [v for v in values.values() if v is not None]
    if len(xs) < 2:
        return {k: None for k in values}
    m = statistics.mean(xs)
    sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
    if sd < 1e-12:
        return {k: 0.0 if values[k] is not None else None for k in values}
    out: dict[str, float | None] = {}
    for k, v in values.items():
        if v is None:
            out[k] = None
        else:
            out[k] = (v - m) / sd
    return out


def rank_percentile_0_100(values: dict[str, float]) -> dict[str, float]:
    """Percentile rank 0–100 (mid-rank) within the cross-section."""
    items = sorted((k, v) for k, v in values.items() if v is not None)
    n = len(items)
    if n == 0:
        return {}
    out: dict[str, float] = {}
    for i, (k, _v) in enumerate(items):
        out[k] = 100.0 * (i + 0.5) / n
    return out


def sentiment_etf_spread_rank(sent_ranks: dict[str, float], etf_ranks: dict[str, float]) -> dict[str, float]:
    """Difference of sentiment rank minus ETF return rank (narrative vs tape)."""
    out: dict[str, float] = {}
    for k in sent_ranks:
        if k in etf_ranks:
            out[k] = sent_ranks[k] - etf_ranks[k]
    return out


def divergence_flag(
    sentiment_avg: float | None,
    etf_ret_5d: float | None,
    eps_sent: float = 0.05,
    eps_ret: float = 0.002,
) -> bool:
    """True when signs disagree and both are material (exploratory)."""
    if sentiment_avg is None or etf_ret_5d is None:
        return False
    if abs(sentiment_avg) < eps_sent and abs(etf_ret_5d) < eps_ret:
        return False
    return (sentiment_avg >= 0) != (etf_ret_5d >= 0)
