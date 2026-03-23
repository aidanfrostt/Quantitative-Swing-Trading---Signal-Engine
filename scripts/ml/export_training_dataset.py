#!/usr/bin/env python3
"""
Export tabular features at date T plus forward return labels from daily OHLCV (no lookahead).

Features use DB tables aligned with the signal pipeline (see docs/DATA_MODEL.md).
Requires: pip install -e ".[ml]" (pyarrow for Parquet).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pandas as pd

from signal_common.config import get_settings
from signal_common.db import create_pool, run_migrations

FEATURE_SCHEMA_VERSION = "v1"

EXPORT_SQL = """
WITH ordered_daily AS (
    SELECT
        symbol_id,
        (bar_time AT TIME ZONE 'America/New_York')::date AS d,
        close,
        ROW_NUMBER() OVER (PARTITION BY symbol_id ORDER BY bar_time) AS rn
    FROM ohlcv
    WHERE interval = '1d'
),
forward AS (
    SELECT
        d1.symbol_id,
        d1.d AS as_of_date,
        (d2.close - d1.close) / NULLIF(d1.close, 0.0) AS forward_return
    FROM ordered_daily d1
    INNER JOIN ordered_daily d2
        ON d2.symbol_id = d1.symbol_id AND d2.rn = d1.rn + $3::int
),
base AS (
    SELECT
        tf.symbol_id,
        sym.ticker,
        tf.as_of_date,
        f.forward_return,
        tf.rsi_14,
        tf.macd,
        tf.macd_signal,
        tf.bb_upper,
        tf.bb_lower,
        tf.bb_mid,
        tf.vwap_daily,
        fs.pe_ratio,
        fs.price_to_book,
        fs.return_on_equity,
        fs.debt_to_equity,
        fs.revenue_growth_yoy,
        fs.fundamental_score,
        att.ret_stock_5d,
        att.ret_spy_5d,
        att.ret_sector_etf_5d,
        att.beta_spy_60d,
        att.market_component_5d,
        att.sector_component_5d,
        att.residual_5d,
        att.peer_percentile_5d,
        rs.spy_close,
        rs.spy_ma200,
        CASE WHEN rs.spy_below_ma200 THEN 1.0 ELSE 0.0 END AS spy_below_ma200_f,
        rs.vix_close,
        rs.buy_dampening_factor,
        sss.weighted_sentiment_avg AS sector_weighted_sentiment_avg,
        sss.sentiment_std AS sector_sentiment_std,
        sss.etf_return_5d AS sector_etf_return_5d,
        sss.etf_return_20d AS sector_etf_return_20d,
        sss.sentiment_z_cross_sector AS sector_sentiment_z,
        sss.performance_sentiment_spread AS sector_perf_sent_spread,
        CASE WHEN sss.divergence_flag THEN 1.0 ELSE 0.0 END AS sector_divergence_f,
        news_agg.news_sent_avg,
        news_agg.news_n::double precision AS news_n
    FROM technical_features tf
    INNER JOIN forward f
        ON f.symbol_id = tf.symbol_id AND f.as_of_date = tf.as_of_date
    INNER JOIN symbols sym ON sym.id = tf.symbol_id
    LEFT JOIN fundamentals_snapshot fs
        ON fs.symbol_id = tf.symbol_id AND fs.as_of_date = tf.as_of_date
    LEFT JOIN attribution_snapshot att
        ON att.symbol_id = tf.symbol_id AND att.as_of_date = tf.as_of_date
    LEFT JOIN regime_snapshot rs ON rs.as_of_date = tf.as_of_date
    LEFT JOIN sector_sentiment_snapshot sss
        ON sss.as_of_date = tf.as_of_date AND sss.sector_key = sym.sector_key
    LEFT JOIN LATERAL (
        SELECT
            AVG(
                ns.score
                * LEAST(GREATEST(COALESCE(ps.influence_score, 1.0), 0.25), 2.0)
                * CASE WHEN ps.is_noise THEN 0.25 ELSE 1.0 END
            ) AS news_sent_avg,
            COUNT(*)::int AS news_n
        FROM news_article_symbols nas
        INNER JOIN news_articles na ON na.id = nas.news_id
        INNER JOIN news_sentiment ns ON ns.news_id = na.id
        LEFT JOIN publisher_scores ps ON ps.source = na.source AND ps.window_days = 90
        WHERE nas.symbol_id = tf.symbol_id
          AND na.published_at::date <= tf.as_of_date
          AND na.published_at::date > tf.as_of_date - INTERVAL '14 days'
    ) news_agg ON TRUE
    WHERE tf.as_of_date >= $1::date AND tf.as_of_date <= $2::date
      AND (
          $4::text = 'all'
          OR EXISTS (
              SELECT 1 FROM filtered_universe fu
              WHERE fu.symbol_id = tf.symbol_id AND fu.as_of_date = tf.as_of_date
          )
      )
)
SELECT * FROM base
ORDER BY as_of_date, symbol_id;
"""


async def export_dataset(
    out_dir: Path,
    start: date,
    end: date,
    horizon_days: int,
    universe: str,
    big_move_tau: float,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    pool = await create_pool(settings)
    try:
        await run_migrations(pool)
        async with pool.acquire() as conn:
            rows = await conn.fetch(EXPORT_SQL, start, end, horizon_days, universe)
    finally:
        await pool.close()

    if not rows:
        raise SystemExit("No rows exported; check date range and that technical_features / ohlcv exist.")

    df = pd.DataFrame([dict(r) for r in rows])
    df["label_big_move"] = (df["forward_return"].abs() >= big_move_tau).astype("float64")

    feature_cols = [
        c
        for c in df.columns
        if c
        not in (
            "symbol_id",
            "ticker",
            "as_of_date",
            "forward_return",
            "label_big_move",
        )
    ]

    parquet_path = out_dir / "train.parquet"
    df.to_parquet(parquet_path, index=False)

    manifest = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "horizon_days": horizon_days,
        "universe": universe,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "big_move_tau": big_move_tau,
        "label_column": "forward_return",
        "classification_label_column": "label_big_move",
        "feature_columns": feature_cols,
        "row_count": len(df),
        "parquet_path": str(parquet_path.name),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(df)} rows to {parquet_path} and manifest.json")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start-date", type=lambda s: date.fromisoformat(s), required=True)
    p.add_argument("--end-date", type=lambda s: date.fromisoformat(s), required=True)
    p.add_argument("--horizon-days", type=int, default=5, help="Forward return using this many trading-day bars")
    p.add_argument(
        "--universe",
        choices=("filtered", "all"),
        default="filtered",
        help="Restrict to filtered_universe per date or all symbols with technical_features",
    )
    p.add_argument(
        "--big-move-tau",
        type=float,
        default=0.02,
        help="Absolute forward return threshold for label_big_move (classification auxiliary label)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts/ml_export"),
        help="Directory for train.parquet and manifest.json",
    )
    args = p.parse_args()
    asyncio.run(
        export_dataset(
            args.out_dir,
            args.start_date,
            args.end_date,
            args.horizon_days,
            args.universe,
            args.big_move_tau,
        )
    )


if __name__ == "__main__":
    main()
