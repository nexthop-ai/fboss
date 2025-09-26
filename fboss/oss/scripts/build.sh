#!/bin/bash
set -e

export SCCACHE_DIR=/var/src/.sccache
export SCCACHE_CACHE_SIZE=30G

common_options='--allow-system-packages --scratch-path /var/src/.build_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

./build/fbcode_builder/getdeps.py install-system-deps --recursive fboss

echo "Building deps"
./build/fbcode_builder/getdeps.py build --only-deps $common_options

echo "Building FBOSS"
export BUILD_SAI_FAKE=1
export BUILD_SAI_FAKE_LINK_TEST=1
./build/fbcode_builder/getdeps.py build --build-type MinSizeRel --no-deps $common_options

./fboss/oss/scripts/package-fboss.py --scratch-path /var/src/.build_dir/ --compress
mv /var/src/.build_dir/fboss_bins.tar.zst .
