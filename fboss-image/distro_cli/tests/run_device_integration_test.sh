#!/bin/bash

export DOCKER_CONFIG=/tmp/docker-config
mkdir -p $DOCKER_CONFIG

if ! docker images | grep -q fboss_builder; then
  cat fboss/fboss_builder.tar | docker image load
fi

if ! docker images | grep -q fboss_proxy_device; then
  cat fboss/fboss-image/distro_cli/tests/proxy_device/proxy_device_image.tar | docker image load
fi

cd fboss/fboss-image/distro_cli/tests || exit 1
PYTHONPATH="../..:${PYTHONPATH:-}" python3 device_integration_test.py "$@"
