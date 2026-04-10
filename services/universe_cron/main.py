"""
Daily universe refresh: Polygon active US tickers, ADV + market-cap liquidity filter.

Skips on non-NYSE session days (see `job_guards`).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import date, timedelta

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, ensure_benchmark_symbols, parse_polygon_ticker, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day
from signal_common.polygon_client import PolygonClient
from signal_common.sector_etfs import sector_from_polygon_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def upsert_symbol(conn: asyncpg.Connection, ticker: str, name: str | None, exchange: str | None) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO symbols (ticker, name, exchange, is_active)
        VALUES ($1, $2, $3, TRUE)
        ON CONFLICT (ticker) DO UPDATE SET
            name = COALESCE(EXCLUDED.name, symbols.name),
            exchange = COALESCE(EXCLUDED.exchange, symbols.exchange),
            updated_at = NOW()
        RETURNING id
        """,
        ticker,
        name,
        exchange,
    )
    assert row is not None
    return int(row["id"])


async def load_all_tickers(client: PolygonClient) -> list[dict]:
    out: list[dict] = []
    next_url: str | None = None
    while True:
        data = await client.get_tickers_page(next_url)
        for r in data.get("results") or []:
            out.append(r)
        next_url = data.get("next_url")
        if not next_url:
            break
        if "apiKey=" not in next_url:
            sep = "&" if "?" in next_url else "?"
            next_url = f"{next_url}{sep}apiKey={client._key}"
    return out


def dedupe_ticker_rows(rows: list[dict]) -> list[dict]:
    """Polygon pages can repeat tickers; keep one row per parsed ticker (last wins)."""
    by_ticker: dict[str, dict] = {}
    for row in rows:
        t = parse_polygon_ticker(row.get("ticker") or "")
        if t:
            by_ticker[t] = row
    return list(by_ticker.values())


async def fetch_adv_volumes(client: PolygonClient, trading_days: list[date]) -> dict[str, list[float]]:
    vols: dict[str, list[float]] = defaultdict(list)
    for d in trading_days:
        try:
            data = await client.get_grouped_daily(d)
        except Exception as e:
            logger.warning("grouped daily failed %s: %s", d, e)
            continue
        for row in data.get("results") or []:
            t = parse_polygon_ticker(row.get("T") or "")
            v = float(row.get("v") or 0)
            vols[t].append(v)
    return vols


async def fetch_ticker_details_map(
    client: PolygonClient,
    tickers: list[str],
    concurrency: int = 1,
) -> dict[str, dict]:
    """Per-ticker Polygon v3 details: market_cap, sector_key, sector_label, benchmark_etf."""
    sem = asyncio.Semaphore(concurrency)
    out: dict[str, dict] = {}

    async def one(t: str) -> None:
        async with sem:
            try:
                js = await client.get_ticker_details_v3(t)
                res = js.get("results") or {}
                if isinstance(res, list):
                    res = res[0] if res else {}
                if not isinstance(res, dict):
                    res = {}
                mc = res.get("market_cap")
                mc_f = float(mc) if mc is not None else None
                sk, sl, etf = sector_from_polygon_result(res)
                out[t] = {
                    "market_cap": mc_f,
                    "sector_key": sk,
                    "sector_label": sl,
                    "benchmark_etf": etf,
                }
            except Exception as e:
                logger.debug("ticker details %s: %s", t, e)

    await asyncio.gather(*(one(t) for t in tickers))
    return out


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    if not settings.polygon_api_key:
        raise RuntimeError("POLYGON_API_KEY is required for universe_cron")

    pool = await create_pool()
    await run_migrations(pool)
    client = PolygonClient()

    tickers = dedupe_ticker_rows(await load_all_tickers(client))
    logger.info("Fetched %d unique ticker rows from Polygon", len(tickers))

    as_of = date.today()
    trading_days: list[date] = []
    d = as_of
    while len(trading_days) < settings.adv_lookback_days + 5:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            trading_days.append(d)
        if len(trading_days) >= settings.adv_lookback_days:
            break
    trading_days = sorted(trading_days)[-settings.adv_lookback_days :]

    adv_by_ticker = await fetch_adv_volumes(client, trading_days)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await ensure_benchmark_symbols(conn, settings.extra_benchmark_etfs)
            for row in tickers:
                t = parse_polygon_ticker(row.get("ticker") or "")
                if not t:
                    continue
                await upsert_symbol(conn, t, row.get("name"), row.get("primary_exchange"))

            await conn.execute("DELETE FROM universe_snapshots WHERE as_of_date = $1", as_of)
            for row in tickers:
                t = parse_polygon_ticker(row.get("ticker") or "")
                if not t:
                    continue
                sid = await conn.fetchval("SELECT id FROM symbols WHERE ticker = $1", t)
                if not sid:
                    continue
                await conn.execute(
                    """
                    INSERT INTO universe_snapshots (as_of_date, symbol_id, is_tradable, raw)
                    VALUES ($1, $2, $3, $4::jsonb)
                    """,
                    as_of,
                    sid,
                    True,
                    json.dumps(row),
                )

            volumes = adv_by_ticker
            adv_candidates: list[str] = []
            adv_values: dict[str, float] = {}
            for t, vs in volumes.items():
                if len(vs) < max(1, settings.adv_lookback_days // 2):
                    continue
                adv = sum(vs) / len(vs)
                if adv >= settings.min_adv_shares:
                    adv_candidates.append(t)
                    adv_values[t] = adv

            logger.info("ADV filter passed: %d symbols", len(adv_candidates))
            details_map = await fetch_ticker_details_map(client, adv_candidates)

            await conn.execute("DELETE FROM filtered_universe WHERE as_of_date = $1", as_of)
            for t in adv_candidates:
                d = details_map.get(t) or {}
                mc = d.get("market_cap")
                if mc is not None and mc < settings.min_market_cap_usd:
                    continue
                sid = await conn.fetchval("SELECT id FROM symbols WHERE ticker = $1", t)
                if not sid:
                    continue
                await conn.execute(
                    """
                    INSERT INTO filtered_universe (as_of_date, symbol_id, market_cap_usd, adv_shares)
                    VALUES ($1, $2, $3, $4)
                    """,
                    as_of,
                    sid,
                    mc,
                    adv_values.get(t),
                )
                sk = d.get("sector_key")
                sl = d.get("sector_label")
                be = d.get("benchmark_etf")
                await conn.execute(
                    """
                    UPDATE symbols
                    SET sector_key = COALESCE($2, sector_key),
                        sector_label = COALESCE($3, sector_label),
                        benchmark_etf = COALESCE($4, benchmark_etf),
                        updated_at = NOW()
                    WHERE ticker = $1
                    """,
                    t,
                    sk,
                    sl,
                    be,
                )

    await pool.close()
    logger.info("Universe cron completed for %s", as_of)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
