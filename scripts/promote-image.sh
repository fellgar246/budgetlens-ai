#!/bin/sh
set -eu

# Copy an immutable image digest from a source ECR repository to a destination repository.
# Required: SOURCE_IMAGE (repo@sha256:...), DEST_REPOSITORY (registry/name)
# Optional: DEST_TAGS (space-separated, never latest), REGION

SOURCE_IMAGE="${SOURCE_IMAGE:?SOURCE_IMAGE is required}"
DEST_REPOSITORY="${DEST_REPOSITORY:?DEST_REPOSITORY is required}"
DEST_TAGS="${DEST_TAGS:-}"
REGION="${AWS_REGION:-${REGION:-us-east-1}}"

case "${SOURCE_IMAGE}" in
  *@sha256:*) ;;
  *)
    echo "SOURCE_IMAGE must be a digest URI (repository@sha256:...)." >&2
    exit 1
    ;;
esac

for tag in ${DEST_TAGS}; do
  if [ "${tag}" = "latest" ] || [ "${tag}" = "LATEST" ]; then
    echo "Refusing to promote the latest tag." >&2
    exit 1
  fi
done

DEST_URI="${DEST_REPOSITORY}@${SOURCE_IMAGE#*@}"
docker pull "${SOURCE_IMAGE}"
docker tag "${SOURCE_IMAGE}" "${DEST_URI}"
docker push "${DEST_URI}"

for tag in ${DEST_TAGS}; do
  docker tag "${SOURCE_IMAGE}" "${DEST_REPOSITORY}:${tag}"
  docker push "${DEST_REPOSITORY}:${tag}"
done

echo "${DEST_URI}"
