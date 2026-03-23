"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from signal_common.config import Settings
from tests.support.fake_db import FakeConnection, FakePool


@pytest.fixture
def dev_settings() -> Settings:
    """API settings with persistence off for tests."""
    return Settings(
        persist_signal_runs=False,
        signals_only_on_trading_days=False,
    )


@pytest.fixture
def signal_api_test_key() -> str:
    return "test-api-key"


@pytest.fixture
def dev_settings_with_api_key(signal_api_test_key: str) -> Settings:
    return Settings(
        persist_signal_runs=False,
        signals_only_on_trading_days=False,
        signal_api_keys=signal_api_test_key,
    )


def make_fake_pool_for_build_signals(
    *,
    universe_version: str,
    main_rows: list[dict],
    ret_5d_symbol_rows: list[dict],
    sentiment_rows: list[dict],
    fundamentals_rows: list[dict],
    attribution_rows: list[dict],
    regime_row: dict | None,
    spy_id: int | None,
    qqq_id: int | None,
    ret_5d_ctx_rows: list[dict],
    sector_rows: list[dict] | None = None,
) -> FakePool:
    """
    Queue responses matching the call order inside `build_signals` for one pass
    (no empty symbol_ids / tickers edge cases).
    """
    q: list = [
        universe_version,
        main_rows,
        ret_5d_symbol_rows,
        sentiment_rows,
        fundamentals_rows,
        attribution_rows,
        regime_row,
        spy_id,
        qqq_id,
    ]
    ctx_ids = [i for i in (spy_id, qqq_id) if i is not None]
    if ctx_ids:
        q.append(ret_5d_ctx_rows)
    q.append(sector_rows if sector_rows is not None else [])
    return FakePool(FakeConnection.from_queue(q))
