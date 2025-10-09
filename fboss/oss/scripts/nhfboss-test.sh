#!/bin/bash

# Run inside the build container
set -e
cd /var/FBOSS/fboss

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

export BUILD_SAI_FAKE=1
export BUILD_SAI_FAKE_LINK_TEST=1
export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
./build/fbcode_builder/getdeps.py test $common_options "$@"
