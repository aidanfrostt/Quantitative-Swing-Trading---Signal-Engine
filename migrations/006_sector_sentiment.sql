-- Global / regional extension points (populated when feeds support non-US universes).
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS country TEXT;
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS market_currency TEXT;

CREATE INDEX IF NOT EXISTS idx_symbols_region ON symbols(region);

-- Daily sector-level news sentiment vs benchmark ETF performance (US v1).
CREATE TABLE IF NOT EXISTS sector_sentiment_snapshot (
    as_of_date DATE NOT NULL,
    sector_key TEXT NOT NULL,
    benchmark_etf TEXT,
    article_count INT NOT NULL DEFAULT 0,
    weighted_sentiment_avg DOUBLE PRECISION,
    sentiment_std DOUBLE PRECISION,
    etf_return_5d DOUBLE PRECISION,
    etf_return_20d DOUBLE PRECISION,
    sentiment_z_cross_sector DOUBLE PRECISION,
    performance_sentiment_spread DOUBLE PRECISION,
    divergence_flag BOOLEAN,
    raw JSONB,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (as_of_date, sector_key)
);

CREATE INDEX IF NOT EXISTS idx_sector_sentiment_date ON sector_sentiment_snapshot(as_of_date DESC);
