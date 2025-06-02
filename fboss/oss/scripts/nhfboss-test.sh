#!/bin/bash

# Run inside the build container
pushd /var/FBOSS/fboss >/dev/null

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . fboss'

export BUILD_SAI_FAKE=1
export BUILD_SAI_FAKE_LINK_TEST=1
./build/fbcode_builder/getdeps.py test $common_options

popd >/dev/null
