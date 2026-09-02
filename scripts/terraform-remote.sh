#!/bin/sh
set -eu

# Initialize an environment root against the remote state bucket.
# Required: TF_ROOT, TF_STATE_BUCKET, AWS_REGION

TF_ROOT="${TF_ROOT:?TF_ROOT is required}"
TF_STATE_BUCKET="${TF_STATE_BUCKET:?TF_STATE_BUCKET is required}"
AWS_REGION="${AWS_REGION:?AWS_REGION is required}"

terraform -chdir="${TF_ROOT}" init \
  -input=false \
  -no-color \
  -backend-config="bucket=${TF_STATE_BUCKET}" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="encrypt=true" \
  -backend-config="use_lockfile=true"
