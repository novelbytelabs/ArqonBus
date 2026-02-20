#!/usr/bin/env bash
set -euo pipefail

# ArqonBus rollout smoke checks (local/staging style).
# Requires:
#   ARQONBUS_VALKEY_URL
#   ARQONBUS_POSTGRES_URL

if [[ -z "${ARQONBUS_VALKEY_URL:-}" ]]; then
  echo "ERROR: ARQONBUS_VALKEY_URL must be set"
  exit 2
fi

if [[ -z "${ARQONBUS_POSTGRES_URL:-}" ]]; then
  echo "ERROR: ARQONBUS_POSTGRES_URL must be set"
  exit 2
fi

conda run -n helios-gpu-118 python scripts/manual_checks/redis_connection_check.py
conda run -n helios-gpu-118 python scripts/manual_checks/postgres_connection_check.py
conda run -n helios-gpu-118 python -m pytest -q \
  tests/integration/test_history_command_e2e.py \
  tests/integration/test_continuum_projector_postgres_e2e.py

echo "OK: rollout smoke checks passed"
