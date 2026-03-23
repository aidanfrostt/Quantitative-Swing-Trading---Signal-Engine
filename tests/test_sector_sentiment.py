"""Unit tests for sector cross-sectional analytics."""

from signal_common.sector_sentiment import (
    cross_sectional_z,
    divergence_flag,
    rank_percentile_0_100,
    sentiment_etf_spread_rank,
)


def test_cross_sectional_z_two_sectors():
    z = cross_sectional_z({"a": 0.0, "b": 2.0})
    assert z["a"] is not None and z["b"] is not None
    assert z["a"] < z["b"]


def test_cross_sectional_z_single_sector_returns_none():
    z = cross_sectional_z({"a": 0.5})
    assert z["a"] is None


def test_rank_percentile_order():
    r = rank_percentile_0_100({"x": -1.0, "y": 0.0, "z": 1.0})
    assert r["x"] < r["y"] < r["z"]


def test_spread_rank_difference():
    s = {"a": 50.0, "b": 50.0}
    e = {"a": 0.0, "b": 100.0}
    sp = sentiment_etf_spread_rank(s, e)
    assert sp["a"] == 50.0
    assert sp["b"] == -50.0


def test_divergence_flag_opposite_signs():
    assert divergence_flag(0.5, -0.01) is True


def test_divergence_flag_same_sign():
    assert divergence_flag(0.5, 0.01) is False
