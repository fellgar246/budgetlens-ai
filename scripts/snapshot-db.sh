#!/bin/sh
set -eu

# Create an RDS snapshot before a high-risk change.
# Required: DB_IDENTIFIER
# Optional: SNAPSHOT_ID, REGION
# Does not print credentials.

DB_IDENTIFIER="${DB_IDENTIFIER:?DB_IDENTIFIER is required}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"
STAMP="$(date -u +%Y%m%d%H%M%S)"
SNAPSHOT_ID="${SNAPSHOT_ID:-budgetlens-${DB_IDENTIFIER}-${STAMP}}"

if echo "${SNAPSHOT_ID}" | grep -Eq '[^A-Za-z0-9-]'; then
  echo "SNAPSHOT_ID must be alphanumeric or hyphen." >&2
  exit 1
fi

aws rds create-db-snapshot \
  --region "${REGION}" \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --query 'DBSnapshot.DBSnapshotIdentifier' \
  --output text

aws rds wait db-snapshot-available \
  --region "${REGION}" \
  --db-snapshot-identifier "${SNAPSHOT_ID}"

echo "Snapshot ready: ${SNAPSHOT_ID}"
