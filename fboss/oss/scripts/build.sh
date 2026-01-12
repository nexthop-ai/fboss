#!/bin/bash
set -e

export SCCACHE_DIR=/var/FBOSS/fboss/.sccache
export SCCACHE_CACHE_SIZE=30G

SAI_DIR=/var/FBOSS/fboss/.build_dir/sai
source $SAI_DIR/sai_build.env

if [ -n "$BUILD_SAI_FAKE" ]; then
  sai_name="sai-fake"
else
  if [ -n "$SAI_BRCM_IMPL" ]; then
    sai_name="sai-bcm-$SAI_SDK_VERSION"
  else
    sai_name="sai-unknown"
  fi
fi

build_dir="/var/FBOSS/fboss/.build_dir/${sai_name}"
mkdir -p $build_dir

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nhfboss-common.sh"

# Share download caches
mkdir -p /var/FBOSS/fboss/.build_dir/downloads
[ ! -L $build_dir/downloads ] && ln -s /var/FBOSS/fboss/.build_dir/downloads $build_dir/downloads
mkdir -p /var/FBOSS/fboss/.build_dir/repos
[ ! -L $build_dir/repos ] && ln -s /var/FBOSS/fboss/.build_dir/repos $build_dir/repos
mkdir -p /var/FBOSS/fboss/.build_dir/extracted
[ ! -L $build_dir/extracted ] && ln -s /var/FBOSS/fboss/.build_dir/extracted $build_dir/extracted

# The build will modify these files when building against a real SAI. Snapshot these files so they can be restored. We
# shouldn't use something like git stash because we are running as root inside the build container.
tar -cf manifests_snapshot.tar build/fbcode_builder/manifests/fboss build/fbcode_builder/manifests/libsai

./fboss/oss/scripts/run-getdeps.py install-system-deps --recursive fboss

if [ -z "$BUILD_SAI_FAKE" ]; then
  ./fboss/oss/scripts/build-helper.py $SAI_DIR/lib/libsai_impl.a $SAI_DIR/include $build_dir/sai_impl $SAI_VERSION
fi

echo "Building deps"
nice -n 10 ./fboss/oss/scripts/run-getdeps.py build --num-jobs ${num_jobs:?} --only-deps ${common_options:?}

export BENCHMARK_INSTALL=1

echo "Building FBOSS"
nice -n 10 ./fboss/oss/scripts/run-getdeps.py build --num-jobs ${num_jobs:?} --build-type MinSizeRel --no-deps ${common_options:?}

nice -n 10 ./fboss/oss/scripts/package-fboss.py --scratch-path $build_dir/ --compress
mv $build_dir/fboss_bins.tar.zst .
rm -rf $build_dir/fboss_bins-*

# Restore modified manifests
tar -xf manifests_snapshot.tar
rm manifests_snapshot.tar
