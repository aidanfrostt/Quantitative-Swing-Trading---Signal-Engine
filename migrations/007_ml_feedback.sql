-- ML prediction feedback loop (offline training / evaluation; not live trading advice).

CREATE TABLE IF NOT EXISTS ml_prediction_runs (
    id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL,
    feature_schema_version TEXT NOT NULL DEFAULT 'v1',
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hyperparams JSONB,
    artifact_path TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ml_prediction_runs_version ON ml_prediction_runs(model_version);

CREATE TABLE IF NOT EXISTS ml_predictions (
    id BIGSERIAL PRIMARY KEY,
    prediction_run_id BIGINT REFERENCES ml_prediction_runs(id) ON DELETE CASCADE,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    horizon_days INT NOT NULL DEFAULT 5,
    score DOUBLE PRECISION,
    predicted_class INT,
    feature_hash TEXT,
    raw_features JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (prediction_run_id, symbol_id, as_of_date, horizon_days)
);

CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_date ON ml_predictions(symbol_id, as_of_date DESC);

CREATE TABLE IF NOT EXISTS ml_outcomes (
    prediction_id BIGINT PRIMARY KEY REFERENCES ml_predictions(id) ON DELETE CASCADE,
    realized_return DOUBLE PRECISION,
    evaluated_at TIMESTAMPTZ,
    label_big_move BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_ml_outcomes_evaluated ON ml_outcomes(evaluated_at DESC);
