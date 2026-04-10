"""Behavioral tests for `build_signals` using a scripted fake asyncpg connection."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.signal_api.main import build_signals
from signal_common.config import Settings
from signal_common.schemas import Horizon, SignalAction
from tests.conftest import make_fake_pool_for_build_signals


def _bullish_main_row() -> dict:
    return {
        "ticker": "TEST",
        "symbol_id": 1,
        "rsi_14": 100.0,
        "macd": 5.0,
        "bb_upper": 100.0,
        "bb_lower": 0.0,
        "bb_mid": 50.0,
        "vwap_daily": 50.0,
        "last_close": 100.0,
    }


@pytest.mark.asyncio
async def test_build_signals_buy_when_conviction_high(dev_settings: Settings) -> None:
    pool = make_fake_pool_for_build_signals(
        universe_version="2025-03-01",
        main_rows=[_bullish_main_row()],
        ret_5d_symbol_rows=[{"symbol_id": 1, "c1": 105.0, "c5": 100.0}],
        sentiment_rows=[{"ticker": "TEST", "s": 1.0, "n": 3}],
        fundamentals_rows=[],
        attribution_rows=[],
        regime_row={
            "buy_dampening_factor": 1.0,
            "spy_below_ma200": False,
            "vix_close": 15.0,
        },
        spy_id=10,
        qqq_id=11,
        ret_5d_ctx_rows=[
            {"symbol_id": 10, "c1": 400.0, "c5": 400.0},
            {"symbol_id": 11, "c1": 300.0, "c5": 300.0},
        ],
    )
    async with pool.acquire() as conn:
        payload = await build_signals(conn, dev_settings, Horizon.d1, 50)

    assert payload.symbols_evaluated == 1
    assert len(payload.signals) == 1
    rec = payload.signals[0]
    assert rec.action == SignalAction.BUY
    assert rec.master_conviction > dev_settings.signal_buy_threshold
    assert rec.move_attribution is None
    assert "TEST" in rec.thesis


@pytest.mark.asyncio
async def test_build_signals_regime_dampens_positive_conviction(dev_settings: Settings) -> None:
    pool = make_fake_pool_for_build_signals(
        universe_version="2025-03-01",
        main_rows=[_bullish_main_row()],
        ret_5d_symbol_rows=[{"symbol_id": 1, "c1": 100.0, "c5": 100.0}],
        sentiment_rows=[],
        fundamentals_rows=[],
        attribution_rows=[],
        regime_row={
            "buy_dampening_factor": 0.5,
            "spy_below_ma200": True,
            "vix_close": 15.0,
        },
        spy_id=10,
        qqq_id=11,
        ret_5d_ctx_rows=[
            {"symbol_id": 10, "c1": 400.0, "c5": 400.0},
            {"symbol_id": 11, "c1": 300.0, "c5": 300.0},
        ],
    )
    async with pool.acquire() as conn:
        payload = await build_signals(conn, dev_settings, Horizon.d1, 50)

    rec = payload.signals[0]
    blended = rec.metrics["blended_pre_regime"]
    assert blended > 0
    expected = blended * 0.5
    assert abs(rec.master_conviction - expected) < 1e-6
    assert rec.regime_adjustment == 0.5


@pytest.mark.asyncio
async def test_build_signals_includes_attribution_when_present(dev_settings: Settings) -> None:
    pool = make_fake_pool_for_build_signals(
        universe_version="2025-03-01",
        main_rows=[_bullish_main_row()],
        ret_5d_symbol_rows=[{"symbol_id": 1, "c1": 100.0, "c5": 100.0}],
        sentiment_rows=[],
        fundamentals_rows=[],
        attribution_rows=[
            {
                "symbol_id": 1,
                "ret_spy_5d": 0.01,
                "ret_sector_etf_5d": 0.02,
                "beta_spy_60d": 1.1,
                "market_component_5d": 0.011,
                "sector_component_5d": 0.001,
                "residual_5d": 0.05,
                "peer_percentile_5d": 75.0,
                "data_quality": "ok",
                "benchmark_etf": "XLK",
            }
        ],
        regime_row={
            "buy_dampening_factor": 1.0,
            "spy_below_ma200": False,
            "vix_close": 12.0,
        },
        spy_id=10,
        qqq_id=11,
        ret_5d_ctx_rows=[
            {"symbol_id": 10, "c1": 400.0, "c5": 400.0},
            {"symbol_id": 11, "c1": 300.0, "c5": 300.0},
        ],
    )
    async with pool.acquire() as conn:
        payload = await build_signals(conn, dev_settings, Horizon.d1, 50)

    rec = payload.signals[0]
    assert rec.move_attribution is not None
    assert rec.move_attribution.beta_spy == pytest.approx(1.1)
    assert rec.move_attribution.sector_etf == "XLK"
    assert "attribution" in rec.metrics
    assert rec.metrics["attribution"]["beta_spy"] == pytest.approx(1.1)


@pytest.mark.asyncio
async def test_build_signals_503_when_only_trading_days_and_not_session() -> None:
    s = Settings(persist_signal_runs=False, signals_only_on_trading_days=True)
    pool = make_fake_pool_for_build_signals(
        universe_version="x",
        main_rows=[],
        ret_5d_symbol_rows=[],
        sentiment_rows=[],
        fundamentals_rows=[],
        attribution_rows=[],
        regime_row=None,
        spy_id=None,
        qqq_id=None,
        ret_5d_ctx_rows=[],
    )
    # Patch calendar: not a trading day -> HTTPException before DB heavy use... actually
    # build_signals checks trading first, then uses conn. We still need pool for acquire pattern
    # when testing via build_signals directly - it will raise before any fetch if not trading day.

    from unittest.mock import patch

    with patch("services.signal_api.main.is_nyse_trading_day", return_value=False):
        async with pool.acquire() as conn:
            with pytest.raises(HTTPException) as ei:
                await build_signals(conn, s, Horizon.d1, 50)
            assert ei.value.status_code == 503


@pytest.mark.asyncio
async def test_build_signals_symbols_evaluated_zero_when_no_technicals(dev_settings: Settings) -> None:
    pool = make_fake_pool_for_build_signals(
        universe_version="2025-03-01",
        main_rows=[],
        ret_5d_symbol_rows=[],
        sentiment_rows=[],
        fundamentals_rows=[],
        attribution_rows=[],
        regime_row={
            "buy_dampening_factor": 1.0,
            "spy_below_ma200": False,
            "vix_close": 15.0,
        },
        spy_id=10,
        qqq_id=11,
        ret_5d_ctx_rows=[
            {"symbol_id": 10, "c1": 400.0, "c5": 400.0},
            {"symbol_id": 11, "c1": 300.0, "c5": 300.0},
        ],
        sector_rows=[],
    )
    async with pool.acquire() as conn:
        payload = await build_signals(conn, dev_settings, Horizon.d1, 50)
    assert payload.symbols_evaluated == 0
    assert len(payload.signals) == 0
    assert len(payload.long_candidates) == 0
