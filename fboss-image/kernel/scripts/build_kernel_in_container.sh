#!/bin/bash
#
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
set -euo pipefail

PROGNAME=$(basename "$0")

# Source kernel build environment
KERNEL_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../env" && pwd)"
source "$KERNEL_ENV_DIR/kernel_build_env.sh"

usage() {
  echo "Usage: $PROGNAME --kernel-version <VERSION> --output-dir <DIR>"
  echo ""
  echo "Build Linux kernel RPMs for FBOSS in Docker container"
  echo ""
  echo "Arguments:"
  echo "  --kernel-version <VERSION>  Kernel version to build (REQUIRED)"
  echo "  --output-dir <DIR>         Directory to store output RPMs (REQUIRED)"
  echo "  --help                     Show this help message"
  echo ""
  echo "Example:"
  echo "  $PROGNAME --kernel-version 6.11.1 --output-dir /tmp/rpms"
}

KERNEL_VERSION=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
  --kernel-version)
    KERNEL_VERSION="$2"
    shift 2
    ;;
  --output-dir)
    OUTPUT_DIR="$2"
    shift 2
    ;;
  --help)
    usage
    exit 1
    ;;
  *)
    echo "$PROGNAME: Error: Unknown option '$1'"
    usage
    exit 2
    ;;
  esac
done

if [[ -z $KERNEL_VERSION ]]; then
  echo "$PROGNAME: Error: --kernel-version is required"
  usage
  exit 3
fi

if [[ -z $OUTPUT_DIR ]]; then
  echo "$PROGNAME: Error: --output-dir is required"
  usage
  exit 4
fi

echo "Building kernel RPMs for version $KERNEL_VERSION"
echo "Output directory: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"
if ! docker version >/dev/null 2>&1; then
  echo "$PROGNAME: Error: Docker is not available or not running" >&2
  exit 5
fi

echo "Running kernel RPM build in container..."
docker run --rm \
  --volume "$PROJECT_ROOT:/src" \
  --volume "$OUTPUT_DIR:/output" \
  --env BASH_ENV=/root/.bashrc \
  "$KERNEL_DOCKER_IMAGE" \
  /bin/bash -c "cd /src/fboss-image/kernel && bash scripts/build_kernel.sh $KERNEL_VERSION /output"

echo "Kernel RPM build finished. Check $OUTPUT_DIR for RPMs."
