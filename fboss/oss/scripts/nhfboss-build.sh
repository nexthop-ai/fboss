#!/bin/bash

# Run inside the build container.
# Builds FBOSS against a real or fake SAI -- assumes
# dependencies have already been fetched and built using the
# nhfboss-get-deps.sh script.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=fboss/oss/scripts/nhfboss-common.sh
source "$SCRIPT_DIR/nhfboss-common.sh"

SAI_IMPL=${SAI_IMPL:-brcm} # Options: brcm, csco, fake

set -e
cd /var/FBOSS/fboss

# Map SAI_IMPL to run-getdeps.py --npu-sai-impl flag
npu_sai_impl_flag=""

case "$SAI_IMPL" in
fake)
  echo "Building with fake SAI"
  export BUILD_SAI_FAKE=1
  export BUILD_SAI_FAKE_LINK_TEST=1
  # Don't pass --npu-sai-impl for fake SAI; run-getdeps.py defaults to fake when not specified
  npu_sai_impl_flag=""
  ;;

brcm)
  echo "Building with Broadcom SAI"
  export SAI_BRCM_IMPL=1
  export SAI_VERSION=${SAI_VERSION:-1.16.1}
  if [ -z "$SAI_SDK_VERSION" ]; then
    case $SAI_VERSION in
    1.14.0) SAI_SDK_VERSION=SAI_VERSION_11_7_0_0_ODP ;;
    1.15.3) SAI_SDK_VERSION=SAI_VERSION_12_2_0_0_ODP ;;
    1.16.1) SAI_SDK_VERSION=SAI_VERSION_13_3_0_0_ODP ;;
    *)
      echo "Don't know what SAI_SDK_VERSION to use for SAI_VERSION=$SAI_VERSION"
      exit 1
      ;;
    esac
    echo "Using SAI_SDK_VERSION=$SAI_SDK_VERSION for SAI_VERSION=$SAI_VERSION"
    export SAI_SDK_VERSION
  fi
  npu_sai_impl_flag="--npu-sai-impl SAI_BRCM_IMPL --npu-sai-sdk-version $SAI_SDK_VERSION"
  ;;

csco)
  echo "Building with Cisco/Silicon One SAI (G202X)"
  export SAI_TAJO_IMPL=1
  export SAI_VERSION=${SAI_VERSION:-1.17.0}
  if [ -z "$SAI_SDK_VERSION" ]; then
    case $SAI_VERSION in
    1.14.0) SAI_SDK_VERSION=TAJO_SDK_VERSION_24_8_3001 ;;
    1.17.0) SAI_SDK_VERSION=TAJO_SDK_VERSION_25_11_4210 ;;
    *)
      echo "Don't know what SAI_SDK_VERSION to use for SAI_VERSION=$SAI_VERSION"
      exit 1
      ;;
    esac
    echo "Using SAI_SDK_VERSION=$SAI_SDK_VERSION for SAI_VERSION=$SAI_VERSION"
    export SAI_SDK_VERSION
  fi
  npu_sai_impl_flag="--npu-sai-impl SAI_TAJO_IMPL --npu-sai-sdk-version $SAI_SDK_VERSION"
  ;;

*)
  echo "Error: Unknown SAI_IMPL='$SAI_IMPL'"
  echo "Valid options: brcm, csco, fake"
  echo "Usage: SAI_IMPL=csco $0"
  echo "   or: SAI_IMPL=fake $0"
  exit 1
  ;;
esac

export BENCHMARK_INSTALL=1

time nice -n 10 ./fboss/oss/scripts/run-getdeps.py $npu_sai_impl_flag build --num-jobs $num_jobs --build-type $BUILD_TYPE --no-deps $common_options "$@" &&
  echo "Build SUCCESS"
