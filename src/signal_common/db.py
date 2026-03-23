"""Database pool, ordered SQL migrations, and ticker normalization."""

from __future__ import annotations

import re
from pathlib import Path

import asyncpg

from signal_common.config import Settings, get_settings
from signal_common.sector_etfs import merged_benchmark_tickers


def _dsn_for_asyncpg(url: str) -> str:
    """Normalize postgresql:// URL for asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def _split_sql_statements(sql: str) -> list[str]:
    """
    Split a migration file into statements for asyncpg.

    Executing very large multi-statement scripts in one ``execute()`` can hit
    asyncpg issues with some DDL/SELECT mixes (e.g. Timescale notices/results).
    Our SQL files use `;` as a statement terminator at end of line.
    """
    raw: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        current.append(line)
        if line.rstrip().endswith(";"):
            block = "\n".join(current).strip()
            if block:
                raw.append(block)
            current = []
    if current:
        block = "\n".join(current).strip()
        if block:
            raw.append(block)
    return raw


def _sql_statement_is_executable(stmt: str) -> bool:
    """True if there is any non-comment SQL (avoids asyncpg issues on comment-only batches)."""
    for line in stmt.splitlines():
        s = line.strip()
        if s and not s.startswith("--"):
            return True
    return False


async def ensure_benchmark_symbols(conn: asyncpg.Connection, extra_etfs_csv: str = "") -> None:
    """Insert SPY, sector ETFs, QQQ, and optional extras into `symbols` if missing."""
    for t in merged_benchmark_tickers(extra_etfs_csv):
        await conn.execute(
            """
            INSERT INTO symbols (ticker, name, exchange, is_active)
            VALUES ($1, $2, $3, TRUE)
            ON CONFLICT (ticker) DO NOTHING
            """,
            t,
            f"Benchmark {t}",
            "ETF",
        )


async def create_pool(settings: Settings | None = None) -> asyncpg.Pool:
    settings = settings or get_settings()
    return await asyncpg.create_pool(_dsn_for_asyncpg(settings.database_url), min_size=1, max_size=10)


async def run_migrations(pool: asyncpg.Pool, migrations_dir: Path | None = None) -> None:
    """Apply SQL migrations in order (001_*.sql, 002_*.sql, ...)."""
    base = migrations_dir or Path(__file__).resolve().parents[2] / "migrations"
    if not base.is_dir():
        return
    files = sorted(base.glob("*.sql"), key=lambda p: p.name)
    async with pool.acquire() as conn:
        # NOTICE messages from IF NOT EXISTS / extension DDL can trigger asyncpg
        # decode errors on multi-statement executes; suppress for migration runs.
        await conn.execute("SET client_min_messages TO ERROR")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        for path in files:
            row = await conn.fetchrow("SELECT 1 FROM schema_migrations WHERE filename = $1", path.name)
            if row:
                continue
            sql = path.read_text(encoding="utf-8")
            for stmt in _split_sql_statements(sql):
                if not _sql_statement_is_executable(stmt):
                    continue
                await conn.execute(stmt)
            await conn.execute("INSERT INTO schema_migrations (filename) VALUES ($1)", path.name)


def parse_polygon_ticker(symbol: str) -> str:
    """Normalize vendor ticker to uppercase alphanumeric + optional dot."""
    s = symbol.strip().upper()
    return re.sub(r"[^A-Z0-9.]", "", s) or s
