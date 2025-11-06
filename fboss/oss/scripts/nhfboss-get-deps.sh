#!/bin/bash

# Run inside the build container
# Fetches and builds only dependencies, not FBOSS itself -- allows one-time
# dependency setup for multiple FBOSS builds during development. Takes 30
# minutes initially without a primed cache, and less than 10 minutes subsequent
# runs.
# REQUIRED: If building against the real SAI, run build-helper before each
# build since it stages the SAI files for an HTTP server that the wrapped
# getdeps script can understand.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nhfboss-common.sh"

set -e
cd /var/FBOSS/fboss

export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
time nice -n 10 ./build/fbcode_builder/getdeps.py install-system-deps --num-jobs $num_jobs --recursive $common_options
time nice -n 10 ./build/fbcode_builder/getdeps.py build --num-jobs $num_jobs --only-deps $common_options
echo "Get deps SUCCESS"
