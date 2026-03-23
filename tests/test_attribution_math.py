import numpy as np

from signal_common.attribution_math import peer_percentile, ret_5d_from_closes, rolling_beta_spy


def test_ret_5d_matches_signal_api_pattern():
    closes = np.array([100.0, 101.0, 102.0, 103.0, 104.0], dtype=float)
    r = ret_5d_from_closes(closes)
    assert r is not None
    assert abs(r - (104.0 - 100.0) / 100.0) < 1e-9


def test_rolling_beta_spy_perfect_correlation():
    x = np.linspace(0.001, 0.06, 60)
    y = 1.5 * x
    b = rolling_beta_spy(y, x, window=60)
    assert b is not None
    assert abs(b - 1.5) < 1e-6


def test_peer_percentile_mid():
    peers = [0.01, 0.02, 0.03, 0.04]
    p = peer_percentile(0.025, peers)
    assert p is not None
    assert abs(p - 50.0) < 1e-6
