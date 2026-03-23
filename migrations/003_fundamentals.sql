CREATE TABLE IF NOT EXISTS fundamentals_snapshot (
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    pe_ratio DOUBLE PRECISION,
    price_to_book DOUBLE PRECISION,
    return_on_equity DOUBLE PRECISION,
    debt_to_equity DOUBLE PRECISION,
    revenue_growth_yoy DOUBLE PRECISION,
    fundamental_score DOUBLE PRECISION,
    raw JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol_date ON fundamentals_snapshot(symbol_id, as_of_date DESC);
