#!/bin/bash
set -e

pushd parts/ipxe
./build.sh
popd

# docker build cannot COPY from outside its context, so stage the shared
# local-mirror dnf config in and drop it again once the build is done.
trap 'rm -f parts/local_mirror.repo' EXIT
cp ../../fboss/oss/docker/local_mirror.repo parts/local_mirror.repo

DOCKER_BUILDKIT=1 docker build . -t fboss_distro_infra
