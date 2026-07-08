#!/bin/bash
# Build a flashrom 1.7.0 RPM for EL9 during fboss-image build.

set -euo pipefail

TARBALL_URL="https://download.flashrom.org/releases/flashrom-v1.7.0.tar.xz"
VERSION="1.7.0"
NAME="flashrom"

# Use a temporary rpmbuild topdir outside the source tree so that Bazel
# doesn't try to index object files with restrictive permissions, and
# clean it up automatically on exit.
TOPDIR="$(mktemp -d /tmp/flashrom-rpmbuild.XXXXXX)"
trap 'rm -rf "${TOPDIR}"' EXIT
mkdir -p "${TOPDIR}/SOURCES"

# Download upstream source tarball
TARBALL_NAME="${NAME}-v${VERSION}.tar.xz"
curl -L "${TARBALL_URL}" -o "${TOPDIR}/SOURCES/${TARBALL_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_FILE="${SCRIPT_DIR}/rpmbuild/SPECS/${NAME}.spec"

# Install build dependencies and build the RPM
cd "${TOPDIR}"
dnf builddep -y --spec "${SPEC_FILE}"
# The container has conflicting meson installations that break both
# /usr/local/bin/meson and /usr/bin/meson. Use an isolated venv instead.
python3 -m venv venv
venv/bin/pip install meson ninja
export PATH="${TOPDIR}/venv/bin:${PATH}"

# Reproducible RPM: pin BUILDTIME + mtimes. :-1 because rpm treats 0 as unset.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1}"
rpmbuild -bb \
  --define "_topdir ${TOPDIR}" \
  --define "use_source_date_epoch_as_buildtime 1" \
  --define "clamp_mtime_to_source_date_epoch 1" \
  "${SPEC_FILE}"

# Copy the resulting RPM to /output with a deterministic name
# (no %{dist} in Release to keep the filename stable across builds).
OUTPUT_DIR="/output"
mkdir -p "${OUTPUT_DIR}"
cp "${TOPDIR}/RPMS/x86_64/flashrom-1.7.0-1.x86_64.rpm" "${OUTPUT_DIR}/"
