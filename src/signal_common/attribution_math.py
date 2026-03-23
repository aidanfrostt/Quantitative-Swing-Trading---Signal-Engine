"""Pure math for move attribution (returns alignment, rolling beta, peer rank)."""

from __future__ import annotations

import numpy as np


def ret_5d_from_closes(closes: np.ndarray) -> float | None:
    """Match signal_api: (latest close − close 4 bars earlier) / that older close (5 daily bars)."""
    if len(closes) < 5:
        return None
    c1 = float(closes[-1])
    c5 = float(closes[-5])
    if c5 == 0:
        return None
    return (c1 - c5) / c5


def rolling_beta_spy(y: np.ndarray, x: np.ndarray, window: int = 60) -> float | None:
    """OLS beta of stock daily returns (y) on SPY (x), last `window` overlapping observations."""
    if len(y) != len(x) or len(y) < window:
        return None
    yw = y[-window:].astype(float)
    xw = x[-window:].astype(float)
    xm = xw - np.mean(xw)
    ym = yw - np.mean(yw)
    denom = float(np.dot(xm, xm))
    if denom < 1e-18:
        return None
    return float(np.dot(xm, ym) / denom)


def peer_percentile(value: float, peers: list[float]) -> float | None:
    if not peers:
        return None
    below = sum(1 for p in peers if p < value)
    equal = sum(1 for p in peers if p == value)
    return 100.0 * (below + 0.5 * equal) / len(peers)
