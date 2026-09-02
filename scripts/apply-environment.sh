#!/bin/sh
set -eu

# Apply a previously reviewed plan file. Never uses -auto-approve.
# Required: ENVIRONMENT=dev|prod, PLAN_FILE, CONFIRM=1
# Production also requires CONFIRM_PROD=1.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-}"
PLAN_FILE="${PLAN_FILE:-}"
CONFIRM="${CONFIRM:-}"
CONFIRM_PROD="${CONFIRM_PROD:-}"

if [ "${CONFIRM}" != "1" ]; then
  echo "Apply does not run automatically. Review the plan and record M-09 first:"
  echo "  ENVIRONMENT=dev PLAN_FILE=<tfplan> CONFIRM=1 $0"
  exit 1
fi

case "${ENVIRONMENT}" in
  dev|prod) ;;
  *)
    echo "ENVIRONMENT must be dev or prod." >&2
    exit 1
    ;;
esac

if [ "${ENVIRONMENT}" = "prod" ] && [ "${CONFIRM_PROD}" != "1" ]; then
  echo "Production apply also requires CONFIRM_PROD=1 after identity and plan review." >&2
  exit 1
fi

if [ -z "${PLAN_FILE}" ] || [ ! -f "${PLAN_FILE}" ]; then
  echo "PLAN_FILE must be a saved Terraform plan from the same review." >&2
  exit 1
fi

TF_ROOT="${TF_ROOT:-${ROOT}/infrastructure/terraform/environments/${ENVIRONMENT}}"
echo "Applying saved plan ${PLAN_FILE} for ${ENVIRONMENT}. This is never -auto-approve."
terraform -chdir="${TF_ROOT}" apply -input=false -no-color "${PLAN_FILE}"
echo "Capture non-sensitive outputs and run scripts/verify-infrastructure.sh."
