#!/bin/sh
set -eu

# Upload an immutable static artifact to the private web bucket and invalidate HTML routes.
# Required: SOURCE, WEB_BUCKET, DISTRIBUTION_ID
# Optional: REGION, RELEASE_SHA (copied under releases/<sha>/)

SOURCE="${SOURCE:?SOURCE is required}"
WEB_BUCKET="${WEB_BUCKET:?WEB_BUCKET is required}"
DISTRIBUTION_ID="${DISTRIBUTION_ID:?DISTRIBUTION_ID is required}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"
RELEASE_SHA="${RELEASE_SHA:-}"

if [ ! -d "${SOURCE}" ]; then
  echo "SOURCE must be a directory of static files." >&2
  exit 1
fi

aws s3 sync "${SOURCE}" "s3://${WEB_BUCKET}/" \
  --region "${REGION}" \
  --delete \
  --only-show-errors

if [ -n "${RELEASE_SHA}" ]; then
  aws s3 sync "${SOURCE}" "s3://${WEB_BUCKET}/releases/${RELEASE_SHA}/" \
    --region "${REGION}" \
    --only-show-errors
fi

# Hashed /_next/static assets stay cached. Invalidate documents and the app shell.
aws cloudfront create-invalidation \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/" "/index.html" "/404.html" "/*.html" \
  --output text >/dev/null

echo "Published ${SOURCE} to s3://${WEB_BUCKET} and invalidated HTML routes on ${DISTRIBUTION_ID}."
