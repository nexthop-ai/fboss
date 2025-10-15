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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../env/kernel_build_env.sh"

KERNEL_VERSIONS=("${FBOSS_KERNEL_VERSIONS[@]}")

usage() {
    echo "Usage: $PROGNAME [--output-dir <DIR>] [--versions <V1[,V2,...]>]"
    echo ""
    echo "Build Linux kernel RPMs for all FBOSS-supported versions in parallel"
    echo ""
    echo "Options:"
    echo "  --output-dir <DIR>         Base directory to store output RPMs (default: \$KERNEL_DIST_DIR)"
    echo "  --versions <V1[,V2,...]>   Comma-separated list of kernel versions (default: ${FBOSS_KERNEL_VERSIONS[*]})"
    echo "  --help                     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $PROGNAME                                  # Build all versions in parallel"
    echo "  $PROGNAME --output-dir /tmp/kernels        # Custom output directory"
    echo "  $PROGNAME --versions ${FBOSS_KERNEL_VERSIONS[0]}                # Build only ${FBOSS_KERNEL_VERSIONS[0]}"
    echo "  $PROGNAME --versions ${FBOSS_KERNEL_VERSIONS[0]},${FBOSS_KERNEL_VERSIONS[1]}  # Build a specific set"
}

OUTPUT_DIR="$KERNEL_DIST_DIR"

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --versions)
            IFS=',' read -ra KERNEL_VERSIONS <<< "$2"
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

echo "Building kernel RPMs for : ${#KERNEL_VERSIONS[@]} versions"

BUILD_SCRIPT="$KERNEL_BUILD_SCRIPT"

if [[ ! -f "$BUILD_SCRIPT" ]]; then
    echo "$PROGNAME: Error: Build script not found: $BUILD_SCRIPT"
    exit 3
fi

echo "Checking for fboss_builder Docker image..."
if ! docker image inspect "$KERNEL_DOCKER_IMAGE" >/dev/null 2>&1; then
    echo "Building $KERNEL_DOCKER_IMAGE Docker image..."
    if ! "$PROJECT_ROOT/fboss/oss/scripts/build_docker.sh"; then
        echo "$PROGNAME: Error: Failed to build $KERNEL_DOCKER_IMAGE" >&2
        exit 5
    fi
fi

declare -a BUILD_PIDS=()
declare -A PID2LOG

echo "Build output directory: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

for VERSION in "${KERNEL_VERSIONS[@]}"; do
    VERSION_OUTPUT_DIR="$OUTPUT_DIR/$VERSION"
    mkdir -p "$VERSION_OUTPUT_DIR"
    LOG_FILE="$VERSION_OUTPUT_DIR/build.log"
    echo "Starting build for kernel $VERSION -> $VERSION_OUTPUT_DIR"

    "$BUILD_SCRIPT" \
        --kernel-version "$VERSION" \
        --output-dir "$VERSION_OUTPUT_DIR" >"$LOG_FILE" 2>&1 &

    pid=$!
    BUILD_PIDS+=("$pid")
    PID2LOG["$pid"]="$LOG_FILE"
done

declare -a FAILED_BUILDS=()

for i in "${!BUILD_PIDS[@]}"; do
    pid=${BUILD_PIDS[$i]}
    version=${KERNEL_VERSIONS[$i]}
    log="${PID2LOG[$pid]}"
    if wait "$pid"; then
        echo "Kernel $version build completed successfully"
    else
        rc=$?
        echo "Kernel $version build failed (exit $rc)"
        FAILED_BUILDS+=("$version")
        echo "----- Begin build log for $version -----"
        cat "$log"
        echo "----- End build log for $version -----"
    fi
done

echo "========================================="
echo "Build Summary"
echo "========================================="
echo "Total versions: ${#KERNEL_VERSIONS[@]}"
echo "Successful builds: $((${#KERNEL_VERSIONS[@]} - ${#FAILED_BUILDS[@]}))"
echo "Failed builds: ${#FAILED_BUILDS[@]}"

if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
    echo "Failed versions: ${FAILED_BUILDS[*]}"
    echo "$PROGNAME: Some builds failed. Check logs above."
    exit 4
fi

echo "All kernel builds completed successfully!"

