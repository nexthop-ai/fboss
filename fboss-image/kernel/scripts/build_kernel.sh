#!/usr/bin/env bash
#
# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
#
set -euo pipefail

# Internal script to build kernel RPMs inside the container.
# Args:
#   $1: Kernel version (required)
#   $2: Output directory inside container (required), e.g. /output

set -x
KERNEL_VERSION="${1:?kernel version required}"
OUT_DIR="${2:?output dir required}"

# Compute container paths
# Determine KERNEL_ROOT from the script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTAINER_DIST_DIR="$KERNEL_ROOT/dist"
CONTAINER_SPECS_DIR="$KERNEL_ROOT/specs"
CONTAINER_CONFIGS_DIR="$KERNEL_ROOT/configs"
CONTAINER_SCRIPTS_DIR="$KERNEL_ROOT/scripts"
CONTAINER_PATCHES_DIR="$KERNEL_ROOT/patches"

# Install kernel build dependencies
bash "$CONTAINER_SCRIPTS_DIR/setup_kernel_build_deps.sh"

# Use a separate build directory to avoid cluttering dist/
BUILD_DIR="$CONTAINER_DIST_DIR/build-$KERNEL_VERSION"

mkdir -p "$BUILD_DIR/SOURCES"
cd "$BUILD_DIR"

# Download kernel source, fronting the flaky public mirror (cdn.kernel.org
# 404s/rate-limits have failed the nightly Monobuild) with our internal
# static_deps mirror -- the same one getdeps uses (see cache_source.py). Flow:
#   1. If already in SOURCES, do nothing.
#   2. Else try the internal mirror; on a hit we never touch the internet.
#   3. Else let spectool fetch Source0 from upstream, then best-effort publish
#      it back to the mirror so the next build stays local.
KERNEL_TARBALL="linux-$KERNEL_VERSION.tar.xz"
# The mirror key is derived from the upstream URL, so this must match Source0
# in kernel.spec (fboss-image/kernel/specs/kernel.spec).
KERNEL_SRC_URL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$KERNEL_VERSION.tar.xz"
if [ ! -f "$BUILD_DIR/SOURCES/$KERNEL_TARBALL" ]; then
  if ! python3 "$CONTAINER_SCRIPTS_DIR/cache_source.py" fetch \
    --url "$KERNEL_SRC_URL" \
    --dest "$BUILD_DIR/SOURCES/$KERNEL_TARBALL"; then
    spectool -g -C SOURCES "$CONTAINER_SPECS_DIR/kernel.spec" \
      --define "kernel_version $KERNEL_VERSION"
    python3 "$CONTAINER_SCRIPTS_DIR/cache_source.py" prime \
      --url "$KERNEL_SRC_URL" \
      --src "$BUILD_DIR/SOURCES/$KERNEL_TARBALL" || true
  fi
fi

# Ensure FBOSS config sources are present for rpmbuild
cp "$CONTAINER_CONFIGS_DIR/fboss-reference.config" "$BUILD_DIR/SOURCES/"

# Generate version-specific local overrides from YAML
python3 "$CONTAINER_SCRIPTS_DIR/generate_config_overrides.py" \
  "$CONTAINER_CONFIGS_DIR/fboss-local-overrides.yaml" \
  "$KERNEL_VERSION" \
  "$BUILD_DIR/SOURCES/fboss-local-overrides.config"

# Copy kernel patches into SOURCES so rpmbuild can find them
if [ -d "$CONTAINER_PATCHES_DIR" ]; then
  cp "$CONTAINER_PATCHES_DIR"/*.patch "$BUILD_DIR/SOURCES/" || true
fi

rpmbuild -ba "$CONTAINER_SPECS_DIR/kernel.spec" \
  --define "_topdir $BUILD_DIR" \
  --define "_sourcedir $BUILD_DIR/SOURCES" \
  --define "container_scripts_dir $CONTAINER_SCRIPTS_DIR" \
  --define "kernel_version $KERNEL_VERSION" || {
  rv=$?
  echo "$(date) Kernel build failed with rv=$rv" >&2
  exit 1
}
chmod -R a+r "${CONTAINER_DIST_DIR}"
echo "$(date) Kernel build completed successfully"

# Copy RPMs to output directory
cp -r RPMS/* "$OUT_DIR"/ 2>/dev/null
cp -r SRPMS/* "$OUT_DIR"/ 2>/dev/null

# Create uncompressed tarball
# Compression will be handled by ImageBuilder on the host if needed
echo "Creating uncompressed tarball..."

# Create tarball with common transform rules
# shellcheck disable=SC2046
tar -cf $OUT_DIR/kernel-$KERNEL_VERSION.rpms.tar \
  --transform 's|.*/||' \
  --transform 's|^\(kernel-[^-]\+\)-.*\.\(x86_64\)\.rpm$|\1-\2.rpm|' \
  $(find RPMS -name "*.rpm")

rm -rf "${CONTAINER_DIST_DIR}/build-"*

echo 'Kernel RPM build complete!'
echo 'Output files:'
find "$OUT_DIR" \( -name '*.rpm' -o -name "*.tar" \) -type f
