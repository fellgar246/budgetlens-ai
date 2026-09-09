#!/usr/bin/env bash
# Capture a Lighthouse baseline for the local static web app.
# Requires a running stack (make dev) and Chrome. Does not write secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${E2E_BASE_URL:-http://localhost:3000}"
OUT_DIR="${1:-$ROOT/var/lighthouse}"
mkdir -p "$OUT_DIR"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required to run Lighthouse."
  exit 1
fi

run_page() {
  local path="$1"
  local name="$2"
  echo "Lighthouse ${BASE_URL}${path} -> ${OUT_DIR}/${name}"
  npx --yes lighthouse@12.6.1 "${BASE_URL}${path}" \
    --only-categories=performance,accessibility \
    --preset=desktop \
    --chrome-flags="--headless --no-sandbox" \
    --output=html \
    --output=json \
    --output-path="${OUT_DIR}/${name}" \
    --quiet
}

run_page "/login/" "login"
run_page "/dashboard/" "dashboard"

echo "Wrote HTML and JSON reports under ${OUT_DIR}."
echo "For a signed-in summary with seed data, open the app, then rerun Lighthouse from Chrome DevTools on /dashboard/."
