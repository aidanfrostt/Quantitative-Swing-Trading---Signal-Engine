"""Environment-driven settings for all services (loads `.env` when present)."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql://signals:signals@localhost:5433/signals",
        description="asyncpg DSN: postgresql://user:pass@host:port/db",
    )

    kafka_bootstrap_servers: str = Field(
        default="localhost:19092",
        description="Redpanda/Kafka brokers; compose maps 19092 on host (see docker-compose.yml)",
    )
    kafka_consumer_group: str = Field(default="signal-generation")
    kafka_publish: bool = Field(
        default=True,
        description="If false, ingest jobs skip Kafka/Redpanda (DB inserts still run).",
    )

    polygon_api_key: str = Field(default="")
    polygon_base_url: str = Field(default="https://api.polygon.io")
    # Stocks Basic (free): 5 API calls / minute. Set higher on paid tiers, or 0 to disable client-side throttling.
    polygon_max_calls_per_minute: int = Field(default=5)

    perigon_api_key: str = Field(default="", description="Bearer token for api.perigon.io")
    perigon_articles_url: str = Field(default="https://api.perigon.io/v1/articles/all")
    perigon_page_size: int = Field(default=100)
    perigon_max_pages: int = Field(default=10)
    perigon_country: str = Field(default="us")
    perigon_language: str = Field(default="en")
    perigon_category: str = Field(
        default="Business",
        description="Optional Perigon category filter (empty string to disable)",
    )

    min_market_cap_usd: float = Field(default=300_000_000)
    min_adv_shares: float = Field(default=500_000)
    adv_lookback_days: int = Field(default=20)

    signal_api_keys: str = Field(
        default="dev-key-change-me",
        description="Comma-separated API keys for signal-api",
    )
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(
        default=8080,
        validation_alias=AliasChoices("PORT", "API_PORT"),
        description="HTTP listen port; Railway and many hosts set PORT.",
    )
    # When true, GET /public/v1/signals and GET /public/v1/sector-sentiment work without X-API-Key (same as /v1/*).
    enable_public_signal_ui: bool = Field(default=False)
    # Comma-separated browser origins for CORS (e.g. Netlify). Empty disables CORS middleware.
    cors_allowed_origins: str = Field(default="")

    finbert_model: str = Field(default="yiyanghkust/finbert-tone")
    nlp_batch_size: int = Field(default=8)

    benchmark_symbol: str = Field(default="SPY")
    vix_symbol: str = Field(default="I:VIX")
    extra_benchmark_etfs: str = Field(
        default="",
        description="Comma-separated extra tickers to ingest alongside sector ETFs (e.g. thematic proxies).",
    )
    regime_spy_below_ma_dampen: float = Field(default=0.5)
    regime_vix_threshold: float = Field(default=25.0)

    signal_buy_threshold: float = Field(default=0.65)
    # Bearish: conviction <= signal_short_threshold implies SHORT intent (strong).
    signal_short_threshold: float = Field(default=-0.65)
    # Conviction in (signal_short_threshold, signal_exit_threshold] implies reduce long / exit.
    signal_exit_threshold: float = Field(default=-0.40)
    # Blend: master = wt*tech + ws*sent + wf*fundamental (before regime on longs).
    weight_technical: float = Field(default=0.45)
    weight_sentiment: float = Field(default=0.35)
    weight_fundamental: float = Field(default=0.20)
    # If true, GET /v1/signals returns 503 when today is not an NYSE session (America/New_York calendar).
    signals_only_on_trading_days: bool = Field(default=False)
    watchlist_abs_conviction_min: float = Field(default=0.35)
    fundamentals_ingest_symbol_limit: int = Field(default=80)
    persist_signal_runs: bool = Field(default=True)

    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.signal_api_keys.split(",") if k.strip()]


def get_settings() -> Settings:
    return Settings()
