#!/usr/bin/env bash
# Build a runnable cFBOSS Docker image from source — one fboss-image invocation.
#
# What it does:
#   Runs `fboss-image build fboss-image/cfboss.json`, which drives the kiwi
#   pipeline (platform-stack + forwarding-stack + kiwi --type docker) and emits
#   fboss-image/cfboss-image.tar.xz — a `docker load`-ready archive. The container
#   image config (CMD=/sbin/init, ENV PATH/LD_LIBRARY_PATH/MALLOC_*) is baked
#   in via <containerconfig> in the kiwi XML.
#
# Usage:
#   cfboss/scripts/build_local_cfboss.sh
#
# After this script finishes, load and launch the container with:
#   docker load < fboss-image/cfboss-image.tar.xz
#   cfboss/scripts/run_cfboss.sh latest
#
# Requirements: python3, docker, jq.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

MANIFEST_DIR="$REPO_ROOT/fboss-image"
IMAGE_TAR="$MANIFEST_DIR/cfboss-image.tar.xz"
FBOSS_IMAGE="$REPO_ROOT/fboss-image/distro_cli/fboss-image"

if [ ! -x "$FBOSS_IMAGE" ]; then
  echo "Error: fboss-image CLI not found or not executable at $FBOSS_IMAGE" >&2
  exit 1
fi

echo "==> Building cfboss docker image via fboss-image (this takes a while on a cold cache)..."
(
  cd "$MANIFEST_DIR"
  "$FBOSS_IMAGE" build cfboss.json
)

if [ ! -f "$IMAGE_TAR" ]; then
  echo "Error: expected docker image tarball at $IMAGE_TAR, not found after fboss-image build" >&2
  exit 1
fi

echo
echo "==> Done. Docker image tarball: $IMAGE_TAR"
echo "Load with:    docker load < $IMAGE_TAR"
echo "Run with:     $REPO_ROOT/cfboss/scripts/run_cfboss.sh latest"
