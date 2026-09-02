#!/bin/sh
set -eu

# Run the one-off ECS migrate task and wait for a zero exit code.
# Required: CLUSTER, TASK_DEFINITION, SUBNETS, SECURITY_GROUPS
# Optional: IMAGE (container override), REGION, CONTAINER_NAME (default migrate)

CLUSTER="${CLUSTER:?CLUSTER is required}"
TASK_DEFINITION="${TASK_DEFINITION:?TASK_DEFINITION is required}"
SUBNETS="${SUBNETS:?SUBNETS is required}"
SECURITY_GROUPS="${SECURITY_GROUPS:?SECURITY_GROUPS is required}"
REGION="${AWS_REGION:-${REGION:-}}"
CONTAINER_NAME="${CONTAINER_NAME:-migrate}"
IMAGE="${IMAGE:-}"

if [ -z "${REGION}" ]; then
  echo "AWS_REGION or REGION is required." >&2
  exit 1
fi

if echo "${IMAGE}${TASK_DEFINITION}" | grep -Eq ':(latest|LATEST)([@"[:space:]]|$)'; then
  echo "Migration image must not use the latest tag." >&2
  exit 1
fi

OVERRIDES="{}"
if [ -n "${IMAGE}" ]; then
  OVERRIDES=$(printf '{"containerOverrides":[{"name":"%s","image":"%s"}]}' "${CONTAINER_NAME}" "${IMAGE}")
fi

NETWORK=$(printf 'awsvpcConfiguration={subnets=[%s],securityGroups=[%s],assignPublicIp=DISABLED}' "${SUBNETS}" "${SECURITY_GROUPS}")

TASK_ARN=$(aws ecs run-task \
  --region "${REGION}" \
  --cluster "${CLUSTER}" \
  --task-definition "${TASK_DEFINITION}" \
  --launch-type FARGATE \
  --count 1 \
  --network-configuration "${NETWORK}" \
  --overrides "${OVERRIDES}" \
  --query 'tasks[0].taskArn' \
  --output text)

if [ -z "${TASK_ARN}" ] || [ "${TASK_ARN}" = "None" ]; then
  echo "ecs run-task did not return a task ARN." >&2
  exit 1
fi

echo "Started migration task ${TASK_ARN}"
aws ecs wait tasks-stopped --region "${REGION}" --cluster "${CLUSTER}" --tasks "${TASK_ARN}"

EXIT_CODE=$(aws ecs describe-tasks \
  --region "${REGION}" \
  --cluster "${CLUSTER}" \
  --tasks "${TASK_ARN}" \
  --query "tasks[0].containers[?name=='${CONTAINER_NAME}'].exitCode | [0]" \
  --output text)

if [ "${EXIT_CODE}" != "0" ]; then
  echo "Migration task ${TASK_ARN} exited with ${EXIT_CODE}." >&2
  exit 1
fi

echo "Migration task ${TASK_ARN} completed successfully."
