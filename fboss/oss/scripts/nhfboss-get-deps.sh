#!/bin/bash

# Run inside the build container
# Fetches and builds only dependencies, not FBOSS itself -- allows one-time
# dependency setup for multiple FBOSS builds during development. Takes 30
# minutes initially without a primed cache, and less than 10 minutes subsequent
# runs.
# REQUIRED: If building against the real SAI, run build-helper before each
# build since it stages the SAI files for an HTTP server that the wrapped
# getdeps script can understand.
#
# Caching: when GETDEPS_CACHE_URL is set, each dep is fetched from an HTTP
# cache (or built and uploaded if not cached yet).  Set GETDEPS_CACHE_UPLOAD=1
# to allow uploads (CI only -- dev machines should not pollute the shared cache).
# NHFBOSS_COMPILE_JOBS and NHFBOSS_LINK_JOBS pin the job counts so that cache
# keys remain stable across fresh VMs of the same flavor.
#
# IMPORTANT: do NOT source fboss-build.env here -- that file runs
# _fboss_ensure_sai which would re-create the sai_impl manifest during the
# fake-SAI get-deps pass after the workflow has deliberately reverted it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=fboss/oss/scripts/nhfboss-common.sh
source "$SCRIPT_DIR/nhfboss-common.sh"

set -e
cd /var/FBOSS/fboss

time nice -n 10 ./fboss/oss/scripts/run-getdeps.py install-system-deps --num-jobs $num_jobs --recursive $common_options

# When a remote cache is available, iterate deps in dependency order using
# cached-get-deps.py (check → download-tarball, else build → upload).
# The extra_cmake_defines variable is exported by nhfboss-common.sh and must
# be passed verbatim so dep install-dir hashes stay consistent with the build.
if [[ -n ${GETDEPS_CACHE_URL:-} ]]; then
  time nice -n 10 python3 ./fboss/oss/scripts/cached-get-deps.py \
    --recursive --project fboss \
    --cache-url "$GETDEPS_CACHE_URL" \
    --extra-cmake-defines "$extra_cmake_defines" \
    --build-type "$BUILD_TYPE" \
    --allow-system-packages \
    --num-jobs "$num_jobs" \
    ${GETDEPS_CACHE_UPLOAD:+--upload}
  # cached-get-deps.py exits 0 only when every dep is either already-built,
  # successfully downloaded from cache, or successfully built from source —
  # so the belt-and-braces run-getdeps build pass below is redundant here.
  echo "Get deps SUCCESS"
  exit 0
fi

# No remote cache: build all deps from scratch.
time nice -n 10 ./fboss/oss/scripts/run-getdeps.py build --num-jobs $num_jobs --build-type $BUILD_TYPE --only-deps $common_options &&
  echo "Get deps SUCCESS"
