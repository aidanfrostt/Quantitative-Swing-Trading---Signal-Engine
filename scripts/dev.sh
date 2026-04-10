#!/usr/bin/env bash
# Start local stack: Docker (DB + Kafka), migrations, then Signal API (foreground).
# Usage: ./scripts/dev.sh
# Prerequisite: Docker Desktop running. Optional: .env (copy from .env.example).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Static UI: absolute path so FastAPI always finds `web/` regardless of cwd quirks.
export WEB_ROOT="$ROOT/web"

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

# Load .env before Compose so COMPOSE_PROFILES=kafka (and DATABASE_URL) apply.
if [[ -f .env ]]; then
  set +u
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  set -u
fi

# Default: TimescaleDB only (fast, reliable). For Redpanda + Kafka topics, set in .env:
#   COMPOSE_PROFILES=kafka
echo "==> Docker Compose (TimescaleDB; add COMPOSE_PROFILES=kafka for Redpanda)"
set +e
docker compose up -d --wait
WAIT_OK=$?
set -e
if [[ "$WAIT_OK" -ne 0 ]]; then
  echo "    (retrying without --wait — upgrade Docker Compose if this keeps happening)"
  docker compose up -d
  echo "==> Waiting for Postgres"
  READY=0
  for _ in $(seq 1 90); do
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
fi

echo "==> Migrations"
export DATABASE_URL="${DATABASE_URL:-postgresql://signals:signals@localhost:5433/signals}"
python scripts/init_db.py

# Default public UI on for local dev; set ENABLE_PUBLIC_SIGNAL_UI=false in .env to disable.
export ENABLE_PUBLIC_SIGNAL_UI="${ENABLE_PUBLIC_SIGNAL_UI:-true}"

echo ""
echo "==> Signal API — http://127.0.0.1:8080/health  (stop with Ctrl+C)"
echo "    Public UI: http://127.0.0.1:8080/  (ENABLE_PUBLIC_SIGNAL_UI=${ENABLE_PUBLIC_SIGNAL_UI})"
echo ""
export PYTHONPATH=src
exec python services/signal_api/main.py
