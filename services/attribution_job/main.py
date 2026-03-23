"""
Nightly move attribution: beta vs SPY, sector ETF context, sector peer percentile.

Skips on non-NYSE session days.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import date, timedelta

import asyncpg
import numpy as np

from signal_common.attribution_math import peer_percentile, ret_5d_from_closes, rolling_beta_spy
from signal_common.config import get_settings
from signal_common.db import create_pool, parse_polygon_ticker, run_migrations
from signal_common.job_guards import exit_if_not_nyse_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _symbol_ids_for_tickers(conn: asyncpg.Connection, tickers: list[str]) -> dict[str, int]:
    rows = await conn.fetch("SELECT id, ticker FROM symbols WHERE ticker = ANY($1::text[])", tickers)
    return {str(r["ticker"]): int(r["id"]) for r in rows}


async def _load_daily_closes(
    conn: asyncpg.Connection,
    symbol_ids: list[int],
    start_d: date,
) -> dict[int, list[tuple[date, float]]]:
    if not symbol_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT symbol_id, bar_time::date AS d, close
        FROM ohlcv
        WHERE interval = '1d' AND symbol_id = ANY($1::bigint[])
          AND bar_time::date >= $2
        ORDER BY symbol_id, bar_time
        """,
        symbol_ids,
        start_d,
    )
    out: dict[int, list[tuple[date, float]]] = defaultdict(list)
    for r in rows:
        sid = int(r["symbol_id"])
        d = r["d"]
        if isinstance(d, date):
            out[sid].append((d, float(r["close"])))
    return dict(out)


def _align_closes(
    stock: list[tuple[date, float]],
    other: list[tuple[date, float]],
) -> tuple[np.ndarray, np.ndarray]:
    sm = {d: c for d, c in stock}
    om = {d: c for d, c in other}
    common = sorted(set(sm) & set(om))
    if len(common) < 5:
        return np.array([]), np.array([])
    return np.array([sm[d] for d in common], dtype=float), np.array([om[d] for d in common], dtype=float)


def _align_three(
    stock: list[tuple[date, float]],
    spy: list[tuple[date, float]],
    sector: list[tuple[date, float]] | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    s1, p1 = _align_closes(stock, spy)
    if len(s1) < 5:
        return s1, p1, None
    if not sector:
        return s1, p1, None
    sm = {d: c for d, c in stock}
    pm = {d: c for d, c in spy}
    sem = {d: c for d, c in sector}
    common = sorted(set(sm) & set(pm) & set(sem))
    if len(common) < 5:
        return s1, p1, None
    return (
        np.array([sm[d] for d in common], dtype=float),
        np.array([pm[d] for d in common], dtype=float),
        np.array([sem[d] for d in common], dtype=float),
    )


def _compute_metrics(
    stock_c: np.ndarray,
    spy_c: np.ndarray,
    sector_c: np.ndarray | None,
) -> dict:
    rs = ret_5d_from_closes(stock_c)
    rp = ret_5d_from_closes(spy_c)
    rsec = ret_5d_from_closes(sector_c) if sector_c is not None and len(sector_c) >= 5 else None

    y = np.diff(stock_c.astype(float)) / stock_c.astype(float)[:-1]
    x = np.diff(spy_c.astype(float)) / spy_c.astype(float)[:-1]
    m = min(len(y), len(x))
    if m < 2:
        y = np.array([])
        x = np.array([])
    else:
        y = y[-m:]
        x = x[-m:]

    beta = rolling_beta_spy(y, x, window=60) if len(y) >= 60 else None
    dq = "ok"
    if len(y) < 60:
        dq = "insufficient_history"
    elif beta is None:
        dq = "beta_unavailable"

    spy_ret = rp
    mkt = beta * spy_ret if beta is not None and spy_ret is not None else None
    residual = rs - mkt if rs is not None and mkt is not None else None

    sector_adj = None
    sector_comp = None
    if rsec is not None and spy_ret is not None:
        sector_adj = rsec - spy_ret
        if beta is not None:
            sector_comp = beta * sector_adj

    return {
        "ret_stock_5d": rs,
        "ret_spy_5d": spy_ret,
        "ret_sector_etf_5d": rsec,
        "beta_spy_60d": beta,
        "market_component_5d": mkt,
        "sector_component_5d": sector_comp,
        "residual_5d": residual,
        "data_quality": dq,
    }


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    pool = await create_pool()
    await run_migrations(pool)

    as_of = date.today()
    start_d = as_of - timedelta(days=400)

    async with pool.acquire() as conn:
        fu = await conn.fetch(
            """
            SELECT fu.symbol_id, s.ticker, s.sector_key, s.benchmark_etf
            FROM filtered_universe fu
            JOIN symbols s ON s.id = fu.symbol_id
            WHERE fu.as_of_date = (SELECT MAX(as_of_date) FROM filtered_universe)
            """
        )
        if not fu:
            logger.warning("No filtered_universe; nothing to attribute.")
            await pool.close()
            return

        spy_t = parse_polygon_ticker(settings.benchmark_symbol)
        tickers_needed = {spy_t}
        for r in fu:
            be = r["benchmark_etf"]
            if be:
                tickers_needed.add(parse_polygon_ticker(str(be)))

        sid_map = await _symbol_ids_for_tickers(conn, list(tickers_needed))
        spy_id = sid_map.get(spy_t)
        if not spy_id:
            logger.error("Benchmark %s missing from symbols; run universe_cron / price_ingest.", spy_t)
            await pool.close()
            return

        symbol_rows = [(int(r["symbol_id"]), str(r["ticker"]), r["sector_key"], r["benchmark_etf"]) for r in fu]

        all_ids = [spy_id] + [sid for sid, _, _, _ in symbol_rows]
        for _, _, _, be in symbol_rows:
            if be:
                bid = sid_map.get(parse_polygon_ticker(str(be)))
                if bid:
                    all_ids.append(bid)

        all_ids = list(dict.fromkeys(all_ids))
        closes_map = await _load_daily_closes(conn, all_ids, start_d)
        spy_series = closes_map.get(spy_id, [])

        peer_lists: dict[str, list[float]] = defaultdict(list)
        for sid, _, sk, _ in symbol_rows:
            st = closes_map.get(sid, [])
            if len(st) < 5:
                continue
            arr = np.array([c for _, c in st], dtype=float)
            rv = ret_5d_from_closes(arr)
            if rv is not None:
                peer_lists[str(sk) if sk else "unknown"].append(rv)

        for sid, tick, sk, be in symbol_rows:
            st = closes_map.get(sid, [])
            if len(st) < 5:
                continue

            sec_series: list[tuple[date, float]] | None = None
            if be:
                bid = sid_map.get(parse_polygon_ticker(str(be)))
                if bid:
                    sec_series = closes_map.get(bid)

            stock_c, spy_c, sector_c = _align_three(st, spy_series, sec_series)
            if len(stock_c) < 5:
                continue

            comp = _compute_metrics(stock_c, spy_c, sector_c)
            sk_str = str(sk) if sk else "unknown"
            peers = list(peer_lists.get(sk_str, []))
            pp = None
            rsv = comp.get("ret_stock_5d")
            if rsv is not None and peers:
                pp = peer_percentile(rsv, peers)

            raw = {"ticker": tick}
            await conn.execute(
                """
                INSERT INTO attribution_snapshot (
                    symbol_id, as_of_date, ret_stock_5d, ret_spy_5d, ret_sector_etf_5d,
                    beta_spy_60d, market_component_5d, sector_component_5d, residual_5d,
                    peer_percentile_5d, data_quality, raw, computed_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW())
                ON CONFLICT (symbol_id, as_of_date) DO UPDATE SET
                    ret_stock_5d = EXCLUDED.ret_stock_5d,
                    ret_spy_5d = EXCLUDED.ret_spy_5d,
                    ret_sector_etf_5d = EXCLUDED.ret_sector_etf_5d,
                    beta_spy_60d = EXCLUDED.beta_spy_60d,
                    market_component_5d = EXCLUDED.market_component_5d,
                    sector_component_5d = EXCLUDED.sector_component_5d,
                    residual_5d = EXCLUDED.residual_5d,
                    peer_percentile_5d = EXCLUDED.peer_percentile_5d,
                    data_quality = EXCLUDED.data_quality,
                    raw = EXCLUDED.raw,
                    computed_at = NOW()
                """,
                sid,
                as_of,
                comp["ret_stock_5d"],
                comp["ret_spy_5d"],
                comp["ret_sector_etf_5d"],
                comp["beta_spy_60d"],
                comp["market_component_5d"],
                comp["sector_component_5d"],
                comp["residual_5d"],
                pp,
                comp["data_quality"],
                json.dumps(raw),
            )

    await pool.close()
    logger.info("Attribution job completed for %s", as_of)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
