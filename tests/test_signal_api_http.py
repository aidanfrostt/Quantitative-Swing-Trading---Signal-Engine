"""HTTP-level tests for `signal_api` with dependency overrides (no real DB)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.signal_api.main import app, get_pool, get_settings
from signal_common.config import Settings
from signal_common.schemas import SignalsPayload
from tests.conftest import make_fake_pool_for_build_signals
from tests.support.fake_db import FakeConnection, FakePool
from tests.test_build_signals import _bullish_main_row


@pytest.fixture
def api_client(
    dev_settings_with_api_key: Settings,
    signal_api_test_key: str,
) -> TestClient:
    pool = make_fake_pool_for_build_signals(
        universe_version="2025-03-01",
        main_rows=[_bullish_main_row()],
        ret_5d_symbol_rows=[{"symbol_id": 1, "c1": 105.0, "c5": 100.0}],
        sentiment_rows=[{"ticker": "TEST", "s": 1.0, "n": 2}],
        fundamentals_rows=[],
        attribution_rows=[],
        regime_row={
            "buy_dampening_factor": 1.0,
            "spy_below_ma200": False,
            "vix_close": 14.0,
        },
        spy_id=10,
        qqq_id=11,
        ret_5d_ctx_rows=[
            {"symbol_id": 10, "c1": 400.0, "c5": 400.0},
            {"symbol_id": 11, "c1": 300.0, "c5": 300.0},
        ],
    )

    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_settings] = lambda: dev_settings_with_api_key
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_v1_signals_401_without_key() -> None:
    client = TestClient(app)
    try:
        r = client.get("/v1/signals")
        assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_v1_signals_200_validates_payload(api_client: TestClient, signal_api_test_key: str) -> None:
    r = api_client.get("/v1/signals", headers={"X-API-Key": signal_api_test_key})
    assert r.status_code == 200
    payload = SignalsPayload.model_validate(r.json())
    assert len(payload.signals) >= 1
    assert payload.symbols_evaluated >= 1
    assert payload.market_context is not None


def test_health() -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_v1_sector_sentiment_200(
    dev_settings_with_api_key: Settings,
    signal_api_test_key: str,
) -> None:
    from signal_common.schemas import SectorSentimentPayload

    sector_rows = [
        {
            "as_of_date": "2025-01-15",
            "sector_key": "technology",
            "benchmark_etf": "XLK",
            "article_count": 10,
            "weighted_sentiment_avg": 0.2,
            "sentiment_std": 0.1,
            "etf_return_5d": 0.01,
            "etf_return_20d": 0.02,
            "sentiment_z_cross_sector": 0.5,
            "performance_sentiment_spread": 1.0,
            "divergence_flag": False,
        }
    ]
    pool = FakePool(FakeConnection.from_queue([sector_rows]))
    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_settings] = lambda: dev_settings_with_api_key
    try:
        client = TestClient(app)
        r = client.get("/v1/sector-sentiment", headers={"X-API-Key": signal_api_test_key})
        assert r.status_code == 200
        payload = SectorSentimentPayload.model_validate(r.json())
        assert payload.as_of_date == "2025-01-15"
        assert len(payload.rows) == 1
        assert payload.rows[0].sector_key == "technology"
    finally:
        app.dependency_overrides.clear()


def test_v1_signals_503_only_trading_days(
    dev_settings_with_api_key: Settings,
    signal_api_test_key: str,
) -> None:
    s = dev_settings_with_api_key.model_copy(update={"signals_only_on_trading_days": True})
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
    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_settings] = lambda: s
    try:
        client = TestClient(app)
        with patch("services.signal_api.main.is_nyse_trading_day", return_value=False):
            r = client.get("/v1/signals", headers={"X-API-Key": signal_api_test_key})
        assert r.status_code == 503
    finally:
        app.dependency_overrides.clear()
