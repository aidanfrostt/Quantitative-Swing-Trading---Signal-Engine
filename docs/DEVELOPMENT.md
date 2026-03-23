# Development

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

First-time **Docker + database** (see [VERIFYING.md](VERIFYING.md)):

```bash
make setup
```

**Start DB + run Signal API** (typical dev loop):

```bash
make dev
```

For ML sentiment (FinBERT worker):

```bash
pip install -e ".[ml]"
```

### Offline move model (PyTorch)

Short-horizon supervised models use **tabular features** exported from the DB (same tables as the signal pipeline) and **labels** from forward daily returns. Outputs are **research artifacts**, not investment advice.

1. **Export** Parquet + manifest (no lookahead; labels use `h` trading-day bars on `1d` OHLCV):

   ```bash
   export DATABASE_URL=postgresql://signals:signals@localhost:5433/signals
   python scripts/ml/export_training_dataset.py --start-date 2024-01-02 --end-date 2024-06-28 --out-dir artifacts/ml_export
   ```

2. **Train** (writes `artifacts/move_model.pt` and `artifacts/features.json`):

   ```bash
   python scripts/ml/train_move_model.py --parquet artifacts/ml_export/train.parquet --manifest artifacts/ml_export/manifest.json
   ```

3. **Evaluate** on held-out or full export:

   ```bash
   python scripts/ml/evaluate_model.py --parquet artifacts/ml_export/train.parquet --manifest artifacts/ml_export/manifest.json --report artifacts/eval_report.md
   ```

4. **Backfill outcomes** for rows inserted into `ml_predictions` (after `007` migration):

   ```bash
   export PYTHONPATH=src
   python services/ml_outcome_job/main.py
   ```

Optional env: `ML_BIG_MOVE_TAU` (default `0.02`) for `label_big_move` when writing `ml_outcomes`.

## Running tests and linters

From the repository root:

```bash
pytest tests/
ruff check src services tests
```

For a bundled check (ruff + pytest, optional ML / integration / research), use [scripts/verify_local.sh](../scripts/verify_local.sh) and see [VERIFYING.md](VERIFYING.md).

`pyproject.toml` sets `pythonpath` to `.` and `src` so `pytest` resolves `signal_common` and `services` without exporting `PYTHONPATH`. For ad-hoc `python` runs, use `export PYTHONPATH=src` (see root README).

Install `torch` (via `.[ml]`) before running `tests/test_ml_model_forward.py`.

### Test layers

- **Unit tests** — Pure functions (`signal_logic`, `attribution_math`, `sector_etfs`, `parse_polygon_ticker`, `technical_z_score`). No database.
- **`build_signals` tests** — [tests/test_build_signals.py](tests/test_build_signals.py) uses a **scripted fake asyncpg** connection ([tests/support/fake_db.py](tests/support/fake_db.py)) so responses follow the same call order as [services/signal_api/main.py](services/signal_api/main.py) without Postgres.
- **HTTP tests** — [tests/test_signal_api_http.py](tests/test_signal_api_http.py) uses FastAPI dependency overrides for `get_pool` / `get_settings` and `TestClient`.
- **Integration (optional)** — [tests/test_integration_db.py](tests/test_integration_db.py) is marked `@pytest.mark.integration` and **skips** unless `RUN_INTEGRATION_TESTS=1` and `DATABASE_URL` point at a real server:

```bash
export RUN_INTEGRATION_TESTS=1
export DATABASE_URL=postgresql://user:pass@localhost:5433/signals
pytest tests/test_integration_db.py -v
```

The **project root** is on pytest’s path via `pythonpath` in `pyproject.toml`, so tests can `import services.signal_api.main`.

### Research scripts

- [scripts/research/correlation_scan.py](../scripts/research/correlation_scan.py) — exploratory Pearson / lag analysis on CSVs or `--demo` synthetic data (not production metrics).

## Database

- `DATABASE_URL` must point at a PostgreSQL instance with TimescaleDB available if you use the bundled `001_init.sql` hypertable DDL.
- Apply migrations: `python scripts/init_db.py` (idempotent).

## Running a single service

```bash
export PYTHONPATH=src
python services/universe_cron/main.py
```

Replace `universe_cron` with any folder under `services/` that contains `main.py`.

## Environment

Copy `.env.example` to `.env` and fill API keys. Never commit real secrets.

## Layout

- `src/signal_common/` — shared package imported by all services.
- `services/<name>/main.py` — one entrypoint per deployable unit.
- `migrations/*.sql` — ordered schema; applied by `run_migrations`.
- `deploy/k8s/` — Kubernetes manifests and CronJobs.
- `tests/` — pytest; `asyncio_mode` is set to `auto` in `pyproject.toml`.
