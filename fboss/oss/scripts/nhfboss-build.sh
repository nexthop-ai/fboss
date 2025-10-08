#!/bin/bash

# Run inside the build container.
# Builds FBOSS against a real (default to 1.14.0) or fake SAI -- assumes
# dependencies have already been fetched and built using the
# nhfboss-get-deps.sh script.

usage() {
    echo "Usage: $0 [--fake-sai]"
    echo "  --fake-sai    Build against fake SAI instead of BRCM SAI"
    exit 1
}

USE_FAKE_SAI=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --fake-sai)
            USE_FAKE_SAI=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

pushd /var/FBOSS/fboss >/dev/null

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

if [ "$USE_FAKE_SAI" = true ]; then
    export BUILD_SAI_FAKE=1
    export BUILD_SAI_FAKE_LINK_TEST=1
else
    export SAI_BRCM_IMPL=1
    export SAI_SDK_VERSION=SAI_VERSION_12_2_0_0_ODP
    export SAI_VERSION=1.15.3
fi

./build/fbcode_builder/getdeps.py build --build-type MinSizeRel --no-deps $common_options

popd >/dev/null
