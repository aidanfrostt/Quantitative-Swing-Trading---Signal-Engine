# Services reference

Each entry is a **Python entrypoint** under `services/<name>/main.py`. Run with `PYTHONPATH=src` (or `pip install -e .` from the repo root). Most batch jobs call `exit_if_not_nyse_trading_day()` at startup and exit **0** on weekends and NYSE holidays.

## Suggested local order (first-time)

1. `universe_cron` — builds `symbols`, `universe_snapshots`, `filtered_universe`, sector/benchmark fields.
2. `price_ingest` — backfills OHLCV for universe symbols **and** benchmark ETFs.
3. `technical_engine` — fills `technical_features` and `regime_snapshot`.
4. `news_ingest` — requires `PERIGON_API_KEY` and existing symbols.
5. `nlp_worker` — scores articles without sentiment (requires `.[ml]` extra).
6. `fundamentals_ingest` — Polygon financials (plan-dependent).
7. `attribution_job` — move attribution snapshots (needs daily history for SPY/sector ETFs).
8. `sector_sentiment_job` — aggregate sector-level news sentiment vs benchmark ETF returns into `sector_sentiment_snapshot` (after NLP + price data exist).
9. `signal_api` — HTTP server for `GET /v1/signals`, `GET /v1/sector-sentiment`, health endpoints.

Optional analytics pipeline: `impact_job` then `source_scoring` (publisher weights feed into API sentiment aggregation).

---

## `universe_cron`

- **Purpose**: Pull active US stock tickers from Polygon, compute ADV over a lookback, filter by market cap, populate `filtered_universe`, upsert `symbols`, enrich **sector** and **benchmark_etf** via Polygon v3 ticker details (throttled).
- **Inputs**: `POLYGON_API_KEY`, `DATABASE_URL`, liquidity settings from [config](../src/signal_common/config.py).
- **Outputs**: Rows in `symbols`, `universe_snapshots`, `filtered_universe`; benchmark ETF symbols seeded via `ensure_benchmark_symbols`.
- **Notes**: Heavy API usage; respect Polygon rate limits.

## `price_ingest`

- **Purpose**: Fetch aggregates from Polygon for **filtered universe symbols (capped in dev)** plus **merged benchmark tickers** (SPY, QQQ, sector ETFs, `EXTRA_BENCHMARK_ETFS`).
- **Outputs**: Inserts into `ohlcv`; may publish `OhlcvBar` messages to Kafka topics for downstream consumers.
- **Notes**: Extends lookback (e.g. 120d) so rolling beta and attribution have enough history.

## `technical_engine`

- **Purpose**: Compute RSI, MACD, Bollinger, VWAP on **daily** bars for latest `filtered_universe`; compute **regime_snapshot** from SPY and VIX (see settings `benchmark_symbol`, `vix_symbol`).
- **Inputs**: Requires OHLCV for symbols and benchmarks.

## `news_ingest`

- **Purpose**: Page Perigon articles, dedupe, match tickers appearing in text against known `symbols`, insert `news_articles` / `news_article_symbols`, optionally emit to Kafka.
- **Inputs**: `PERIGON_API_KEY`.

## `nlp_worker`

- **Purpose**: FinBERT sentiment for rows in `news_articles` missing `news_sentiment`; optional Kafka consumer mode via env.
- **Dependencies**: `pip install -e ".[ml]"` (torch/transformers).

## `fundamentals_ingest`

- **Purpose**: Polygon ratios (v1) with fallback endpoint; writes `fundamentals_snapshot` and heuristic `fundamental_score`.
- **Inputs**: `POLYGON_API_KEY`; respects `fundamentals_ingest_symbol_limit`.

## `attribution_job`

- **Purpose**: For each symbol in latest `filtered_universe`, align daily closes with SPY and sector ETF, compute 5d returns, 60d rolling beta vs SPY, residual vs market strip, sector spread component, peer percentile within `sector_key`; upsert `attribution_snapshot`.
- **Notes**: Explanatory only; see [SIGNAL_PIPELINE.md](SIGNAL_PIPELINE.md).

## `sector_sentiment_job`

- **Purpose**: Group publisher-weighted article sentiment by `sector_key` (14d), join `benchmark_etf` 5d/20d returns from `ohlcv`, compute cross-sectional z-score, rank spread, and `divergence_flag`; upsert `sector_sentiment_snapshot`.
- **Inputs**: Requires `news_sentiment` (run `nlp_worker`) and ETF OHLCV.
- **Notes**: See [SIGNAL_PIPELINE.md](SIGNAL_PIPELINE.md); global columns on `symbols` are for future multi-region use.

## `impact_job`

- **Purpose**: For news-linked symbols, compute forward returns at fixed horizons using `1h` and `1d` OHLCV; store `news_impact_observations` for calibration.

## `source_scoring`

- **Purpose**: Aggregate impact observations into `publisher_scores` (and author scores) over a rolling window; used when the API averages sentiment with source weights.

## `ml_outcome_job`

- **Purpose**: For `ml_predictions` rows with no `ml_outcomes` row yet, compute realized forward return from daily `ohlcv` when enough trading days have elapsed (same bar-offset logic as `scripts/ml/export_training_dataset.py`); upsert `ml_outcomes`.
- **Config**: Optional `ML_BIG_MOVE_TAU` (default `0.02`) sets `label_big_move` from \|return\|.
- **Notes**: Offline / research feedback loop; **not** a live signal API change. See [DEVELOPMENT.md](DEVELOPMENT.md) ML section.

## `signal_api`

- **Purpose**: FastAPI app exposing `GET /v1/signals`, `GET /v1/sector-sentiment`, `GET /health`, `GET /ready`. Authenticate with `X-API-Key` matching `SIGNAL_API_KEYS`.
- **Behavior**: On each request, loads latest technical rows, aggregates news sentiment, fundamentals, regime dampening, optional move attribution and **sector_context**, builds grouped lists and optional `signal_runs` persistence.
- **Config**: `SIGNALS_ONLY_ON_TRADING_DAYS` forces **503** off session when enabled.

## Docker / Kubernetes

- [Dockerfile.service](../Dockerfile.service) copies one service’s `main.py` to `/app/run.py`; build with `--build-arg SVC=<folder_name>` (e.g. `signal_api`, `attribution_job`).
- Cron manifests live under [deploy/k8s/base/cronjobs.yaml](../deploy/k8s/base/cronjobs.yaml).
