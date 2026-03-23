"""
Polygon financial ratios (v1) with vX reference fallback; throttled per symbol.

Plan limits may block endpoints—rows are skipped on error. Skips on non-NYSE days.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day
from signal_common.polygon_client import PolygonClient
from signal_common.signal_logic import extract_ratios_from_polygon_payload, fundamental_score_from_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    if not settings.polygon_api_key:
        raise RuntimeError("POLYGON_API_KEY is required")

    pool = await create_pool()
    await run_migrations(pool)
    client = PolygonClient()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.ticker FROM filtered_universe fu
            JOIN symbols s ON s.id = fu.symbol_id
            WHERE fu.as_of_date = (SELECT MAX(as_of_date) FROM filtered_universe)
            LIMIT $1
            """,
            settings.fundamentals_ingest_symbol_limit,
        )
        if not rows:
            rows = await conn.fetch("SELECT id, ticker FROM symbols WHERE ticker = 'SPY' LIMIT 1")

    as_of = date.today()

    for r in rows:
        sid = int(r["id"])
        ticker = r["ticker"]
        data: dict = {}
        try:
            data = await client.get_financial_ratios_v1(ticker)
        except Exception as e:
            logger.debug("ratios v1 %s: %s", ticker, e)
            try:
                data = await client.get_vx_reference_financials(ticker)
            except Exception as e2:
                logger.warning("fundamentals skip %s: %s", ticker, e2)
                continue

        extracted = extract_ratios_from_polygon_payload(data)
        pe = extracted.get("pe_ratio")
        pb = extracted.get("price_to_book")
        roe = extracted.get("return_on_equity")
        de = extracted.get("debt_to_equity")
        rg = extracted.get("revenue_growth_yoy")
        fscore = fundamental_score_from_metrics(pe, roe, de, rg)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO fundamentals_snapshot (
                    symbol_id, as_of_date, pe_ratio, price_to_book, return_on_equity,
                    debt_to_equity, revenue_growth_yoy, fundamental_score, raw
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                ON CONFLICT (symbol_id, as_of_date) DO UPDATE SET
                    pe_ratio = EXCLUDED.pe_ratio,
                    price_to_book = EXCLUDED.price_to_book,
                    return_on_equity = EXCLUDED.return_on_equity,
                    debt_to_equity = EXCLUDED.debt_to_equity,
                    revenue_growth_yoy = EXCLUDED.revenue_growth_yoy,
                    fundamental_score = EXCLUDED.fundamental_score,
                    raw = EXCLUDED.raw,
                    updated_at = NOW()
                """,
                sid,
                as_of,
                pe,
                pb,
                roe,
                de,
                rg,
                fscore,
                json.dumps(data),
            )
        logger.info("Fundamentals %s score=%.3f", ticker, fscore)
        await asyncio.sleep(0.15)

    await pool.close()
    logger.info("Fundamentals ingest done")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
