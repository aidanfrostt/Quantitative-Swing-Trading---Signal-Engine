#!/usr/bin/env bash
# Run batch jobs in first-time order (see docs/SERVICES.md). Requires Docker Postgres, .env with keys.
# Usage: ./scripts/run_full_pipeline.sh
# Optional: KAFKA_PUBLISH=false if Redpanda is not running (OHLCV/news still go to DB).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: Copy .env.example to .env and set POLYGON_API_KEY, PERIGON_API_KEY." >&2
  exit 1
fi

set +u
set -a
# shellcheck disable=SC1091
source .env
set +a
set -u

export PYTHONPATH=src
export KAFKA_PUBLISH="${KAFKA_PUBLISH:-true}"

if ! python -c "import signal_common" 2>/dev/null; then
  pip install -q -e ".[dev]"
fi

run_job() {
  local name="$1"
  echo ""
  echo "========== ${name} =========="
  python "services/${name}/main.py"
}

run_job universe_cron
run_job price_ingest
run_job technical_engine
run_job news_ingest

echo ""
echo "========== nlp_worker (ML extra; may download model on first run) =========="
pip install -q -e ".[ml]" 2>/dev/null || pip install -e ".[ml]"
python services/nlp_worker/main.py

run_job fundamentals_ingest
run_job attribution_job
run_job sector_sentiment_job

echo ""
echo "========== Pipeline finished =========="
echo "Restart or refresh the signal API UI; GET /public/v1/signals should show data if Polygon/Perigon limits allow."
