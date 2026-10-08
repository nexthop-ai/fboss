#!/bin/bash

export DOCKER_CONFIG=/tmp/docker-config
mkdir -p $DOCKER_CONFIG

if ! docker images | grep -q fboss_builder; then
  cat fboss/fboss_builder.tar | docker image load
fi

if ! docker images | grep -q fboss_proxy_device; then
  cat fboss/fboss-image/distro_cli/tests/proxy_device/proxy_device_image.tar | docker image load
fi

# The builder container bind-mounts the source tree and its build directories
# through the host Docker daemon, so stage them under /var/tmp, which is the same
# path inside the sandbox and on the host.
STAGE="$(mktemp -d /var/tmp/fboss_integration_XXXXXX)"
trap 'rm -rf "$STAGE" 2>/dev/null' EXIT
# test_helpers.enter_tempdir prefers TEST_TMPDIR, so both have to move.
export TMPDIR="$STAGE/tmp"
export TEST_TMPDIR="$TMPDIR"
export FBOSS_ROOT="$STAGE/root"
mkdir -p "$TMPDIR" "$FBOSS_ROOT/fboss-image/distro_cli" "$FBOSS_ROOT/fboss"
cp -rL fboss/fboss-image/distro_cli/tools "$FBOSS_ROOT/fboss-image/distro_cli/"
cp -rL fboss/fboss/oss "$FBOSS_ROOT/fboss/"

# distro_cli hands oss/scripts/region.env to every container. The region links are
# build state, not inputs, so recreate them in the copy as distro_build() does
# (//fboss:region_config provides regions/, and the links when one was selected).
REGION_DIR="$FBOSS_ROOT/fboss/oss/scripts"
if [ -n "${NH_CLOUD_PROVIDER:-}" ]; then
  if [ ! -f "$REGION_DIR/regions/${NH_CLOUD_PROVIDER}.env" ]; then
    echo "device_integration_test: unknown region '${NH_CLOUD_PROVIDER}'" >&2
    exit 1
  fi
  ln -sfn "regions/${NH_CLOUD_PROVIDER}.env" "$REGION_DIR/region.env"
  ln -sfn "regions/local_mirror.${NH_CLOUD_PROVIDER}.repo" "$REGION_DIR/region.repo"
elif [ ! -e "$REGION_DIR/region.env" ]; then
  echo "ERROR: no build region selected; pass --action_env=NH_CLOUD_PROVIDER=<region>" >&2
  exit 1
fi

cd fboss/fboss-image/distro_cli/tests || exit 1
PYTHONPATH="../..:${PYTHONPATH:-}" python3 device_integration_test.py "$@"
