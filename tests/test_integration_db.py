"""
Optional integration tests against a real PostgreSQL/Timescale instance.

Enable with:
  export RUN_INTEGRATION_TESTS=1
  export DATABASE_URL=postgresql://...

Default `pytest` skips these (no DB required for CI).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_EXPECTED_MIGRATION_FILES = sorted(p.name for p in _MIGRATIONS_DIR.glob("*.sql"))

_KEY_TABLES = (
    "symbols",
    "ohlcv",
    "technical_features",
    "news_articles",
    "schema_migrations",
    "sector_sentiment_snapshot",
    "ml_prediction_runs",
    "ml_predictions",
    "ml_outcomes",
)


def _require_integration_env() -> None:
    if os.environ.get("RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 and DATABASE_URL to run integration tests")


@pytest.mark.asyncio
async def test_database_connectivity_and_migrations() -> None:
    _require_integration_env()
    from signal_common.db import create_pool, run_migrations

    pool = await create_pool()
    try:
        await run_migrations(pool)
        async with pool.acquire() as conn:
            v = await conn.fetchval("SELECT 1")
            assert v == 1
            row = await conn.fetchrow("SELECT 1 FROM schema_migrations LIMIT 1")
            assert row is not None
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_expected_migration_files_applied() -> None:
    """All SQL files in migrations/ should have a row in schema_migrations after run_migrations."""
    _require_integration_env()
    from signal_common.db import create_pool, run_migrations

    pool = await create_pool()
    try:
        await run_migrations(pool)
        async with pool.acquire() as conn:
            applied = {r["filename"] for r in await conn.fetch("SELECT filename FROM schema_migrations")}
            for name in _EXPECTED_MIGRATION_FILES:
                assert name in applied, f"migration {name} not recorded in schema_migrations"
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_key_tables_exist() -> None:
    """Core and extension tables exist after migrations."""
    _require_integration_env()
    from signal_common.db import create_pool, run_migrations

    pool = await create_pool()
    try:
        await run_migrations(pool)
        async with pool.acquire() as conn:
            for table in _KEY_TABLES:
                ok = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = $1
                    )
                    """,
                    table,
                )
                assert ok, f"expected table public.{table}"
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_ohlcv_is_timescale_hypertable_when_extension_present() -> None:
    """When TimescaleDB is installed, ohlcv should be registered as a hypertable."""
    _require_integration_env()
    from signal_common.db import create_pool, run_migrations

    pool = await create_pool()
    try:
        await run_migrations(pool)
        async with pool.acquire() as conn:
            ext = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            if not ext:
                pytest.skip("timescaledb extension not present (use TimescaleDB image for ohlcv hypertable)")
            row = await conn.fetchrow(
                """
                SELECT 1 FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'public' AND hypertable_name = 'ohlcv'
                LIMIT 1
                """
            )
            assert row is not None
    finally:
        await pool.close()
