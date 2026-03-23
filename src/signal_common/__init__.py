"""
Shared library for the signal-generation platform.

All services under ``services/`` add ``PYTHONPATH=src`` (or install the package editable)
and import from ``signal_common``. Major areas:

- **config** — environment-driven settings (Pydantic).
- **db** — asyncpg pool, ordered SQL migrations in ``migrations/``, ticker helpers.
- **schemas** — API and Kafka payload models.
- **polygon_client** / **perigon_client** — external HTTP integrations.
- **signal_logic** — pure conviction blending, thesis text, fundamental parsing helpers.
- **indicators** — technical indicators used by ``technical_engine``.
- **market_calendar** / **job_guards** — NYSE session checks for batch jobs.
- **sector_etfs** / **attribution_math** — sector ETF mapping and move-attribution math.

See the ``docs/`` directory at the repository root for architecture and data model write-ups.
"""

__version__ = "0.1.0"
