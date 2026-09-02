#!/bin/sh
set -eu

# Restore the previous API task definition and/or previous web artifact.
# Never downgrades the database. Schema-incompatible images must not be passed as PREVIOUS_TASK_DEFINITION.
# Required: one of PREVIOUS_TASK_DEFINITION or PREVIOUS_WEB_SOURCE
# Optional: CLUSTER, SERVICE, REGION, WEB_BUCKET, DISTRIBUTION_ID

REGION="${AWS_REGION:-${REGION:-us-east-1}}"
PREVIOUS_TASK_DEFINITION="${PREVIOUS_TASK_DEFINITION:-}"
PREVIOUS_WEB_SOURCE="${PREVIOUS_WEB_SOURCE:-}"
CLUSTER="${CLUSTER:-}"
SERVICE="${SERVICE:-}"
WEB_BUCKET="${WEB_BUCKET:-}"
DISTRIBUTION_ID="${DISTRIBUTION_ID:-}"

if [ -z "${PREVIOUS_TASK_DEFINITION}" ] && [ -z "${PREVIOUS_WEB_SOURCE}" ]; then
  echo "Set PREVIOUS_TASK_DEFINITION and/or PREVIOUS_WEB_SOURCE." >&2
  exit 1
fi

if echo "${PREVIOUS_TASK_DEFINITION}" | grep -Eq ':(latest|LATEST)([@"[:space:]]|$)'; then
  echo "Rollback target must not use the latest tag." >&2
  exit 1
fi

if [ -n "${PREVIOUS_TASK_DEFINITION}" ]; then
  if [ -z "${CLUSTER}" ] || [ -z "${SERVICE}" ]; then
    echo "CLUSTER and SERVICE are required to roll back the API." >&2
    exit 1
  fi
  aws ecs update-service \
    --region "${REGION}" \
    --cluster "${CLUSTER}" \
    --service "${SERVICE}" \
    --task-definition "${PREVIOUS_TASK_DEFINITION}" \
    --force-new-deployment \
    --output text >/dev/null
  echo "API service ${SERVICE} is rolling back to ${PREVIOUS_TASK_DEFINITION}."
fi

if [ -n "${PREVIOUS_WEB_SOURCE}" ]; then
  if [ -z "${WEB_BUCKET}" ] || [ -z "${DISTRIBUTION_ID}" ]; then
    echo "WEB_BUCKET and DISTRIBUTION_ID are required to roll back the web artifact." >&2
    exit 1
  fi
  SOURCE="${PREVIOUS_WEB_SOURCE}"
  WEB_BUCKET="${WEB_BUCKET}"
  DISTRIBUTION_ID="${DISTRIBUTION_ID}"
  AWS_REGION="${REGION}"
  export SOURCE WEB_BUCKET DISTRIBUTION_ID AWS_REGION
  ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
  "${ROOT}/deploy-web.sh"
  echo "Restored previous web artifact without a schema downgrade."
fi
