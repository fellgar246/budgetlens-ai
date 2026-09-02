#!/bin/sh
set -eu

# Capture non-sensitive outputs and verify VPC, RDS, buckets, compute, and edge.
# Required: ENVIRONMENT=dev|prod

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
ACCOUNT="${ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"
WORKDIR="${TMPDIR:-/tmp}/budgetlens-${ENVIRONMENT}-verify"
mkdir -p "${WORKDIR}"
OUTPUTS="${WORKDIR}/outputs.json"
FACTS="${WORKDIR}/facts.json"

tf_raw() {
  terraform -chdir="${TF_ROOT}" output -raw "$1"
}

terraform -chdir="${TF_ROOT}" output -json > "${OUTPUTS}"
SUBNETS_JSON="$(terraform -chdir="${TF_ROOT}" output -json private_subnet_ids)"
RDS_IDENTIFIER="$(tf_raw rds_identifier)"
DATA_BUCKET="$(tf_raw data_bucket_name)"
WEB_BUCKET="$(tf_raw web_bucket_name)"
RDS_PUBLIC="false"
DATA_PUBLIC="false"
WEB_PUBLIC="false"

if [ -n "${RDS_IDENTIFIER}" ]; then
  RDS_PUBLIC="$(aws rds describe-db-instances \
    --region "${REGION}" \
    --db-instance-identifier "${RDS_IDENTIFIER}" \
    --query 'DBInstances[0].PubliclyAccessible' \
    --output text 2>/dev/null || echo false)"
fi

bucket_is_public() {
  name="$1"
  if [ -z "${name}" ]; then
    echo false
    return
  fi
  aws s3api get-public-access-block --bucket "${name}" --region "${REGION}" --output json 2>/dev/null \
    | python3 -c 'import json,sys; c=json.load(sys.stdin).get("PublicAccessBlockConfiguration") or {}; print("false" if all(c.get(k) is True for k in ("BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets")) else "true")' \
    || echo true
}

DATA_PUBLIC="$(bucket_is_public "${DATA_BUCKET}")"
WEB_PUBLIC="$(bucket_is_public "${WEB_BUCKET}")"

python3 -c "
import json
from pathlib import Path
facts = {
    'vpc_id': 'present',
    'private_subnet_ids': json.loads('''${SUBNETS_JSON}'''),
    'ecs_security_group_id': '''$(tf_raw ecs_security_group_id)''',
    'ecr_repository_url': '''$(tf_raw ecr_repository_url)''',
    'ecs_cluster_name': '''$(tf_raw ecs_cluster_name)''',
    'alb_arn': 'present',
    'log_group_name': 'present',
    'cognito_user_pool_id': '''$(tf_raw cognito_user_pool_id)''',
    'cloudfront_distribution_id': '''$(tf_raw cloudfront_distribution_id)''',
    'rds_publicly_accessible': '''${RDS_PUBLIC}'''.lower() == 'true',
    'data_bucket_public': '''${DATA_PUBLIC}''' == 'true',
    'web_bucket_public': '''${WEB_PUBLIC}''' == 'true',
}
Path('''${FACTS}''').write_text(json.dumps(facts) + '\n', encoding='utf-8')
"

python3 "${ROOT}/scripts/verify_infrastructure.py" \
  --from-json "${OUTPUTS}" \
  --facts-json "${FACTS}" \
  --environment "${ENVIRONMENT}" \
  --account "${ACCOUNT}"
echo "Secret ARNs may be listed. Do not print DATABASE_URL or passwords."
