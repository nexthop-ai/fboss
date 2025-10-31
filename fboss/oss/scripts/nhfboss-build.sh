#!/bin/bash

# Run inside the build container.
# Builds FBOSS against a real or fake SAI -- assumes
# dependencies have already been fetched and built using the
# nhfboss-get-deps.sh script.

USE_FAKE_SAI=${USE_FAKE_SAI:-false}
# Don't overload the system
num_jobs=$(( $(nproc) - 2 ))
echo 1000 > /proc/self/oom_score_adj

set -e
cd /var/FBOSS/fboss

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

if [ "$USE_FAKE_SAI" = true ]; then
    export BUILD_SAI_FAKE=1
    export BUILD_SAI_FAKE_LINK_TEST=1
else
    export SAI_BRCM_IMPL=1
    export SAI_SDK_VERSION=SAI_VERSION_13_3_0_0_ODP
    export SAI_VERSION=1.16.1
fi

export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
nice -n 10 ./build/fbcode_builder/getdeps.py build --num-jobs $num_jobs --build-type MinSizeRel --no-deps $common_options "$@"
