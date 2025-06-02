#!/usr/bin/env python3

# Build the FBOSS build container

import importlib
docker_build = importlib.import_module("docker-build")

docker_build.build_docker_image(docker_build.get_docker_path())
