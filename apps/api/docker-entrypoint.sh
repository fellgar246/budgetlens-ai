#!/bin/sh
set -eu

STORAGE_PATH="${LOCAL_STORAGE_PATH:-/var/lib/budgetlens/storage}"
mkdir -p "$STORAGE_PATH"

if [ ! -w "$STORAGE_PATH" ]; then
  echo "Storage path is not writable: $STORAGE_PATH" >&2
  exit 1
fi

case "${1:-api}" in
  migrate)
    exec alembic upgrade head
    ;;
  api)
    if [ "${RUN_MIGRATIONS_ON_START:-1}" = "1" ]; then
      alembic upgrade head
    fi
    if [ "${API_RELOAD:-0}" = "1" ]; then
      exec uvicorn budgetlens.main:app --host 0.0.0.0 --port 8000 \
        --timeout-graceful-shutdown 30 --reload --reload-dir /app/src
    fi
    exec uvicorn budgetlens.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30
    ;;
  worker)
    exec python -m budgetlens worker
    ;;
  seed|eval-ai|watchdog|retain-files|import-job)
    exec python -m budgetlens "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
