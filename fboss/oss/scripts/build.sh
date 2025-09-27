#!/bin/bash
set -e

export SCCACHE_DIR=/var/src/.sccache
export SCCACHE_CACHE_SIZE=30G

common_options='--allow-system-packages --scratch-path /var/src/.build_dir --src-dir . --extra-cmake-defines {"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"} fboss'

./build/fbcode_builder/getdeps.py install-system-deps --recursive fboss

SAI_DIR=/var/src/.build_dir/sai
source $SAI_DIR/sai_build.env

if [ -z "$BUILD_SAI_FAKE" ]; then
    ./fboss/oss/scripts/build-helper.py $SAI_DIR/lib/libsai_impl.a $SAI_DIR/include /var/src/.build_dir/sai_impl $SAI_VERSION
fi

echo "Building deps"
./build/fbcode_builder/getdeps.py build --only-deps $common_options

echo "Building FBOSS"
./build/fbcode_builder/getdeps.py build --build-type MinSizeRel --no-deps $common_options

./fboss/oss/scripts/package-fboss.py --scratch-path /var/src/.build_dir/ --compress
mv /var/src/.build_dir/fboss_bins.tar.zst .