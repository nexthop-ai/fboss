#!/bin/bash
<<<<<<< HEAD
python3 fboss/lib/oss/run-helper.py \
  --target fboss-platform-mapping-gen.GEN_PY_EXE \
  --extra-cmake-defines='{"RANGE_V3_TESTS":"OFF"}' \
||||||| a75ad2f54f
python3 fboss/lib/oss/run-helper.py --target fboss-platform-mapping-gen "$@"
=======
exec python3 fboss/lib/oss/run-helper.py \
  --target fboss-platform-mapping-gen \
  --fboss-root fboss \
>>>>>>> 4c0febe6554dd53b1a6eed56b3bb194e2f42f408
  "$@"
