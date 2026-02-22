#!/bin/bash
# Navigate to the right directory
cd /var/FBOSS/fboss || exit

# Build using a cmake target
time ./fboss/oss/scripts/run-getdeps.py build --allow-system-packages \
<<<<<<< HEAD
  --build-type MinSizeRel \
  --extra-cmake-defines='{"CMAKE_CXX_STANDARD": "20"}' \
||||||| 7e29d6aa34
--extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20"}' \
--scratch-path /var/FBOSS/tmp_bld_dir --src-dir . fboss
=======
  --extra-cmake-defines='{"CMAKE_BUILD_TYPE": "MinSizeRel", "CMAKE_CXX_STANDARD": "20", "RANGE_V3_TESTS": "OFF", "RANGE_V3_PERF": "OFF"}' \
>>>>>>> 716bedba537020d694677496e22daa66dbcb4d42
  --scratch-path /var/FBOSS/tmp_bld_dir --src-dir . fboss
