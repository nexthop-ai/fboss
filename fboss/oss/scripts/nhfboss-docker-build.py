#!/usr/bin/env python3

# Build the image for creating the container to build FBOSS in.
# Creates only the Docker image from docker-build.py without running the full build process,
# allowing the container to be reused for faster incremental development cycles.

import importlib
import os
docker_build = importlib.import_module("docker-build")

use_clang = os.getenv("USE_CLANG", "").lower() in ("true", "1", "yes")
if use_clang:
    print("Using clang for build (experimental)")

docker_build.build_docker_image(docker_build.get_docker_path(), use_clang)
