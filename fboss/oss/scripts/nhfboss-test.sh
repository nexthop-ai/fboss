#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/nhfboss-common.sh"

# Run inside the build container
set -e
cd /var/FBOSS/fboss

export BUILD_SAI_FAKE=1
export BUILD_SAI_FAKE_LINK_TEST=1
export PATH=/opt/rh/gcc-toolset-12/root/usr/bin:$PATH
./build/fbcode_builder/getdeps.py test $common_options --timeout=90 "$@"
