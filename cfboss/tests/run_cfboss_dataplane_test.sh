#!/usr/bin/env bash
# Bazel sh_test wrapper for the cFBOSS kernel-dataplane validation.
#
# Runs inside the Monobuild's `bazel test //fboss/...` sweep, against the very
# cfboss-image.tar.xz produced earlier in the same build (declared as a data
# dependency).
#
# Steps: load the image, boot the systemd container, run the 7 dataplane
# checks, tear the container down on exit.
set -euo pipefail

# Runfiles-relative paths (sh_test runs from the runfiles root; the //fboss
# package materializes under fboss/, matching the device_integration_test idiom).
IMAGE_TAR="fboss/cfboss-image.tar.xz"
RUN_SCRIPT="fboss/cfboss/scripts/run_cfboss.sh"
VALIDATE_SCRIPT="fboss/cfboss/tests/validate_dataplane.sh"

CTR="cfboss-monobuild-$$"
cleanup() { docker rm -f "$CTR" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "== cfboss_dataplane_test: loading image from ${IMAGE_TAR} =="
docker load -i "${IMAGE_TAR}"

echo "== cfboss_dataplane_test: booting container ${CTR} =="
"${RUN_SCRIPT}" latest "${CTR}"

echo "== cfboss_dataplane_test: validating dataplane =="
"${VALIDATE_SCRIPT}" "${CTR}"
