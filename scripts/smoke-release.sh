#!/bin/sh
set -eu

# Confirm the public application and API are ready after deploy.
# Required: API_HEALTH_URL
# Optional: APPLICATION_URL, VERSION_URL, EXPECTED_COMMIT, ATTEMPTS, DELAY_SECONDS

API_HEALTH_URL="${API_HEALTH_URL:?API_HEALTH_URL is required}"
APPLICATION_URL="${APPLICATION_URL:-}"
VERSION_URL="${VERSION_URL:-}"
EXPECTED_COMMIT="${EXPECTED_COMMIT:-}"
ATTEMPTS="${ATTEMPTS:-20}"
DELAY_SECONDS="${DELAY_SECONDS:-15}"

if [ -z "${VERSION_URL}" ] && [ -n "${API_HEALTH_URL}" ]; then
  VERSION_URL=$(printf '%s' "${API_HEALTH_URL}" | sed 's#/health/ready/*$#/version#')
fi

fetch() {
  url="$1"
  curl -fsS --max-time 20 "${url}"
}

attempt=1
while [ "${attempt}" -le "${ATTEMPTS}" ]; do
  if body=$(fetch "${API_HEALTH_URL}") && echo "${body}" | grep -Eq '"status": ?"ready"'; then
    echo "Ready: ${API_HEALTH_URL}"
    break
  fi
  if [ "${attempt}" -eq "${ATTEMPTS}" ]; then
    echo "Readiness did not succeed after ${ATTEMPTS} attempts: ${API_HEALTH_URL}" >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep "${DELAY_SECONDS}"
done

if [ -n "${APPLICATION_URL}" ]; then
  fetch "${APPLICATION_URL}" >/dev/null
  echo "Application URL responded: ${APPLICATION_URL}"
fi

if [ -n "${VERSION_URL}" ]; then
  version=$(fetch "${VERSION_URL}")
  echo "${version}"
  if [ -n "${EXPECTED_COMMIT}" ]; then
    echo "${version}" | grep -F "${EXPECTED_COMMIT}" >/dev/null
    echo "Version commit matches ${EXPECTED_COMMIT}."
  fi
fi
