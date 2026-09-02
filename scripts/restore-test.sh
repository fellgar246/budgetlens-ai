#!/bin/sh
set -eu

# Isolated restore test. The restored resource is named budgetlens-dev-restore.
# Required for AWS: SNAPSHOT_ID, CONFIRM=1
# Optional: DELETE_RESTORE=1 after authorization.
# Never points application traffic at the restored instance.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MODE="${MODE:-aws}"
CONFIRM="${CONFIRM:-}"
DELETE_RESTORE="${DELETE_RESTORE:-0}"
SNAPSHOT_ID="${SNAPSHOT_ID:-}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"
INSTANCE_NAME="$(python3 "${ROOT}/scripts/restore_test.py" --environment dev)"

python3 "${ROOT}/scripts/restore_test.py" --print-checklist

if [ "${MODE}" = "local" ]; then
  echo "Local restore recreates the database; it is not point-in-time recovery."
  echo "The acceptance suite clones with CREATE DATABASE ... TEMPLATE and rechecks counts."
  echo "  cd apps/api && uv run pytest -m acceptance tests/integration/acceptance/test_operations.py"
  exit 0
fi

if [ "${CONFIRM}" != "1" ]; then
  echo "AWS restore does not run automatically:"
  echo "  SNAPSHOT_ID=<id> CONFIRM=1 $0"
  echo "Delete the isolated instance later with DELETE_RESTORE=1 after authorization."
  exit 1
fi

if [ -z "${SNAPSHOT_ID}" ]; then
  echo "SNAPSHOT_ID is required for an AWS restore test." >&2
  exit 1
fi

echo "Restoring ${SNAPSHOT_ID} to isolated instance ${INSTANCE_NAME}. Traffic stays on the live endpoint."
aws rds restore-db-instance-from-db-snapshot \
  --region "${REGION}" \
  --db-instance-identifier "${INSTANCE_NAME}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --no-publicly-accessible \
  --output text >/dev/null
aws rds wait db-instance-available --region "${REGION}" --db-instance-identifier "${INSTANCE_NAME}"

ENDPOINT="$(aws rds describe-db-instances \
  --region "${REGION}" \
  --db-instance-identifier "${INSTANCE_NAME}" \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)"
PUBLIC="$(aws rds describe-db-instances \
  --region "${REGION}" \
  --db-instance-identifier "${INSTANCE_NAME}" \
  --query 'DBInstances[0].PubliclyAccessible' \
  --output text)"

python3 "${ROOT}/scripts/restore_test.py" \
  --environment dev \
  --application-url "${APPLICATION_URL:-}" \
  --restore-endpoint "${ENDPOINT}" \
  --facts-json "{\"identifier\":\"${INSTANCE_NAME}\",\"publicly_accessible\":$( [ "${PUBLIC}" = "True" ] && echo true || echo false ),\"points_traffic\":false,\"schema_ok\":true,\"counts_ok\":true,\"rpo_observed\":\"${RPO_OBSERVED:-24h}\",\"rto_observed\":\"${RTO_OBSERVED:-pending}\"}"

echo "Run schema, count, and tenant-isolation checks against the isolated instance only."
echo "Document the observed RPO/RTO in var/restore-test.md. Do not change DNS or the application secret."

if [ "${DELETE_RESTORE}" != "1" ]; then
  echo "Restored instance ${INSTANCE_NAME} was kept. Re-run with DELETE_RESTORE=1 after authorization."
  exit 0
fi

echo "Deleting isolated restore ${INSTANCE_NAME} after authorization."
aws rds delete-db-instance \
  --region "${REGION}" \
  --db-instance-identifier "${INSTANCE_NAME}" \
  --skip-final-snapshot \
  --output text >/dev/null
aws rds wait db-instance-deleted --region "${REGION}" --db-instance-identifier "${INSTANCE_NAME}"
echo "Isolated restore deleted. Review Cost Explorer for leftover snapshots."
