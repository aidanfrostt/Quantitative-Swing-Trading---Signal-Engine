"""
Daily technical features + SPY/VIX regime snapshot. Requires OHLCV for benchmark symbols.

Skips on non-NYSE session days.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import pandas as pd

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations
from signal_common.indicators import bollinger, macd, rolling_vwap, rsi
from signal_common.job_guards import exit_if_not_nyse_trading_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_daily_series(conn, symbol_id: int, days: int = 400) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT bar_time, open, high, low, close, volume, vwap
        FROM ohlcv
        WHERE symbol_id = $1 AND interval = '1d'
        ORDER BY bar_time ASC
        """,
        symbol_id,
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["bar_time"] = pd.to_datetime(df["bar_time"], utc=True)
    return df.tail(days)


async def run() -> None:
    exit_if_not_nyse_trading_day()
    settings = get_settings()
    pool = await create_pool()
    await run_migrations(pool)

    async with pool.acquire() as conn:
        fu = await conn.fetch(
            """
            SELECT s.id, s.ticker FROM filtered_universe fu
            JOIN symbols s ON s.id = fu.symbol_id
            WHERE fu.as_of_date = (SELECT MAX(as_of_date) FROM filtered_universe)
            """
        )
        if not fu:
            fu = await conn.fetch("SELECT id, ticker FROM symbols WHERE ticker IN ('SPY') LIMIT 1")

    for row in fu:
        sid = int(row["id"])
        async with pool.acquire() as conn:
            df = await load_daily_series(conn, sid)
        if df.empty or len(df) < 30:
            continue
        close = df["close"].astype(float)
        vol = df["volume"].astype(float)

        rsi_s = rsi(close, 14)
        macd_line, macd_sig = macd(close)
        bb_u, bb_m, bb_l = bollinger(close, 20, 2.0)
        vwap_col = rolling_vwap(close, vol)

        last_i = -1
        rv = rsi_s.iloc[last_i]
        rsi_v = float(rv) if not pd.isna(rv) else None
        mv = macd_line.iloc[last_i]
        ms = macd_sig.iloc[last_i]
        macd_v = float(mv) if not pd.isna(mv) else None
        macd_sig_v = float(ms) if not pd.isna(ms) else None
        bu = bb_u.iloc[last_i]
        bl = bb_l.iloc[last_i]
        bm = bb_m.iloc[last_i]
        bb_u_v = float(bu) if not pd.isna(bu) else None
        bb_l_v = float(bl) if not pd.isna(bl) else None
        bb_m_v = float(bm) if not pd.isna(bm) else None
        vw = vwap_col.iloc[last_i]
        vwap_d = float(vw) if not pd.isna(vw) else None

        as_of: date = df["bar_time"].dt.date.iloc[last_i]

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO technical_features (
                    symbol_id, as_of_date, rsi_14, macd, macd_signal,
                    bb_upper, bb_lower, bb_mid, vwap_daily
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (symbol_id, as_of_date) DO UPDATE SET
                    rsi_14 = EXCLUDED.rsi_14,
                    macd = EXCLUDED.macd,
                    macd_signal = EXCLUDED.macd_signal,
                    bb_upper = EXCLUDED.bb_upper,
                    bb_lower = EXCLUDED.bb_lower,
                    bb_mid = EXCLUDED.bb_mid,
                    vwap_daily = EXCLUDED.vwap_daily
                """,
                sid,
                as_of,
                rsi_v,
                macd_v,
                macd_sig_v,
                bb_u_v,
                bb_l_v,
                bb_m_v,
                vwap_d,
            )

    async with pool.acquire() as conn:
        spy_id = await conn.fetchval(
            "SELECT id FROM symbols WHERE ticker = $1", settings.benchmark_symbol
        )
        vix_id = await conn.fetchval("SELECT id FROM symbols WHERE ticker = $1", settings.vix_symbol)
        if not spy_id:
            spy_id = await conn.fetchval("SELECT id FROM symbols WHERE ticker = 'SPY'")

        if spy_id:
            df_spy = await load_daily_series(conn, int(spy_id))
            if not df_spy.empty:
                c = df_spy["close"].astype(float)
                ma200 = c.rolling(200).mean()
                spy_c = float(c.iloc[-1])
                spy_ma = float(ma200.iloc[-1]) if not pd.isna(ma200.iloc[-1]) else spy_c
                below = spy_c < spy_ma
                vix_c = None
                if vix_id:
                    df_v = await load_daily_series(conn, int(vix_id))
                    if not df_v.empty:
                        vix_c = float(df_v["close"].astype(float).iloc[-1])
                damp = 1.0
                if below and vix_c is not None and vix_c >= settings.regime_vix_threshold:
                    damp = settings.regime_spy_below_ma_dampen
                elif below:
                    damp = min(damp, settings.regime_spy_below_ma_dampen + 0.25)

                d_reg = df_spy["bar_time"].dt.date.iloc[-1]
                await conn.execute(
                    """
                    INSERT INTO regime_snapshot (
                        as_of_date, spy_close, spy_ma200, spy_below_ma200, vix_close, buy_dampening_factor
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (as_of_date) DO UPDATE SET
                        spy_close = EXCLUDED.spy_close,
                        spy_ma200 = EXCLUDED.spy_ma200,
                        spy_below_ma200 = EXCLUDED.spy_below_ma200,
                        vix_close = EXCLUDED.vix_close,
                        buy_dampening_factor = EXCLUDED.buy_dampening_factor
                    """,
                    d_reg,
                    spy_c,
                    spy_ma,
                    below,
                    vix_c,
                    damp,
                )

    await pool.close()
    logger.info("Technical engine completed")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
