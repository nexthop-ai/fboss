# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Execute utilities for FBOSS image builder."""

import logging
from pathlib import Path

from distro_cli.lib.docker.container import run_container
from distro_cli.lib.docker.image import build_fboss_builder_image

from .exceptions import BuildError

logger = logging.getLogger(__name__)


def execute_build_in_container(
    image_name: str,
    command: list[str],
    volumes: dict[Path, Path],
    component_name: str,
    privileged: bool = False,
    working_dir: str | None = None,
) -> None:
    """Execute build command in Docker container.

    Args:
        image_name: Docker image name
        command: Command to execute as list
        volumes: Host to container path mappings
        component_name: Component name
        privileged: Run in privileged mode
        working_dir: Working directory in container

    Raises:
        BuildError: If build fails
    """
    logger.info(f"Executing {component_name} build in Docker container: {image_name}")

    # Ensure fboss_builder image is built
    build_fboss_builder_image()

    logger.info(f"Running in container: {' '.join(command)}")

    try:
        exit_code = run_container(
            image=image_name,
            command=command,
            volumes=volumes,
            privileged=privileged,
            working_dir=working_dir,
        )

        if exit_code != 0:
            raise BuildError(
                f"{component_name} build failed with exit code {exit_code}"
            )

        logger.info(f"{component_name} build in container complete")

    except RuntimeError as e:
        raise BuildError(f"Failed to run Docker container: {e}")
