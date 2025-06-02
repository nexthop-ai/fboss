#!/bin/bash

# Run inside the build container
pushd /var/FBOSS/fboss >/dev/null

common_options='--allow-system-packages --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . fboss'
./build/fbcode_builder/getdeps.py install-system-deps --recursive $common_options
./build/fbcode_builder/getdeps.py build --only-deps $common_options

popd >/dev/null
