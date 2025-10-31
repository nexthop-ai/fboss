#!/bin/bash

# Run inside the build container
# Fetches and builds only dependencies, not FBOSS itself -- allows one-time
# dependency setup for multiple FBOSS builds during development. Takes 30
# minutes initially without a primed cache, and less than 10 minutes subsequent
# runs.
# REQUIRED: If building against the real SAI, run build-helper before each
# build since it stages the SAI files for an HTTP server that the wrapped
# getdeps script can understand.

# Don't overload the system
if [ -z "$num_jobs" ]; then
    num_jobs=$(( $(nproc) - 2 ))
fi

set -e
cd /var/FBOSS/fboss

export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'
nice -n 10 ./build/fbcode_builder/getdeps.py install-system-deps --num-jobs $num_jobs --recursive $common_options
nice -n 10 ./build/fbcode_builder/getdeps.py build --num-jobs $num_jobs --only-deps $common_options
