#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
API="$ROOT/apps/api"
if command -v corepack >/dev/null 2>&1; then
  PNPM="corepack pnpm"
else
  PNPM="pnpm"
fi
REQUIRE_INTEGRATION="${REQUIRE_INTEGRATION:-${CI:-}}"
REQUIRE_E2E="${REQUIRE_E2E:-}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens}"

postgres_ready() {
  (cd "$API" && DATABASE_URL="$DATABASE_URL" uv run python -c "
from budgetlens.adapters.db import ping_database
from budgetlens.config import reset_settings_cache
import os
os.environ.setdefault('APP_ENV', 'test')
reset_settings_cache()
raise SystemExit(0 if ping_database() else 1)
")
}

echo "==> 1. format/lint"
(cd "$API" && uv run ruff check src tests migrations)
(cd "$API" && uv run ruff format --check src tests migrations)
${PNPM} --filter web lint
${PNPM} --filter web format:check

echo "==> 2. type check"
(cd "$API" && uv run pyright)
${PNPM} --filter web typecheck

echo "==> 3. unit tests"
(cd "$API" && uv run pytest -m "not integration and not perf")
${PNPM} --filter web test

echo "==> 4. integration (PostgreSQL)"
if postgres_ready; then
  (cd "$API" && DATABASE_URL="$DATABASE_URL" uv run pytest -m integration)
else
  if [ -n "$REQUIRE_INTEGRATION" ]; then
    echo "PostgreSQL is required for integration tests." >&2
    exit 1
  fi
  echo "NOTE  integration skipped; PostgreSQL is not reachable at $DATABASE_URL"
fi

echo "==> 5. contract / OpenAPI"
(cd "$API" && uv run pytest tests/unit/test_openapi.py)

echo "==> 6. frontend build"
${PNPM} --filter web build

echo "==> 7. E2E smoke"
if [ -n "${E2E_BASE_URL:-}" ] || [ -n "$REQUIRE_E2E" ]; then
  ${PNPM} --filter web test:e2e
else
  echo "NOTE  E2E skipped; set E2E_BASE_URL or REQUIRE_E2E=1 against a running app"
fi

echo "==> 8. security / IaC"
chmod +x "$ROOT/scripts/scan.sh"
"$ROOT/scripts/scan.sh"

echo "CI stages complete."
