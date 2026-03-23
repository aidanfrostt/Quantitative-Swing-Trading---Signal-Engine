# Data model

The database is **PostgreSQL** with the **TimescaleDB** extension for `ohlcv` time-series. Schema evolves via ordered SQL files in [migrations/](../migrations/).

## Migration order

| File | Purpose |
|------|---------|
| `001_init.sql` | Core tables: symbols, universe snapshots, filtered universe, ohlcv hypertable, news, sentiment, impact observations, publisher/author scores, technical_features, regime_snapshot, signal_runs |
| `002_retention.sql` | Retention policies / hygiene for Timescale (if present) |
| `003_fundamentals.sql` | `fundamentals_snapshot` and related indexes |
| `004_news_provider_default.sql` | News provider metadata tweaks |
| `005_attribution.sql` | `symbols` sector columns; `attribution_snapshot` |
| `006_sector_sentiment.sql` | `symbols` region/country/currency; `sector_sentiment_snapshot` |
| `007_ml_feedback.sql` | `ml_prediction_runs`, `ml_predictions`, `ml_outcomes` (offline model feedback) |

Apply with `python scripts/init_db.py` or any code path that calls `run_migrations()` (most services do this on startup).

## Core entities

### `symbols`

Reference row per tradable ticker. Extended in `005_attribution.sql` with:

- `sector_key` — normalized slug for grouping peers
- `sector_label` — human-readable label from Polygon details
- `benchmark_etf` — sector proxy ETF ticker (e.g. XLK), used for attribution and OHLCV joins

Extended in `006_sector_sentiment.sql` with nullable **global hooks**: `region`, `country`, `market_currency` (for future non-US universes).

Benchmark rows (SPY, QQQ, sector ETFs) are inserted by `ensure_benchmark_symbols` in [db.py](../src/signal_common/db.py) so price ingestion can attach OHLCV without listing them in the equity universe.

### `universe_snapshots` / `filtered_universe`

- **universe_snapshots**: raw Polygon ticker rows per `as_of_date` (audit / replay).
- **filtered_universe**: liquidity and market-cap filter outputs; **downstream jobs typically key off the latest `as_of_date`.**

### `ohlcv`

Hypertable keyed by `(symbol_id, interval, bar_time)`. Intervals used in code include `1d`, `1h`, and optionally `1m` (ingestion may cap symbol count in dev).

### News pipeline

- **news_articles**: deduped by `(provider, article_id)`; Perigon is the default provider.
- **news_article_symbols**: many-to-many link from article to `symbol_id`.
- **news_sentiment**: one row per article with model name and score in `[-1, 1]`.
- **news_impact_observations**: forward returns after article time (see `impact_job`).
- **publisher_scores** / **author_scores**: rolling influence/reliability from `source_scoring`.

### `technical_features`

Per `(symbol_id, as_of_date)`: RSI, MACD, Bollinger, VWAP snapshot computed by `technical_engine` from daily OHLCV.

### `regime_snapshot`

Per `as_of_date`: SPY vs 200-day MA, VIX, and a **buy dampening factor** applied to positive conviction in the API (see [SIGNAL_PIPELINE.md](SIGNAL_PIPELINE.md)).

### `fundamentals_snapshot`

Latest Polygon-derived ratios and a scalar `fundamental_score` per symbol/date window.

### `attribution_snapshot`

Per `(symbol_id, as_of_date)`: explanatory move decomposition vs SPY and sector ETF, peer percentile within `sector_key`. Populated by `attribution_job`; consumed by `signal_api` as the latest row per symbol.

### `sector_sentiment_snapshot`

Per `(as_of_date, sector_key)`: aggregate weighted news sentiment for the sector (14d articles), benchmark ETF returns, cross-sectional z-score, rank spread vs ETF performance, `divergence_flag`. Populated by `sector_sentiment_job`; read by `signal_api` as the latest `as_of_date` across all sectors.

### `signal_runs`

Optional JSON audit of full `SignalsPayload` when `PERSIST_SIGNAL_RUNS=true`.

### ML feedback (`007_ml_feedback.sql`)

Research / offline evaluation only; **not** wired into `GET /v1/signals` by default.

- **`ml_prediction_runs`**: one row per trained artifact (`model_version`, `feature_schema_version`, `hyperparams`, optional `artifact_path`).
- **`ml_predictions`**: scores per `(symbol_id, as_of_date, horizon_days)` linked to a run; optional `raw_features` / `feature_hash` for audit.
- **`ml_outcomes`**: one row per prediction (`realized_return`, `evaluated_at`, optional `label_big_move`) filled after the forward window is observable in `ohlcv` (see `ml_outcome_job`).

## `schema_migrations`

Table used by [db.py](../src/signal_common/db.py) to record which migration files have been applied; safe to re-run `init_db` on an existing DB (already-applied files are skipped).
