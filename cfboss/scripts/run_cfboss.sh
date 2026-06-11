#!/usr/bin/env bash
# Run the cFBOSS container produced by kiwi --type docker.
#
# Usage: run_cfboss.sh [version] [container-name]
#   version         Image tag (default: "latest" -- matches kiwi <containerconfig tag>).
#   container-name  Container name (default: cfboss-${USER}).
#
# Assumes the image is already loaded into docker (docker load < cfboss-image.tar.xz).
# Runs systemd as PID-1.
set -euo pipefail

VERSION="${1:-latest}"
NAME="${2:-cfboss-${USER}}"
IMAGE="cfboss:${VERSION}"

echo "Starting ${NAME} from ${IMAGE}..."
docker rm -f "${NAME}" >/dev/null 2>&1 || true
exec docker run -d \
  --name "${NAME}" \
  --privileged \
  --cgroupns=private \
  --tmpfs /run \
  --tmpfs /tmp \
  --shm-size=512m \
  --memory=4g \
  "${IMAGE}"
