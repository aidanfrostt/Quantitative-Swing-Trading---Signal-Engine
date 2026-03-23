"""Tests for technical_z_score (signal blend input)."""

from signal_common.signal_logic import technical_z_score


def test_technical_z_score_rsi_only():
    t = technical_z_score(rsi=80.0, macd=None, close=100.0, bb_u=None, bb_l=None)
    assert abs(t - 0.6) < 1e-9


def test_technical_z_score_empty_indicators():
    assert technical_z_score(None, None, 100.0, None, None) == 0.0


def test_technical_z_score_clamped():
    t = technical_z_score(rsi=150.0, macd=None, close=100.0, bb_u=None, bb_l=None)
    assert t == 1.0
