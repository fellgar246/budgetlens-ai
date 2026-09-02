#!/bin/sh
set -eu

# Generate an environment plan against the remote backend.
# Required: ENVIRONMENT=dev|prod, TF_STATE_BUCKET, AWS_REGION
# Unexpected destroys fail the guard. Do not apply a rejected plan to "try it".

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"

case "${ENVIRONMENT}" in
  dev|prod) ;;
  *)
    echo "ENVIRONMENT must be dev or prod." >&2
    exit 1
    ;;
esac

TF_ROOT="${TF_ROOT:-${ROOT}/infrastructure/terraform/environments/${ENVIRONMENT}}"
export TF_ROOT AWS_REGION="${REGION}" TF_STATE_BUCKET="${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"

echo "Caller identity:"
aws sts get-caller-identity --output json
echo "allowed_account_ids must match the recorded account (M-01)."

"${ROOT}/scripts/terraform-remote.sh"
terraform -chdir="${TF_ROOT}" plan \
  -input=false \
  -no-color \
  -lock=true \
  ${AWS_ACCOUNT_ID:+-var="aws_account_id=${AWS_ACCOUNT_ID}"} \
  ${API_IMAGE:+-var="api_image=${API_IMAGE}"} \
  -out="${TF_ROOT}/tfplan"
terraform -chdir="${TF_ROOT}" show -json "${TF_ROOT}/tfplan" > "${TF_ROOT}/tfplan.json"
python3 "${ROOT}/scripts/terraform_plan_guard.py" "${TF_ROOT}/tfplan.json" --summary "${ROOT}/var/plan-summary.md"
python3 "${ROOT}/scripts/record_cost_estimate.py" --print-sizes --environment "${ENVIRONMENT}"
python3 "${ROOT}/scripts/record_gate.py" --print-checklist M-09
echo "Review create/change/destroy, IAM wildcards, network exposure, RDS deletion, buckets,"
echo "frontend public values, and Cognito callbacks. An unexpected destroy is rejected."
echo "Do not apply this plan to experiment. Record M-09 before apply."
