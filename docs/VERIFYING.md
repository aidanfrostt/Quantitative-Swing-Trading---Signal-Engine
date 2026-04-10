# System verification

Use this checklist to validate the stack beyond CI (ruff + pytest with dev extras only).

## First-time setup

With Docker Desktop running:

```bash
make setup
# or: ./scripts/setup_local.sh
```

This installs `.[dev]`, runs `docker compose up -d` (TimescaleDB by default; add `COMPOSE_PROFILES=kafka` for Redpanda), waits for Postgres, and runs `scripts/init_db.py`.

**Daily development** (DB + migrations + API in one terminal):

```bash
make dev
# or: bash scripts/dev.sh
```

## Quick verification script

From the repo root:

```bash
chmod +x scripts/verify_local.sh   # once
./scripts/verify_local.sh
```

Optional:

```bash
VERIFY_ML=1 ./scripts/verify_local.sh
VERIFY_RESEARCH=1 ./scripts/verify_local.sh
export RUN_INTEGRATION_TESTS=1
export DATABASE_URL=postgresql://signals:signals@localhost:5433/signals
./scripts/verify_local.sh
```

## Phase 1 — Baseline (matches CI)

```bash
pip install -e ".[dev]"
ruff check src services tests
pytest -q
```

With PyTorch / ML tests:

```bash
pip install -e ".[dev,ml]"
pytest tests/test_ml_model_forward.py -q
```

## Phase 2 — Database and migrations

1. Start TimescaleDB: `docker compose up -d timescaledb` (see [docker-compose.yml](../docker-compose.yml)).
2. `export DATABASE_URL=postgresql://signals:signals@localhost:5433/signals`
3. `python scripts/init_db.py`
4. Integration tests:

```bash
export RUN_INTEGRATION_TESTS=1
pytest tests/test_integration_db.py -v
```

## Phase 3 — Service smoke

Set `export PYTHONPATH=src`. Run each job once; **exit code 0 on NYSE holidays or weekends** is normal when `exit_if_not_nyse_trading_day()` applies.

| Service | Command | Notes |
|--------|---------|--------|
| universe_cron | `python services/universe_cron/main.py` | Needs `POLYGON_API_KEY` for real work |
| price_ingest | `python services/price_ingest/main.py` | Polygon + Kafka optional |
| technical_engine | `python services/technical_engine/main.py` | Needs `ohlcv` |
| news_ingest | `python services/news_ingest/main.py` | `PERIGON_API_KEY` |
| nlp_worker | `python services/nlp_worker/main.py` | `pip install -e ".[ml]"` |
| fundamentals_ingest | `python services/fundamentals_ingest/main.py` | Polygon |
| attribution_job | `python services/attribution_job/main.py` | Trading-day guard |
| sector_sentiment_job | `python services/sector_sentiment_job/main.py` | Trading-day guard |
| impact_job | `python services/impact_job/main.py` | Trading-day guard |
| source_scoring | `python services/source_scoring/main.py` | |
| ml_outcome_job | `python services/ml_outcome_job/main.py` | Needs `ml_predictions` rows to do work |
| signal_api | `python services/signal_api/main.py` (with `PYTHONPATH=src`) | Or `pytest tests/test_signal_api_http.py` |

API keys: copy [.env.example](../.env.example) to `.env`.

## Phase 4 — End-to-end pipeline (manual)

With DB + keys populated:

1. `universe_cron` → symbols / universe  
2. `price_ingest` → `ohlcv`  
3. `technical_engine` → `technical_features`  
4. `news_ingest` + `nlp_worker` → `news_sentiment`  
5. `fundamentals_ingest`, `attribution_job`, `sector_sentiment_job` as needed  
6. `GET /v1/signals` on `signal_api` → 200 and structured JSON  

See [SERVICES.md](SERVICES.md) for details.

## Phase 5 — Offline ML (optional)

See [DEVELOPMENT.md](DEVELOPMENT.md) (Offline move model). Requires `.[ml]`, Parquet export data, and sufficient `technical_features` / `ohlcv` history.

## Phase 6 — Research script

```bash
python scripts/research/correlation_scan.py --demo
```

## Related

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — common failures  
- [DEVELOPMENT.md](DEVELOPMENT.md) — tests and layout  
