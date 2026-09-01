#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not available; rollback simulation skipped."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running; rollback simulation skipped."
  exit 0
fi

if ! docker image inspect budgetlens-api:local >/dev/null 2>&1; then
  echo "budgetlens-api:local is not present. Run make build first."
  exit 0
fi

docker image inspect budgetlens-api:local >/dev/null
if docker image inspect budgetlens-api:previous >/dev/null 2>&1; then
  docker tag budgetlens-api:previous budgetlens-api:local
  echo "Restored budgetlens-api:previous onto :local without a schema downgrade."
else
  docker tag budgetlens-api:local budgetlens-api:previous
  echo "Recorded budgetlens-api:local as :previous for the next rollback."
fi

if docker image inspect budgetlens-web:previous >/dev/null 2>&1; then
  docker tag budgetlens-web:previous budgetlens-web:local
fi

echo "Rollback tags are ready. Do not revert an incompatible schema."
