import pandas as pd

from signal_common.indicators import bollinger, macd, rsi


def test_rsi_bounds():
    close = pd.Series([100.0, 101.2, 99.5, 102.0, 98.0, 103.0, 97.0, 104.0] * 10)
    out = rsi(close, 14)
    last = float(out.iloc[-1])
    assert not pd.isna(last)
    assert 0 <= last <= 100


def test_macd_length():
    close = pd.Series([float(i) for i in range(1, 100)])
    line, sig = macd(close)
    assert len(line) == len(close)


def test_bollinger():
    close = pd.Series([100.0 + i * 0.1 for i in range(50)])
    upper, mid, lower = bollinger(close, 10)
    assert upper.iloc[-1] >= mid.iloc[-1] >= lower.iloc[-1]
