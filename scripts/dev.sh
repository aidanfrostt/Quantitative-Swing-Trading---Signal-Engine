#!/usr/bin/env bash
# Start local stack: Docker (DB + Kafka), migrations, then Signal API (foreground).
# Usage: ./scripts/dev.sh
# Prerequisite: Docker Desktop running. Optional: .env (copy from .env.example).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "==> No .env found — copying .env.example to .env"
  echo "    Edit .env and add POLYGON_API_KEY, PERIGON_API_KEY, and SIGNAL_API_KEYS."
  cp .env.example .env
fi

if ! python -c "import signal_common" 2>/dev/null; then
  echo "==> Installing Python package (editable, dev extras)"
  pip install -q -e ".[dev]"
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running. Open Docker Desktop and try again." >&2
  exit 1
fi

echo "==> Docker Compose: TimescaleDB + Redpanda"
docker compose up -d

echo "==> Waiting for Postgres"
READY=0
for _ in $(seq 1 60); do
  if docker compose exec -T timescaledb pg_isready -U signals -d signals >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "$READY" != "1" ]]; then
  echo "ERROR: Postgres not ready. Try: docker compose logs timescaledb" >&2
  exit 1
fi

echo "==> Migrations"
export DATABASE_URL="${DATABASE_URL:-postgresql://signals:signals@localhost:5433/signals}"
python scripts/init_db.py

echo ""
echo "==> Signal API — http://127.0.0.1:8080/health  (stop with Ctrl+C)"
echo ""
export PYTHONPATH=src
exec python services/signal_api/main.py
