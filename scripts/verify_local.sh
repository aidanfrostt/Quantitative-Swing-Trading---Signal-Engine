#!/usr/bin/env bash
# Local verification: ruff, pytest, optional ML and DB integration.
# Usage:
#   ./scripts/verify_local.sh
#   VERIFY_ML=1 ./scripts/verify_local.sh          # also run tests requiring torch
#   RUN_INTEGRATION_TESTS=1 DATABASE_URL=... ./scripts/verify_local.sh
#   VERIFY_RESEARCH=1 ./scripts/verify_local.sh   # correlation_scan --demo
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Install (dev)"
pip install -q -e ".[dev]"

echo "==> Ruff"
ruff check src services tests

echo "==> Pytest (unit + HTTP + fake DB)"
pytest -q

if [[ "${VERIFY_ML:-0}" == "1" ]]; then
  echo "==> Install ML extras + PyTorch tests"
  pip install -q -e ".[ml]"
  pytest -q tests/test_ml_model_forward.py
fi

if [[ "${RUN_INTEGRATION_TESTS:-0}" == "1" ]]; then
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "RUN_INTEGRATION_TESTS=1 requires DATABASE_URL" >&2
    exit 1
  fi
  echo "==> Integration tests (PostgreSQL)"
  pytest -v tests/test_integration_db.py
fi

if [[ "${VERIFY_RESEARCH:-0}" == "1" ]]; then
  echo "==> Research script smoke (demo)"
  python scripts/research/correlation_scan.py --demo | head -20
fi

echo "==> verify_local: OK"
