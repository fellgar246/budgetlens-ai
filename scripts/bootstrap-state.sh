#!/bin/sh
set -eu

# First-time bootstrap of remote state and optional OIDC.
# Required: CONFIRM=1
# Apply only with APPLY=1 after reviewing the plan.
# Never commits state, plan files, or secret keys.

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
CONFIRM="${CONFIRM:-}"
APPLY="${APPLY:-0}"
TF_ROOT="${TF_ROOT:-${ROOT}/infrastructure/terraform/bootstrap}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"

if [ "${CONFIRM}" != "1" ]; then
  echo "Bootstrap uses temporary administrative credentials. Confirm the account and region:"
  echo "  CONFIRM=1 AWS_REGION=${REGION} $0"
  echo "Review the plan before APPLY=1. Do not paste secret keys."
  exit 1
fi

if [ ! -d "${TF_ROOT}" ]; then
  echo "Bootstrap root is missing: ${TF_ROOT}" >&2
  exit 1
fi

echo "Caller identity (account/role/region must match the recorded gates):"
aws sts get-caller-identity --output json
echo "Region: ${REGION}"

terraform -chdir="${TF_ROOT}" fmt -check
terraform -chdir="${TF_ROOT}" init -input=false -no-color -backend=false
terraform -chdir="${TF_ROOT}" validate -no-color
terraform -chdir="${TF_ROOT}" plan -input=false -no-color -out="${TF_ROOT}/bootstrap.tfplan"

echo "Review the state bucket, versioning, encryption, public access, and CI roles."
echo "State, plan files, and backend.hcl must stay out of Git."

if [ "${APPLY}" != "1" ]; then
  echo "Bootstrap was not applied. Re-run with APPLY=1 after review."
  exit 0
fi

terraform -chdir="${TF_ROOT}" apply -input=false -no-color "${TF_ROOT}/bootstrap.tfplan"
echo "Configure the remote backend with partial config from the outputs, then verify the lockfile."
echo "Confirm CI can assume the plan role. Do not add state or plan files to Git."
