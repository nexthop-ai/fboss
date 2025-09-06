#!/bin/bash

# Run inside the build container
pushd /var/FBOSS/fboss >/dev/null

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

#export BUILD_SAI_FAKE=1
#export BUILD_SAI_FAKE_LINK_TEST=1
export SAI_BRCM_IMPL=1
export SAI_SDK_VERSION=SAI_VERSION_11_7_0_0_ODP
export SAI_VERSION=1.14.0
./build/fbcode_builder/getdeps.py build --build-type MinSizeRel --no-deps $common_options

popd >/dev/null
