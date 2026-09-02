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

# Hashed assets keep a long cache. HTML and manifests stay revalidated.
aws s3 sync "${SOURCE}" "s3://${WEB_BUCKET}/" \
  --region "${REGION}" \
  --delete \
  --exclude "*" \
  --include "_next/static/*" \
  --cache-control "public,max-age=31536000,immutable" \
  --only-show-errors
aws s3 sync "${SOURCE}" "s3://${WEB_BUCKET}/" \
  --region "${REGION}" \
  --exclude "_next/static/*" \
  --cache-control "public,max-age=0,must-revalidate" \
  --only-show-errors

if [ -n "${RELEASE_SHA}" ]; then
  aws s3 sync "${SOURCE}" "s3://${WEB_BUCKET}/releases/${RELEASE_SHA}/" \
    --region "${REGION}" \
    --only-show-errors
fi

# Invalidate HTML and manifests only. Versioned hashed assets do not need a blanket invalidation.
aws cloudfront create-invalidation \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/" "/index.html" "/404.html" "/*.html" "/manifest.json" "/site.webmanifest" \
  --output text >/dev/null

echo "Published ${SOURCE} to s3://${WEB_BUCKET} with cache headers and invalidated HTML/manifest routes on ${DISTRIBUTION_ID}."
