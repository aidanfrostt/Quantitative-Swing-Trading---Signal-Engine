"""
Nightly impact: forward returns at 1h / 4h / 24h after article time (uses 1h/1d OHLCV bars).

Skips on non-NYSE session days.
"""

from __future__ import annotations

import logging
from datetime import timedelta, timezone

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HORIZONS = (1.0, 4.0, 24.0)


async def price_at_or_after(
    conn: asyncpg.Connection,
    symbol_id: int,
    interval: str,
    t0,
) -> float | None:
    row = await conn.fetchrow(
        """
        SELECT close FROM ohlcv
        WHERE symbol_id = $1 AND interval = $2 AND bar_time >= $3
        ORDER BY bar_time ASC
        LIMIT 1
        """,
        symbol_id,
        interval,
        t0,
    )
    if not row:
        return None
    return float(row["close"])


async def run() -> None:
    exit_if_not_nyse_trading_day()
    get_settings()
    pool = await create_pool()
    await run_migrations(pool)

    async with pool.acquire() as conn:
        pairs = await conn.fetch(
            """
            SELECT na.id AS news_id, na.published_at, nas.symbol_id, s.ticker
            FROM news_articles na
            JOIN news_article_symbols nas ON nas.news_id = na.id
            JOIN symbols s ON s.id = nas.symbol_id
            LEFT JOIN news_sentiment ns ON ns.news_id = na.id
            WHERE ns.news_id IS NOT NULL
            ORDER BY na.published_at DESC
            LIMIT 5000
            """
        )

    for row in pairs:
        news_id = int(row["news_id"])
        symbol_id = int(row["symbol_id"])
        pub = row["published_at"]
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)

        async with pool.acquire() as conn:
            p0 = await price_at_or_after(conn, symbol_id, "1h", pub)
            if p0 is None:
                p0 = await price_at_or_after(conn, symbol_id, "1d", pub)
            if p0 is None or p0 == 0:
                continue

            for h in HORIZONS:
                t_end = pub + timedelta(hours=h)
                p1 = await price_at_or_after(conn, symbol_id, "1h", t_end)
                if p1 is None:
                    p1 = await price_at_or_after(conn, symbol_id, "1d", t_end)
                if p1 is None:
                    continue
                fwd = (p1 - p0) / p0
                await conn.execute(
                    """
                    INSERT INTO news_impact_observations (
                        news_id, symbol_id, horizon_hours, forward_return, realized_vol)
                    VALUES ($1, $2, $3, $4, NULL)
                    ON CONFLICT (news_id, symbol_id, horizon_hours) DO UPDATE SET
                        forward_return = EXCLUDED.forward_return
                    """,
                    news_id,
                    symbol_id,
                    h,
                    fwd,
                )

    await pool.close()
    logger.info("Impact job completed")


def main() -> None:
    import asyncio

    asyncio.run(run())


if __name__ == "__main__":
    main()
