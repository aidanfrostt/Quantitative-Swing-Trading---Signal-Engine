# Documentation index

Start here if you are new to the repository.

| Document | What it covers |
|----------|----------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | End-to-end system diagram, batch vs request-time flows, dependencies between components |
| [DATA_MODEL.md](DATA_MODEL.md) | PostgreSQL/Timescale tables, migrations order, what each store is for |
| [SERVICES.md](SERVICES.md) | Every runnable service under `services/`, inputs/outputs, typical run order locally |
| [SIGNAL_PIPELINE.md](SIGNAL_PIPELINE.md) | How conviction scores are built, regime, news sentiment, move attribution, API response shape |
| [DEVELOPMENT.md](DEVELOPMENT.md) | venv, pytest, ruff, `PYTHONPATH`, migrations, test layers (unit / fake-DB / HTTP / integration) |
| [VERIFYING.md](VERIFYING.md) | Full local verification checklist: `scripts/verify_local.sh`, DB, services, E2E pipeline |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common failures (API keys, migrations, Kafka, empty signals) |

The root [README.md](../README.md) has quick setup, trading-calendar behavior, and links here.
