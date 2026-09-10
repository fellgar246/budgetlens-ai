#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
API="$ROOT/apps/api"
if command -v corepack >/dev/null 2>&1; then
  PNPM="corepack pnpm"
else
  PNPM="pnpm"
fi
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:${WEB_PORT}}"
API_BASE="${NEXT_PUBLIC_API_BASE_URL:-http://localhost:${API_PORT}}"

export APP_ENV="${APP_ENV:-local}"
export AUTH_MODE="${AUTH_MODE:-dev}"
export DATABASE_URL
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}}"
export NEXT_PUBLIC_API_BASE_URL="$API_BASE"
export NEXT_PUBLIC_APP_ENV="${NEXT_PUBLIC_APP_ENV:-local}"
export E2E_BASE_URL

wait_for() {
  url="$1"
  attempts=0
  while [ "$attempts" -lt 60 ]; do
    if python3 -c "import urllib.request; urllib.request.urlopen('$url', timeout=2)" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 1
  done
  echo "Timed out waiting for $url" >&2
  return 1
}

echo "Migrating and seeding the E2E database..."
(cd "$API" && uv run alembic upgrade head)
(cd "$API" && uv run python -m budgetlens seed)

echo "Starting the API..."
API_PID=""
WEB_PID=""
(cd "$API" && uv run uvicorn budgetlens.main:app --host 127.0.0.1 --port "$API_PORT") &
API_PID=$!
trap 'kill $API_PID $WEB_PID >/dev/null 2>&1 || true' EXIT
wait_for "http://127.0.0.1:${API_PORT}/api/v1/health/live"

echo "Building and serving the web app..."
${PNPM} --filter web build
python3 -m http.server "$WEB_PORT" --directory "$ROOT/apps/web/out" --bind 127.0.0.1 &
WEB_PID=$!
wait_for "http://127.0.0.1:${WEB_PORT}/"

echo "Running Playwright..."
${PNPM} --filter web exec playwright install chromium
E2E_BASE_URL="$E2E_BASE_URL" ${PNPM} --filter web test:e2e
echo "E2E complete."
