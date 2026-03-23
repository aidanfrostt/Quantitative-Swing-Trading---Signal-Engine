-- Sector / benchmark ETF for move attribution (filled from Polygon ticker details).
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS sector_key TEXT;
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS sector_label TEXT;
ALTER TABLE symbols ADD COLUMN IF NOT EXISTS benchmark_etf TEXT;

CREATE INDEX IF NOT EXISTS idx_symbols_sector_key ON symbols(sector_key);

-- Daily attribution: market vs SPY beta strip, sector ETF context, peer rank.
CREATE TABLE IF NOT EXISTS attribution_snapshot (
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    ret_stock_5d DOUBLE PRECISION,
    ret_spy_5d DOUBLE PRECISION,
    ret_sector_etf_5d DOUBLE PRECISION,
    beta_spy_60d DOUBLE PRECISION,
    market_component_5d DOUBLE PRECISION,
    sector_component_5d DOUBLE PRECISION,
    residual_5d DOUBLE PRECISION,
    peer_percentile_5d DOUBLE PRECISION,
    data_quality TEXT,
    raw JSONB,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_attribution_date ON attribution_snapshot(as_of_date DESC);
