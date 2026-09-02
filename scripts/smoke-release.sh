#!/bin/sh
set -eu

# Confirm the public application and API are ready after deploy.
# Required: API_HEALTH_URL
# Optional: APPLICATION_URL, VERSION_URL, EXPECTED_COMMIT, ATTEMPTS, DELAY_SECONDS

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
API_HEALTH_URL="${API_HEALTH_URL:?API_HEALTH_URL is required}"

python3 "${ROOT}/smoke_release.py" \
  --print-checklist \
  --api-health-url "${API_HEALTH_URL}" \
  --application-url "${APPLICATION_URL:-}" \
  --version-url "${VERSION_URL:-}" \
  --expected-commit "${EXPECTED_COMMIT:-}" \
  --attempts "${ATTEMPTS:-20}" \
  --delay-seconds "${DELAY_SECONDS:-15}"
