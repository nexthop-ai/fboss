#!/bin/bash

# Run inside the build container.
# Builds FBOSS against a real or fake SAI -- assumes
# dependencies have already been fetched and built using the
# nhfboss-get-deps.sh script.

USE_FAKE_SAI=${USE_FAKE_SAI:-false}
# Don't overload the system
if [ -z "$num_jobs" ]; then
    num_jobs=$(( $(nproc) - 2 ))
fi
echo 1000 > /proc/self/oom_score_adj

set -e
cd /var/FBOSS/fboss

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

if [ "$USE_FAKE_SAI" = true ]; then
    export BUILD_SAI_FAKE=1
    export BUILD_SAI_FAKE_LINK_TEST=1
else
    export SAI_BRCM_IMPL=1
    export SAI_VERSION=${SAI_VERSION:-1.16.1}
    if [ -z "$SAI_SDK_VERSION" ]; then
        case $SAI_VERSION in
            1.14.0) SAI_SDK_VERSION=SAI_VERSION_11_7_0_0_ODP ;;
            1.15.3) SAI_SDK_VERSION=SAI_VERSION_12_2_0_0_ODP ;;
            1.16.1) SAI_SDK_VERSION=SAI_VERSION_13_3_0_0_ODP ;;
            *) echo "Don't know what SAI_SDK_VERSION to use for $SAI_VERSION"; exit 1 ;;
        esac
        echo "Using SAI_SDK_VERSION=$SAI_SDK_VERSION for SAI_VERSION=$SAI_VERSION"
        export SAI_SDK_VERSION
    fi
fi

export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
nice -n 10 ./build/fbcode_builder/getdeps.py build --num-jobs $num_jobs --build-type MinSizeRel --no-deps $common_options "$@"
