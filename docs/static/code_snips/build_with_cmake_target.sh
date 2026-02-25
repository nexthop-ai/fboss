#!/bin/bash
# Navigate to the right directory
cd /var/FBOSS/fboss || exit

# Build using a cmake target
<<<<<<< HEAD
time ./fboss/oss/scripts/run-getdeps.py build --allow-system-packages \
  --build-type MinSizeRel \
  --extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20", "RANGE_V3_TESTS": "OFF", "RANGE_V3_PERF": "OFF"}' \
  --scratch-path /var/FBOSS/tmp_bld_dir --cmake-target $TARGET fboss
||||||| 716bedba53
time ./fboss/oss/scripts/run-getdeps.py build --allow-system-packages \
  --extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20", "RANGE_V3_TESTS": "OFF", "RANGE_V3_PERF": "OFF"}' \
  --scratch-path /var/FBOSS/tmp_bld_dir --cmake-target $TARGET fboss
=======
time ./fboss/oss/scripts/run-getdeps.py \
  build \
  --allow-system-packages \
  --build-type MinSizeRel \
  --extra-cmake-defines='{"CMAKE_CXX_STANDARD": "20", "RANGE_V3_TESTS": "OFF", "RANGE_V3_PERF": "OFF"}' \
  --scratch-path /var/FBOSS/tmp_bld_dir \
  --cmake-target $TARGET \
  fboss
>>>>>>> 2d8d425e2cb666e8325cbc136b8199006fbd3d48
