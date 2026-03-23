"""
Aggregate weighted news sentiment by sector_key and join benchmark ETF returns.

Runs after news sentiment exists; skips on non-NYSE session days.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import Any

import asyncpg

from signal_common.db import create_pool, parse_polygon_ticker, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day
from signal_common.sector_sentiment import (
    cross_sectional_z,
    divergence_flag,
    rank_percentile_0_100,
    sentiment_etf_spread_rank,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _aggregate_sector_sentiment(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT
            s.sector_key,
            MAX(s.benchmark_etf) AS benchmark_etf,
            COUNT(DISTINCT na.id)::int AS article_count,
            AVG(
                ns.score
                * LEAST(GREATEST(COALESCE(ps.influence_score, 1.0), 0.25), 2.0)
                * CASE WHEN ps.is_noise THEN 0.25 ELSE 1.0 END
            ) AS weighted_sentiment,
            STDDEV_POP(ns.score) AS sentiment_std
        FROM news_articles na
        JOIN news_article_symbols nas ON nas.news_id = na.id
        JOIN symbols s ON s.id = nas.symbol_id
        JOIN news_sentiment ns ON ns.news_id = na.id
        LEFT JOIN publisher_scores ps ON ps.source = na.source AND ps.window_days = 90
        WHERE na.published_at >= NOW() - INTERVAL '14 days'
          AND s.sector_key IS NOT NULL
          AND s.sector_key != 'unknown'
        GROUP BY s.sector_key
        """
    )


async def _etf_return_5d_20d_map(
    conn: asyncpg.Connection,
    tickers: list[str],
) -> dict[str, tuple[float | None, float | None]]:
    if not tickers:
        return {}
    rows_ids = await conn.fetch(
        "SELECT id, ticker FROM symbols WHERE ticker = ANY($1::text[])",
        [parse_polygon_ticker(t) for t in tickers],
    )
    sid_to_ticker = {int(r["id"]): str(r["ticker"]) for r in rows_ids}
    if not sid_to_ticker:
        return {}
    sids = list(sid_to_ticker.keys())
    rows = await conn.fetch(
        """
        WITH ranked AS (
            SELECT symbol_id, close,
                   ROW_NUMBER() OVER (PARTITION BY symbol_id ORDER BY bar_time DESC) AS rn
            FROM ohlcv
            WHERE interval = '1d' AND symbol_id = ANY($1::bigint[])
        )
        SELECT symbol_id,
               MAX(CASE WHEN rn = 1 THEN close END) AS c1,
               MAX(CASE WHEN rn = 5 THEN close END) AS c5,
               MAX(CASE WHEN rn = 21 THEN close END) AS c21
        FROM ranked
        WHERE rn <= 21
        GROUP BY symbol_id
        """,
        sids,
    )
    out: dict[str, tuple[float | None, float | None]] = {}
    for r in rows:
        tkr = sid_to_ticker.get(int(r["symbol_id"]))
        if not tkr:
            continue
        c1, c5, c21 = r["c1"], r["c5"], r["c21"]
        r5 = r20 = None
        if c1 is not None and c5 is not None and float(c5) != 0:
            r5 = (float(c1) - float(c5)) / float(c5)
        if c1 is not None and c21 is not None and float(c21) != 0:
            r20 = (float(c1) - float(c21)) / float(c21)
        out[tkr] = (r5, r20)
    return out


async def run() -> None:
    exit_if_not_nyse_trading_day()
    pool = await create_pool()
    await run_migrations(pool)

    as_of = date.today()

    async with pool.acquire() as conn:
        agg = await _aggregate_sector_sentiment(conn)
        if not agg:
            logger.warning("No sector sentiment aggregates; check news + NLP coverage.")
            await pool.close()
            return

        etf_tickers = list(
            dict.fromkeys(
                parse_polygon_ticker(str(r["benchmark_etf"]))
                for r in agg
                if r["benchmark_etf"]
            )
        )
        etf_rets = await _etf_return_5d_20d_map(conn, etf_tickers)

        sent_map: dict[str, float] = {}
        etf5_map: dict[str, float | None] = {}
        std_map: dict[str, float | None] = {}

        for row in agg:
            sk = str(row["sector_key"])
            w = float(row["weighted_sentiment"]) if row["weighted_sentiment"] is not None else None
            if w is not None:
                w = max(-1.0, min(1.0, w))
            sent_map[sk] = w if w is not None else 0.0
            std_map[sk] = float(row["sentiment_std"]) if row["sentiment_std"] is not None else None
            be = row["benchmark_etf"]
            bt = parse_polygon_ticker(str(be)) if be else None
            if bt and bt in etf_rets:
                e5, _e20 = etf_rets[bt]
                etf5_map[sk] = e5
            else:
                etf5_map[sk] = None

        etf5_clean = {k: v for k, v in etf5_map.items() if v is not None}
        z_map = cross_sectional_z(sent_map)
        r_sent = rank_percentile_0_100(sent_map)
        r_etf = rank_percentile_0_100(etf5_clean)
        spread_rank = sentiment_etf_spread_rank(r_sent, r_etf)

        for row in agg:
            sk = str(row["sector_key"])
            be = row["benchmark_etf"]
            be_s = str(be) if be else None
            bt = parse_polygon_ticker(str(be)) if be else None
            e5, e20 = (None, None)
            if bt and bt in etf_rets:
                e5, e20 = etf_rets[bt]

            z = z_map.get(sk)
            spr = spread_rank.get(sk)
            div = divergence_flag(sent_map.get(sk), e5)

            raw: dict[str, Any] = {
                "benchmark_etf_ticker": bt,
                "sentiment_rank_pctile": r_sent.get(sk),
                "etf_return_rank_pctile": r_etf.get(sk),
            }

            await conn.execute(
                """
                INSERT INTO sector_sentiment_snapshot (
                    as_of_date, sector_key, benchmark_etf, article_count,
                    weighted_sentiment_avg, sentiment_std,
                    etf_return_5d, etf_return_20d,
                    sentiment_z_cross_sector, performance_sentiment_spread, divergence_flag,
                    raw, computed_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW())
                ON CONFLICT (as_of_date, sector_key) DO UPDATE SET
                    benchmark_etf = EXCLUDED.benchmark_etf,
                    article_count = EXCLUDED.article_count,
                    weighted_sentiment_avg = EXCLUDED.weighted_sentiment_avg,
                    sentiment_std = EXCLUDED.sentiment_std,
                    etf_return_5d = EXCLUDED.etf_return_5d,
                    etf_return_20d = EXCLUDED.etf_return_20d,
                    sentiment_z_cross_sector = EXCLUDED.sentiment_z_cross_sector,
                    performance_sentiment_spread = EXCLUDED.performance_sentiment_spread,
                    divergence_flag = EXCLUDED.divergence_flag,
                    raw = EXCLUDED.raw,
                    computed_at = NOW()
                """,
                as_of,
                sk,
                be_s,
                int(row["article_count"] or 0),
                sent_map.get(sk),
                std_map.get(sk),
                e5,
                e20,
                z,
                spr,
                div,
                json.dumps(raw),
            )

    await pool.close()
    logger.info("Sector sentiment snapshot completed for %s (%d sectors)", as_of, len(agg))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
