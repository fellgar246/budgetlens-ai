#!/bin/sh
set -eu

STORAGE_PATH="${LOCAL_STORAGE_PATH:-/var/lib/budgetlens/storage}"
mkdir -p "$STORAGE_PATH"

alembic upgrade head
exec uvicorn budgetlens.main:app --host 0.0.0.0 --port 8000
