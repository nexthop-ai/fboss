#!/bin/bash
# Navigate to the right directory
cd /var/FBOSS/fboss || exit

# Set environment variables appropriate for your build
export SAI_BRCM_IMPL=1

# Start the build
<<<<<<< HEAD
time ./build/fbcode_builder/getdeps.py build --allow-system-packages \
  --build-type MinSizeRel \
  --extra-cmake-defines='{"CMAKE_CXX_STANDARD": "20"}' \
  --scratch-path /var/FBOSS/tmp_bld_dir fboss
||||||| 81da1b3a3f
time ./build/fbcode_builder/getdeps.py build --allow-system-packages \
--extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20"}' \
--scratch-path /var/FBOSS/tmp_bld_dir fboss
=======
time ./fboss/oss/scripts/run-getdeps.py build --allow-system-packages \
--extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20"}' \
--scratch-path /var/FBOSS/tmp_bld_dir fboss
>>>>>>> 285e7f8dbe069e649de933f0e791f98560c6c2dd
