"""Backfill recent OHLCV from Polygon into Timescale and Kafka topics (dev caps symbol count)."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import asyncpg

from signal_common.config import get_settings
from signal_common.db import create_pool, ensure_benchmark_symbols, parse_polygon_ticker, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day
from signal_common.kafka_bus import TOPIC_OHLCV_1D, TOPIC_OHLCV_1H, TOPIC_OHLCV_1M, make_producer
from signal_common.polygon_client import PolygonClient
from signal_common.schemas import OhlcvBar
from signal_common.sector_etfs import merged_benchmark_tickers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def ingest_bars(
    pool: asyncpg.Pool,
    producer,
    symbol: str,
    interval: str,
    multiplier: int,
    timespan: str,
    start: date,
    end: date,
) -> None:
    client = PolygonClient()
    data = await client.get_aggregates(symbol, multiplier, timespan, start, end)
    results = data.get("results") or []
    sid = await pool.fetchval("SELECT id FROM symbols WHERE ticker = $1", symbol)
    if not sid:
        logger.warning("Unknown symbol %s", symbol)
        return

    rows = []
    topic = {"1m": TOPIC_OHLCV_1M, "1h": TOPIC_OHLCV_1H, "day": TOPIC_OHLCV_1D}[timespan]
    import datetime as dt

    for r in results:
        ts_ms = int(r.get("t") or 0)
        if not ts_ms:
            continue
        ts = dt.datetime.utcfromtimestamp(ts_ms / 1000.0).replace(tzinfo=dt.timezone.utc)
        o = float(r.get("o") or 0)
        h = float(r.get("h") or 0)
        low = float(r.get("l") or 0)
        c = float(r.get("c") or 0)
        v = float(r.get("v") or 0)
        vw = float(r["vw"]) if r.get("vw") is not None else None
        rows.append((sid, interval, ts, o, h, low, c, v, vw))
        bar = OhlcvBar(
            symbol=symbol,
            interval=interval,
            ts=ts,
            open=o,
            high=h,
            low=low,
            close=c,
            volume=v,
            vwap=vw,
        )
        await producer.send_and_wait(topic, value=bar.model_dump())

    if not rows:
        return

    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO ohlcv (symbol_id, interval, bar_time, open, high, low, close, volume, vwap)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (symbol_id, interval, bar_time) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume, vwap = EXCLUDED.vwap
            """,
            rows,
        )


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    if not settings.polygon_api_key:
        raise RuntimeError("POLYGON_API_KEY is required")

    pool = await create_pool()
    await run_migrations(pool)
    producer = await make_producer()

    end = date.today()
    start = end - timedelta(days=120)

    async with pool.acquire() as conn:
        await ensure_benchmark_symbols(conn, settings.extra_benchmark_etfs)
        ref = merged_benchmark_tickers(settings.extra_benchmark_etfs)
        tickers = await conn.fetch(
            """
            SELECT s.ticker FROM filtered_universe fu
            JOIN symbols s ON s.id = fu.symbol_id
            WHERE fu.as_of_date = (SELECT MAX(as_of_date) FROM filtered_universe)
            LIMIT 50
            """
        )
        uni = [parse_polygon_ticker(r["ticker"]) for r in tickers]
        symbols = list(dict.fromkeys(uni + ref))
    if not uni:
        logger.warning("No filtered universe; run universe_cron first. Ingesting benchmarks only.")
        symbols = list(dict.fromkeys(ref or ["SPY"]))

    for sym in symbols:
        await ingest_bars(pool, producer, sym, "1d", 1, "day", start, end)
        await ingest_bars(pool, producer, sym, "1h", 1, "hour", start, end)
        # 1m is heavy; optional for dev
        # await ingest_bars(pool, producer, sym, "1m", 1, "minute", start, end)

    await producer.stop()
    await pool.close()
    logger.info("Price ingest done for %d symbols", len(symbols))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
