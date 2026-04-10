# Troubleshooting

## Batch job exits immediately with code 0

Many jobs call `exit_if_not_nyse_trading_day()` and **skip work** on weekends and NYSE holidays. That is **expected**, not a bug. Run on a US equity session day for real work.

## `signal_api` returns 401

Ensure `X-API-Key` matches one of the comma-separated keys in `SIGNAL_API_KEYS` (see `.env.example`).

## Local: page loads but “Live snapshot” errors (503 / database)

The API needs **PostgreSQL/TimescaleDB** on the host/port in `DATABASE_URL` (default **`localhost:5433`** from `docker-compose.yml`).

1. **Docker Desktop** must be running.
2. Start the DB: `docker compose up -d` (TimescaleDB only by default) or `docker compose up -d timescaledb`.
3. Apply migrations: `export DATABASE_URL=postgresql://signals:signals@localhost:5433/signals` then `python scripts/init_db.py`.
4. Or run everything in one step from the repo root: **`make dev`** or **`./scripts/dev.sh`** (starts Compose, migrations, then the API).

If Postgres is down, `/public/v1/signals` returns **503** with a short message instead of an opaque 500.

## Public routes return 404

Set **`ENABLE_PUBLIC_SIGNAL_UI=true`** in `.env` (or the environment). `./scripts/dev.sh` defaults this to **`true`** for local use unless you set it to `false` in `.env`.

## Empty or sparse signals

Trace upstream tables: `ohlcv`, `technical_features`, `news_sentiment`, `fundamentals_snapshot`, `attribution_snapshot`, `sector_sentiment_snapshot`. See [DATA_MODEL.md](DATA_MODEL.md).

## Migration or Timescale errors

- Use a **TimescaleDB** image for `ohlcv` hypertable DDL (see `docker-compose.yml`), not plain Postgres.  
- Re-run `python scripts/init_db.py`; already-applied files are skipped via `schema_migrations`.

## Kafka / Redpanda connection failures

Redpanda is **optional** in Compose (profile **`kafka`**). To start it and create topics: set **`COMPOSE_PROFILES=kafka`** in `.env` (or export it), then `docker compose up -d`. On the host, `KAFKA_BOOTSTRAP_SERVERS=localhost:19092` matches the compose port mapping. The **signal API** does not require Kafka to start; batch jobs that publish bars/news may.

## Polygon / Perigon errors

Set `POLYGON_API_KEY` and `PERIGON_API_KEY` in `.env`. Without keys, ingest jobs may fail or return no data.

## Polygon `429 Too Many Requests` during `universe_cron`

**Stocks Basic (free)** is **5 calls per minute** across Polygon stock endpoints. The shared `PolygonClient` enforces **minimum spacing** between calls—about **`60 / POLYGON_MAX_CALLS_PER_MINUTE`** seconds (default **5** → ~**12s** between requests)—so traffic is not sent in bursts that trigger **429**. If you still see **429**, wait and retry, or raise **`POLYGON_MAX_CALLS_PER_MINUTE`** / set **`0`** to disable only if your plan allows higher throughput.

## ML export: “No rows exported”

You need overlapping `technical_features` and daily `ohlcv` for your date range and horizon. Widen `--start-date` / `--end-date` or backfill prices and technicals first.

## `ModuleNotFoundError: No module named 'tests.support'` when running pytest

Some Python installs (e.g. **Anaconda**) ship a top-level `tests` package in `site-packages`, which can shadow this repo’s `tests/` directory. The repo includes [`tests/__init__.py`](../tests/__init__.py) so the local package wins when pytest adds the project root to the path. Use a **venv** dedicated to this project if imports still conflict.

## Integration tests skipped

`tests/test_integration_db.py` runs only when `RUN_INTEGRATION_TESTS=1` and `DATABASE_URL` point at a live database.

## `role "signals" does not exist` when Docker is running

The app is probably connecting to a **different** PostgreSQL on your machine (often something already bound to port **5432**), not the Compose TimescaleDB container. This repo maps TimescaleDB to host port **5433** (see `docker-compose.yml`). Use:

`DATABASE_URL=postgresql://signals:signals@localhost:5433/signals`

## Docker Desktop errors (`input/output error`, `containerd`, pull failures)

These come from the **local Docker engine** (disk full, corrupted Docker data, or Desktop needing a restart), not from this repo.

1. Quit Docker Desktop completely and start it again (or reboot).
2. In Docker Desktop: **Troubleshoot** → **Clean / Purge data** only if you accept losing local images/volumes.
3. Ensure enough free disk space.
4. When `docker compose up -d timescaledb` works, run:

```bash
export DATABASE_URL=postgresql://signals:signals@localhost:5433/signals
python scripts/init_db.py
export RUN_INTEGRATION_TESTS=1
pytest tests/test_integration_db.py -v
```

Or: `./scripts/verify_local.sh` with `RUN_INTEGRATION_TESTS=1` and `DATABASE_URL` set (see [VERIFYING.md](VERIFYING.md)).
