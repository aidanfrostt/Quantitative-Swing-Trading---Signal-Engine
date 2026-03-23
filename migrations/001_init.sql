-- Core reference data
CREATE TABLE IF NOT EXISTS symbols (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT,
    exchange TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS universe_snapshots (
    id BIGSERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    is_tradable BOOLEAN DEFAULT TRUE,
    raw JSONB,
    UNIQUE (as_of_date, symbol_id)
);

CREATE INDEX IF NOT EXISTS idx_universe_snapshots_date ON universe_snapshots(as_of_date);

CREATE TABLE IF NOT EXISTS filtered_universe (
    id BIGSERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    market_cap_usd DOUBLE PRECISION,
    adv_shares DOUBLE PRECISION,
    UNIQUE (as_of_date, symbol_id)
);

CREATE INDEX IF NOT EXISTS idx_filtered_universe_date ON filtered_universe(as_of_date);

-- Timescale: OHLCV
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS ohlcv (
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    interval TEXT NOT NULL,
    bar_time TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    vwap DOUBLE PRECISION,
    PRIMARY KEY (symbol_id, interval, bar_time)
);

SELECT create_hypertable('ohlcv', 'bar_time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_interval ON ohlcv(symbol_id, interval, bar_time DESC);

-- News (ingestion uses Perigon; provider distinguishes source per article_id)
CREATE TABLE IF NOT EXISTS news_articles (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'perigon',
    article_id TEXT NOT NULL,
    headline TEXT NOT NULL,
    body TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    author TEXT DEFAULT '',
    source TEXT DEFAULT '',
    url TEXT DEFAULT '',
    raw JSONB,
    UNIQUE (provider, article_id)
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at DESC);

CREATE TABLE IF NOT EXISTS news_article_symbols (
    news_id BIGINT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    PRIMARY KEY (news_id, symbol_id)
);

CREATE TABLE IF NOT EXISTS news_sentiment (
    news_id BIGINT PRIMARY KEY REFERENCES news_articles(id) ON DELETE CASCADE,
    score DOUBLE PRECISION NOT NULL,
    model TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news_impact_observations (
    id BIGSERIAL PRIMARY KEY,
    news_id BIGINT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    horizon_hours DOUBLE PRECISION NOT NULL,
    forward_return DOUBLE PRECISION NOT NULL,
    realized_vol DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (news_id, symbol_id, horizon_hours)
);

CREATE INDEX IF NOT EXISTS idx_impact_symbol ON news_impact_observations(symbol_id);

CREATE TABLE IF NOT EXISTS publisher_scores (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    influence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    reliability_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_noise BOOLEAN DEFAULT FALSE,
    window_days INT NOT NULL DEFAULT 90,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source, window_days)
);

CREATE TABLE IF NOT EXISTS author_scores (
    id BIGSERIAL PRIMARY KEY,
    author TEXT NOT NULL,
    influence_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    reliability_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_noise BOOLEAN DEFAULT FALSE,
    window_days INT NOT NULL DEFAULT 90,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (author, window_days)
);

-- Technical features
CREATE TABLE IF NOT EXISTS technical_features (
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    rsi_14 DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    bb_mid DOUBLE PRECISION,
    vwap_daily DOUBLE PRECISION,
    PRIMARY KEY (symbol_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS regime_snapshot (
    as_of_date DATE PRIMARY KEY,
    spy_close DOUBLE PRECISION,
    spy_ma200 DOUBLE PRECISION,
    spy_below_ma200 BOOLEAN,
    vix_close DOUBLE PRECISION,
    buy_dampening_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

-- Signals
CREATE TABLE IF NOT EXISTS signal_runs (
    id BIGSERIAL PRIMARY KEY,
    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    universe_version TEXT NOT NULL,
    horizon TEXT NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signal_runs_at ON signal_runs(run_at DESC);
