#!/usr/bin/env bash
# One-shot local setup: Python deps, Docker Compose (DB + Kafka), SQL migrations.
# Usage: ./scripts/setup_local.sh
# Requires: Docker Desktop running, Python 3.11+

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example (edit API keys as needed)"
fi

echo "==> Install Python package (dev)"
pip install -q -e ".[dev]"

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running. Open Docker Desktop and run this script again." >&2
  exit 1
fi

if [[ -f .env ]]; then
  set +u
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  set -u
fi

echo "==> Docker Compose (TimescaleDB; set COMPOSE_PROFILES=kafka in .env for Redpanda)"
set +e
docker compose up -d --wait
WAIT_OK=$?
set -e
if [[ "$WAIT_OK" -ne 0 ]]; then
  docker compose up -d
  READY=0
  for _ in $(seq 1 90); do
    if docker compose exec -T timescaledb pg_isready -U signals -d signals >/dev/null 2>&1; then
      READY=1
      break
    fi
    sleep 1
  done
  if [[ "$READY" != "1" ]]; then
    echo "ERROR: Postgres did not become ready in time. Check: docker compose logs timescaledb" >&2
    exit 1
  fi
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://signals:signals@localhost:5433/signals}"
echo "==> Apply migrations (DATABASE_URL=$DATABASE_URL)"
python scripts/init_db.py

echo ""
echo "==> Setup complete."
echo "    Database:  $DATABASE_URL"
echo "    Kafka:     optional — add COMPOSE_PROFILES=kafka to .env, then docker compose up -d; use KAFKA_BOOTSTRAP_SERVERS=localhost:19092"
echo "    Next:      edit .env with your API keys, then run  make dev  or  ./scripts/dev.sh"
echo "    Tests:     ./scripts/verify_local.sh"
