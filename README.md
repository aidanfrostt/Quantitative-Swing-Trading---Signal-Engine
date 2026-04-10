# Signal Generation System

Python microservices for market data ingestion, NLP sentiment, technical features, **Polygon fundamentals**, and swing-trading signals. See `.env.example` for configuration.

**Disclaimer:** Signals are quantitative model outputs, not investment advice. **Outcomes are not guaranteed.** Short selling requires broker borrow/locate; the API only labels `position_intent`.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Index of all documentation |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, batch vs API, `signal_common` module map |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Tables, migrations, what each store is for |
| [docs/SERVICES.md](docs/SERVICES.md) | Every service: purpose, inputs/outputs, run order |
| [docs/SIGNAL_PIPELINE.md](docs/SIGNAL_PIPELINE.md) | How conviction, regime, news, and move attribution work |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Tests, lint, repo layout for contributors |
| [docs/VERIFYING.md](docs/VERIFYING.md) | Full system verification script and checklist |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues when running jobs or the API |

## Public GitHub + Railway (API + web UI)

**Do not commit `.env`** (it is gitignored). Use [`.env.example`](.env.example) as the template for local and document-only reference.

| Resource | Description |
|----------|-------------|
| [deploy/GITHUB_AND_RAILWAY_SETUP.md](deploy/GITHUB_AND_RAILWAY_SETUP.md) | **Step-by-step:** create a public GitHub repo, push this project, deploy on Railway, set variables, generate a domain |
| [deploy/railway.md](deploy/railway.md) | Railway-focused checklist (Postgres, Docker, health, optional Netlify + CORS) |
| [`railway.json`](railway.json) | Config-as-code: `Dockerfile.service`, `/health` check |

The Docker image serves the **FastAPI** app and the static **`web/`** UI. Set `ENABLE_PUBLIC_SIGNAL_UI=true` on Railway for browser access to `/public/v1/signals` without embedding API keys in the client.

## Quick start

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. From the repo root (a venv is optional but recommended: `python -m venv .venv && source .venv/bin/activate`):

```bash
make dev
```

(No Make? Run `bash scripts/dev.sh` — same behavior.)

This installs the Python package if needed, copies `.env.example` → `.env` when `.env` is missing, starts **TimescaleDB** (port `5433`), applies migrations, and runs the **Signal API** on **http://127.0.0.1:8080** (stop with `Ctrl+C`). **Redpanda/Kafka** is optional: add **`COMPOSE_PROFILES=kafka`** to `.env` if you run ingestion workers that publish to Kafka (see [`.env.example`](.env.example)).

3. Edit `.env` with real `POLYGON_API_KEY`, `PERIGON_API_KEY`, and `SIGNAL_API_KEYS` so ingestion and authenticated API calls work.

**First-time machine setup only** (skip if you already ran it): `make setup` — same as `./scripts/setup_local.sh` (deps + Docker + migrations, does not start the API).

Equivalent without Make: `./scripts/dev.sh`

## How this runs (batch vs real time)

- **Batch jobs** (`universe_cron`, `price_ingest`, `technical_engine`, `news_ingest`, `fundamentals_ingest`, `attribution_job`, etc.) run **on a schedule or when you manually start them**, then exit. Many use `exit_if_not_nyse_trading_day()` so they **skip work** on weekends and NYSE holidays (exit code 0).
- **The signal API** (`services/signal_api/main.py`) is a **long-running web server**. Each `GET /v1/signals` call **recomputes** scores from the **latest database state** at that moment. It is **not** a continuous streaming “real-time” engine unless you run ingestion on a tight loop and keep OHLCV/news fresh.
- **News sentiment** reflects articles ingested into the DB (e.g. Perigon) and scored by the NLP worker; **latency** depends on how often you run `news_ingest` and `nlp_worker`, not on the API alone.

## Configuration

Default `KAFKA_BOOTSTRAP_SERVERS` in code matches **local** Redpanda (`localhost:19092` in `docker-compose.yml`). In Kubernetes, use the in-cluster broker (e.g. `redpanda:9092` from the ConfigMap).

## Local development

Use **Quick start** above for DB + API. For **batch jobs** (ingestion, features), set `PYTHONPATH=src` and run the service you need:

```bash
export PYTHONPATH=src
python services/universe_cron/main.py
python services/price_ingest/main.py
python services/attribution_job/main.py
python services/sector_sentiment_job/main.py
python services/fundamentals_ingest/main.py
```

See [docs/SERVICES.md](docs/SERVICES.md) for order and dependencies.

**Run the full pipeline once** (universe → prices → technicals → news → NLP → fundamentals → attribution → sector):

```bash
./scripts/run_full_pipeline.sh
```

If **Redpanda/Kafka is not running**, set `KAFKA_PUBLISH=false` in `.env` so `price_ingest` and `news_ingest` still write to PostgreSQL without a broker.

NLP worker needs the ML extra: `pip install -e ".[ml]"` (or use `Dockerfile.nlp`). The script installs `[ml]` before `nlp_worker`.

**Polygon rate limits:** **Stocks Basic** allows **5 API calls per minute**. The `PolygonClient` spaces requests by about **`60 / POLYGON_MAX_CALLS_PER_MINUTE`** seconds (default **5** → ~**12s** between calls) to avoid burst **429**s. Raise the cap for paid tiers or set **`0`** to disable client-side throttling. Full batch runs are slow on Basic; **HTTP 429** can still happen—wait and retry.

**Offline move model (optional):** after migrations and `technical_features` / `ohlcv` history exist, run `python scripts/ml/export_training_dataset.py ...`, then `python scripts/ml/train_move_model.py ...` (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)). Outputs are research-only; not investment advice.

News ingest uses **Perigon** (`PERIGON_API_KEY`); populate `symbols` (e.g. run universe cron) so headlines can be matched to tickers.

## Trading calendar

Batch jobs that depend on the US equity session call `exit_if_not_nyse_trading_day()` and **exit successfully (code 0)** on **NYSE holidays** and weekends. Kubernetes `CronJob` schedules still fire on holidays; the guard prevents work. **Kubernetes does not know the NYSE calendar**—the application does.

## Signal API (`GET /v1/signals`, `GET /v1/sector-sentiment`)

`GET /v1/signals` returns `long_candidates`, `short_candidates`, `watchlist`, and `signals` (top by \|conviction\|), plus `market_session` (`nyse_trading_day`, `nyse_calendar_date`). Set `SIGNALS_ONLY_ON_TRADING_DAYS=true` to return **503** on non-session days.

Each record includes `thesis`, `evidence`, `confidence_tier`, and `master_conviction` (blend of technical, sentiment, fundamentals, regime). Rows are optionally appended to **`signal_runs`** when `PERSIST_SIGNAL_RUNS=true`.

Optional **`move_attribution`** explains recent **5d** price action vs **SPY** (rolling beta strip), a **sector ETF** proxy from Polygon `sic_description` / industry text (mapped in `src/signal_common/sector_etfs.py`), and **peer percentile** within the same `sector_key` in the filtered universe. `market_context` summarizes SPY/QQQ 5d returns and regime/VIX when data exists. **`sector_context`** lists aggregate **sector news sentiment vs benchmark ETF** rows when `sector_sentiment_job` has populated `sector_sentiment_snapshot` (also available via `GET /v1/sector-sentiment`). This layer is **explanatory**: beta on short windows is noisy, sector ETFs are imperfect proxies, and peer ranks depend on universe coverage.

Offline **exploratory** correlation reports: `python scripts/research/correlation_scan.py --demo` (see [docs/SIGNAL_PIPELINE.md](docs/SIGNAL_PIPELINE.md)).

## Kubernetes

Apply manifests under `deploy/k8s/` (see `deploy/k8s/README.md`).
