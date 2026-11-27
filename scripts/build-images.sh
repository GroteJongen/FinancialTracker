#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_SHA:?Missing GITHUB_SHA}"
: "${GITHUB_REPOSITORY:?Missing GITHUB_REPOSITORY}"
: "${IMAGE_PREFIX:?Missing IMAGE_PREFIX}"
: "${APP_VERSION:?Missing APP_VERSION}"
[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ && "$APP_VERSION" == "sha-$GITHUB_SHA" ]] || {
  echo 'The release must match the checked-out commit.' >&2
  exit 1
}
source_url="${GITHUB_SERVER_URL:-https://github.com}/$GITHUB_REPOSITORY"
for component in backend frontend; do
  docker build --platform linux/amd64 \
    --label "org.opencontainers.image.source=$source_url" \
    --label "org.opencontainers.image.revision=$GITHUB_SHA" \
    --label "org.opencontainers.image.version=$APP_VERSION" \
    --tag "$IMAGE_PREFIX-$component:$APP_VERSION" "$component"
done
