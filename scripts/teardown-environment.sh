#!/bin/sh
set -eu

# Safe teardown of an environment root. Never destroys bootstrap state.
# Required: ENVIRONMENT=dev|prod, CONFIRM=1
# Production also requires CONFIRM_PROD=1
# Optional: SNAPSHOT=1, DISABLE_DELETION_PROTECTION=1, EMPTY_BUCKET=<exact name>,
#           APPLY_DESTROY=1, TF_STATE_BUCKET, AWS_REGION

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-}"
CONFIRM="${CONFIRM:-}"
CONFIRM_PROD="${CONFIRM_PROD:-}"
SNAPSHOT="${SNAPSHOT:-0}"
DISABLE_DELETION_PROTECTION="${DISABLE_DELETION_PROTECTION:-0}"
EMPTY_BUCKET="${EMPTY_BUCKET:-}"
APPLY_DESTROY="${APPLY_DESTROY:-0}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"

if [ "${CONFIRM}" != "1" ]; then
  echo "Teardown does not run automatically. Confirm the environment:"
  echo "  ENVIRONMENT=dev CONFIRM=1 $0"
  echo "Production also requires CONFIRM_PROD=1. Review the destroy plan before APPLY_DESTROY=1."
  exit 1
fi

case "${ENVIRONMENT}" in
  dev|prod) ;;
  bootstrap)
    echo "This script does not destroy bootstrap or the Terraform state bucket." >&2
    echo "State retention is a separate, explicit decision. See docs/OPERATIONS.md#teardown." >&2
    exit 1
    ;;
  *)
    echo "ENVIRONMENT must be dev or prod." >&2
    exit 1
    ;;
esac

if [ "${ENVIRONMENT}" = "prod" ] && [ "${CONFIRM_PROD}" != "1" ]; then
  echo "Production teardown also requires CONFIRM_PROD=1 after identity review." >&2
  exit 1
fi

TF_ROOT="${TF_ROOT:-${ROOT}/infrastructure/terraform/environments/${ENVIRONMENT}}"
export TF_ROOT AWS_REGION="${REGION}"

if [ ! -d "${TF_ROOT}/.terraform" ]; then
  if [ -z "${TF_STATE_BUCKET:-}" ]; then
    echo "TF_STATE_BUCKET is required to initialize the remote backend." >&2
    exit 1
  fi
  "${ROOT}/scripts/terraform-remote.sh"
fi

tf_output() {
  terraform -chdir="${TF_ROOT}" output -raw "$1"
}

OUTPUT_ENV="$(tf_output environment)"
RECORDED_ACCOUNT="$(tf_output aws_account_id)"
RDS_IDENTIFIER="$(tf_output rds_identifier)"
DATA_BUCKET="$(tf_output data_bucket_name)"
WEB_BUCKET="$(tf_output web_bucket_name)"
CALLER_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
CALLER_ARN="$(aws sts get-caller-identity --query Arn --output text)"

echo "Caller identity: ${CALLER_ARN}"
echo "Caller account:  ${CALLER_ACCOUNT}"
echo "Recorded account:${RECORDED_ACCOUNT}"
echo "Output environment: ${OUTPUT_ENV}"
echo "Requested environment: ${ENVIRONMENT}"
echo "RDS identifier: ${RDS_IDENTIFIER}"
echo "Data bucket: ${DATA_BUCKET}"
echo "Web bucket: ${WEB_BUCKET}"
echo "A budget is an alert, not a hard cap. Teardown does not delete Terraform state."

if [ "${OUTPUT_ENV}" != "${ENVIRONMENT}" ]; then
  echo "Terraform output environment (${OUTPUT_ENV}) does not match ENVIRONMENT=${ENVIRONMENT}." >&2
  exit 1
fi

if [ -z "${RECORDED_ACCOUNT}" ]; then
  echo "aws_account_id is empty. Record the account in terraform.tfvars before teardown." >&2
  exit 1
fi

if [ "${RECORDED_ACCOUNT}" != "${CALLER_ACCOUNT}" ]; then
  echo "Caller account ${CALLER_ACCOUNT} does not match recorded ${RECORDED_ACCOUNT}." >&2
  exit 1
fi

echo "Export any required audit or demo data before continuing. This script does not dump tenant data."

if [ "${SNAPSHOT}" = "1" ]; then
  DB_IDENTIFIER="${RDS_IDENTIFIER}" AWS_REGION="${REGION}" "${ROOT}/scripts/snapshot-db.sh"
fi

if [ "${DISABLE_DELETION_PROTECTION}" = "1" ]; then
  echo "Disabling RDS deletion protection on ${RDS_IDENTIFIER} after explicit review."
  aws rds modify-db-instance \
    --region "${REGION}" \
    --db-instance-identifier "${RDS_IDENTIFIER}" \
    --no-deletion-protection \
    --apply-immediately >/dev/null
else
  PROTECTED="$(tf_output deletion_protection)"
  if [ "${PROTECTED}" = "true" ]; then
    echo "Deletion protection is enabled. Re-run with DISABLE_DELETION_PROTECTION=1 after review." >&2
    exit 1
  fi
fi

if [ -n "${EMPTY_BUCKET}" ]; then
  case "${EMPTY_BUCKET}" in
    "${DATA_BUCKET}"|"${WEB_BUCKET}") ;;
    *)
      echo "EMPTY_BUCKET must be the exact data or web bucket name from Terraform outputs." >&2
      echo "Refusing to empty ${EMPTY_BUCKET}." >&2
      exit 1
      ;;
  esac
  if echo "${EMPTY_BUCKET}" | grep -Eq 'tfstate|budgetlens-tfstate'; then
    echo "Refusing to empty a Terraform state bucket." >&2
    exit 1
  fi
  echo "Emptying authorized bucket ${EMPTY_BUCKET}."
  aws s3 rm "s3://${EMPTY_BUCKET}" --region "${REGION}" --recursive
fi

terraform -chdir="${TF_ROOT}" plan -destroy -input=false -no-color -out="${TF_ROOT}/destroy.tfplan"
echo "Destroy plan written to ${TF_ROOT}/destroy.tfplan. Review resources before apply."

if [ "${APPLY_DESTROY}" != "1" ]; then
  echo "Destroy was not applied. Re-run with APPLY_DESTROY=1 after reviewing the plan."
  echo "Keep or delete remote state only after that review; this script never deletes the state bucket."
  exit 0
fi

if [ "${ENVIRONMENT}" = "prod" ]; then
  echo "Production destroy uses the saved plan file and is never -auto-approve."
fi

terraform -chdir="${TF_ROOT}" apply -input=false -no-color "${TF_ROOT}/destroy.tfplan"
echo "Environment ${ENVIRONMENT} destroy applied. State remains in the bootstrap bucket until a human deletes it."
