#!/bin/sh
set -eu

STORAGE_PATH="${LOCAL_STORAGE_PATH:-/var/lib/budgetlens/storage}"
mkdir -p "$STORAGE_PATH"

if [ ! -w "$STORAGE_PATH" ]; then
  echo "Storage path is not writable: $STORAGE_PATH" >&2
  exit 1
fi

alembic upgrade head
exec uvicorn budgetlens.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30
