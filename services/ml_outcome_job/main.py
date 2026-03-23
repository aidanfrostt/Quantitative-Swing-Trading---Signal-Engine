"""
Backfill ml_outcomes.realized_return when the forward horizon has enough daily bars.

Uses the same trading-day offset as export_training_dataset (no calendar-day shortcut).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTCOME_SQL = """
WITH ordered_daily AS (
    SELECT
        symbol_id,
        (bar_time AT TIME ZONE 'America/New_York')::date AS d,
        close,
        ROW_NUMBER() OVER (PARTITION BY symbol_id ORDER BY bar_time) AS rn
    FROM ohlcv
    WHERE interval = '1d'
),
pending AS (
    SELECT p.id, p.symbol_id, p.as_of_date, p.horizon_days
    FROM ml_predictions p
    LEFT JOIN ml_outcomes o ON o.prediction_id = p.id
    WHERE o.prediction_id IS NULL
)
SELECT
    pe.id AS prediction_id,
    (d2.close - d1.close) / NULLIF(d1.close, 0.0) AS realized_return
FROM pending pe
INNER JOIN ordered_daily d1 ON d1.symbol_id = pe.symbol_id AND d1.d = pe.as_of_date
INNER JOIN ordered_daily d2 ON d2.symbol_id = pe.symbol_id AND d2.rn = d1.rn + pe.horizon_days;
"""


async def run_once(pool: asyncpg.Pool, big_move_tau: float) -> int:
    async with pool.acquire() as conn:
        rows = await conn.fetch(OUTCOME_SQL)
    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    n = 0
    async with pool.acquire() as conn:
        for r in rows:
            rr = r["realized_return"]
            if rr is None:
                continue
            fr = float(rr)
            lbl = abs(fr) >= big_move_tau
            await conn.execute(
                """
                INSERT INTO ml_outcomes (prediction_id, realized_return, evaluated_at, label_big_move)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (prediction_id) DO UPDATE SET
                    realized_return = EXCLUDED.realized_return,
                    evaluated_at = EXCLUDED.evaluated_at,
                    label_big_move = EXCLUDED.label_big_move
                """,
                int(r["prediction_id"]),
                fr,
                now,
                lbl,
            )
            n += 1
    return n


async def main() -> None:
    settings = get_settings()
    tau = float(os.environ.get("ML_BIG_MOVE_TAU", "0.02"))
    pool = await create_pool(settings)
    try:
        await run_migrations(pool)
        n = await run_once(pool, tau)
        logger.info("Updated %s ml_outcomes rows", n)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
