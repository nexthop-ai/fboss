#!/usr/bin/env bash

# FBOSS is now built using fbcode_builder. Thus, just invoke fbcode_builder
# getdeps.py to build fboss here.

TOOLCHAIN_DIR=/opt/rh/devtoolset-8/root/usr/bin
if [[ -d $TOOLCHAIN_DIR ]]; then
  PATH="$TOOLCHAIN_DIR:$PATH"
fi

FBOSS_DIR=$(dirname "$0")
GETDEPS_PATHS=(
<<<<<<< HEAD
  "$FBOSS_DIR/build/fbcode_builder/getdeps.py"
  "$FBOSS_DIR/../../opensource/fbcode_builder/getdeps.py"
||||||| 81da1b3a3f
    "$FBOSS_DIR/build/fbcode_builder/getdeps.py"
    "$FBOSS_DIR/../../opensource/fbcode_builder/getdeps.py"
=======
    "$FBOSS_DIR/fboss/oss/scripts/run-getdeps.py"
    "$FBOSS_DIR/../../opensource/fbcode_builder/getdeps.py"
>>>>>>> 285e7f8dbe069e649de933f0e791f98560c6c2dd
)
for getdeps in "${GETDEPS_PATHS[@]}"; do
  if [[ -x $getdeps ]]; then
    exec "$getdeps" build fboss --current-project fboss "$@"
  fi
done
echo "Could not find getdeps.py!?" >&2
exit 1
