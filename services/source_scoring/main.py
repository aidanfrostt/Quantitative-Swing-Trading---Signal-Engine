"""Roll publisher/author scores from `news_impact_observations` (rolling window). Skips on non-NYSE days."""

from __future__ import annotations

import asyncio
import logging
import statistics

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WINDOW_DAYS = 90


async def upsert_publisher(
    conn: asyncpg.Connection,
    source: str,
    influence: float,
    reliability: float,
    noise: bool,
) -> None:
    await conn.execute(
        """
        INSERT INTO publisher_scores (source, influence_score, reliability_score, is_noise, window_days)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (source, window_days) DO UPDATE SET
            influence_score = EXCLUDED.influence_score,
            reliability_score = EXCLUDED.reliability_score,
            is_noise = EXCLUDED.is_noise,
            updated_at = NOW()
        """,
        source,
        influence,
        reliability,
        noise,
        WINDOW_DAYS,
    )


async def upsert_author(
    conn: asyncpg.Connection,
    author: str,
    influence: float,
    reliability: float,
    noise: bool,
) -> None:
    await conn.execute(
        """
        INSERT INTO author_scores (author, influence_score, reliability_score, is_noise, window_days)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (author, window_days) DO UPDATE SET
            influence_score = EXCLUDED.influence_score,
            reliability_score = EXCLUDED.reliability_score,
            is_noise = EXCLUDED.is_noise,
            updated_at = NOW()
        """,
        author,
        influence,
        reliability,
        noise,
        WINDOW_DAYS,
    )


async def run() -> None:
    exit_if_not_nyse_trading_day()
    get_settings()
    pool = await create_pool()
    await run_migrations(pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT na.source, na.author,
                   ns.score AS sentiment,
                   nio.forward_return,
                   nio.horizon_hours
            FROM news_impact_observations nio
            JOIN news_articles na ON na.id = nio.news_id
            JOIN news_sentiment ns ON ns.news_id = na.id
            WHERE na.published_at >= NOW() - ($1 * INTERVAL '1 day')
            """,
            WINDOW_DAYS,
        )

    by_source: dict[str, list[tuple[float, float]]] = {}
    by_author: dict[str, list[tuple[float, float]]] = {}

    for r in rows:
        sent = float(r["sentiment"] or 0)
        ret = float(r["forward_return"] or 0)
        src = (r["source"] or "").strip() or "unknown"
        auth = (r["author"] or "").strip() or "unknown"
        by_source.setdefault(src, []).append((sent, ret))
        by_author.setdefault(auth, []).append((sent, ret))

    def compute(pairs: list[tuple[float, float]]) -> tuple[float, float, bool] | None:
        if len(pairs) < 5:
            return None
        signs = []
        vol_spread = []
        for sent, ret in pairs:
            pred = 1 if sent > 0.05 else (-1 if sent < -0.05 else 0)
            if pred == 0:
                continue
            actual = 1 if ret > 0 else (-1 if ret < 0 else 0)
            if actual != 0:
                signs.append(1 if pred == actual else 0)
            vol_spread.append(abs(ret))
        if not signs:
            return None
        reliability = sum(signs) / len(signs)
        influence = statistics.mean([s * r for s, r in pairs])
        noise = (statistics.mean(vol_spread) if vol_spread else 0) > 0.05 and reliability < 0.45
        return influence, reliability, noise

    async with pool.acquire() as conn:
        for key, pairs in by_source.items():
            out = compute(pairs)
            if not out:
                continue
            inf, rel, noise = out
            await upsert_publisher(conn, key, inf, rel, noise)

        for key, pairs in by_author.items():
            out = compute(pairs)
            if not out:
                continue
            inf, rel, noise = out
            await upsert_author(conn, key, inf, rel, noise)

    await pool.close()
    logger.info("Source scoring done")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
