#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if [ "${CONFIRM:-}" != "1" ]; then
  echo "This removes the local PostgreSQL volume and object storage."
  echo "It does not run automatically. Confirm explicitly:"
  echo "  make reset-local-data CONFIRM=1"
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  docker compose down --volumes
else
  echo "docker compose is not available; skipped volume removal."
fi

rm -rf var/storage
mkdir -p var/storage
echo "Local data reset. Run make dev to start a clean environment."
