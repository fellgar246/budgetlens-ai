#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
API_BASE="http://127.0.0.1:${API_PORT}"
WEB_BASE="http://127.0.0.1:${WEB_PORT}"

check_url() {
  url="$1"
  python3 -c "import urllib.request; urllib.request.urlopen('$url', timeout=3)" >/dev/null 2>&1
}

if ! check_url "${API_BASE}/api/v1/health/live"; then
  echo "API liveness is not reachable at ${API_BASE}. Start the stack with make bootstrap && make dev." >&2
  exit 1
fi

if ! check_url "${API_BASE}/api/v1/health/ready"; then
  echo "API readiness failed. PostgreSQL is not healthy or migrations are pending." >&2
  exit 1
fi

if ! check_url "${WEB_BASE}/"; then
  echo "Web is not reachable at ${WEB_BASE}." >&2
  exit 1
fi

if ! check_url "${WEB_BASE}/estado/"; then
  echo "Status screen is not reachable at ${WEB_BASE}/estado/." >&2
  exit 1
fi

echo "Local stack is healthy: web ${WEB_BASE}, API ${API_BASE}, readiness 200."
