#!/usr/bin/env bash
# Optional: load .env into shell for psql / terminal commands (Python loads .env via utils/db.py).
# Usage: source scripts/load_env.sh
#
# From project root:
#   cp .env.example .env   # first time only
#   source scripts/load_env.sh
#   python utils/db.py

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — run: cp .env.example .env" >&2
  return 1 2>/dev/null || exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "Loaded .env (PGHOST=${PGHOST:-localhost} PGUSER=${PGUSER:-postgres} PGDATABASE=${PGDATABASE:-ecommerce_bronze})"
