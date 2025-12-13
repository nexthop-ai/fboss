# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Image Builder - handles building FBOSS images from manifests."""

import logging
import shutil
import sys
from pathlib import Path
from typing import ClassVar

from distro_cli.lib.artifact import find_artifact_in_dir
from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.docker.image import build_fboss_builder_image, get_root_dir
from distro_cli.lib.exceptions import ComponentError, ManifestError

logger = logging.getLogger(__name__)


class ImageBuilder:
    """Handles building FBOSS images from manifests."""

    # Component list - build order based on dependencies
    # TODO: Convert to DAG for parallel builds and easier extensibility
    COMPONENTS: ClassVar[list[str]] = [
        'kernel',
        'other_dependencies',
        'fboss-platform-stack',
        'bsps',
        'sai',
        'fboss-forwarding-stack'
    ]

    def __init__(self, manifest):
        self.manifest = manifest
        self.workspace_root = manifest.manifest_dir

    def build_all(self):
        """Build all components and create distribution artifacts."""
        logger.info("Building FBOSS Image")

        # Build components in dependency order (if present in manifest)
        for component in self.COMPONENTS:
            if self.manifest.has_component(component):
                self._build_component(component)

        self._build_base_image()

    def build_components(self, component_names: list[str]):
        """Build specific components only."""
        logger.info(f"Building components: {', '.join(component_names)}")

        # Validate all requested components exist in manifest
        for component in component_names:
            if not self.manifest.has_component(component):
                raise ComponentError(f"Component '{component}' not found in manifest")

        # Build requested components in dependency order
        for component in self.COMPONENTS:
            if component in component_names:
                self._build_component(component)

    def _move_distro_file(self, image_builder_dir: Path, format_name: str, file_extension: str):
        dist_formats = self.manifest.data.get("distribution_formats")
        if not dist_formats or format_name not in dist_formats:
            return

        output = find_artifact_in_dir(
                output_dir=image_builder_dir / "output",
                pattern=f"FBOSS-Distro-Image.x86_64-1.0.install.{file_extension}",
                component_name="Base image")
        image = Path(dist_formats[format_name])
        shutil.move(str(output), str(image))

    def _build_base_image(self):
        """Build the base OS image and create distribution artifacts."""
        logger.info("Starting base OS image build")

        # Validate distribution formats are specified
        dist_formats = self.manifest.data.get("distribution_formats")
        if not dist_formats:
            raise ManifestError("No distribution formats specified in manifest")

        if not any(k in dist_formats for k in ["usb", "pxe"]):
            raise ManifestError("No distribution format specified in manifest")

        # Locate the image builder directory
        root_dir = get_root_dir()
        image_builder_dir = root_dir / "fboss-image" / "image_builder"

        logger.info(f"Using image builder: {image_builder_dir}")

        # Ensure fboss_builder Docker image is available
        build_fboss_builder_image()

        # Set up volume mounts for the container
        # Mount /dev from host to allow loop device partition management
        volumes = {
            image_builder_dir: Path("/image_builder"),
            Path("/dev"): Path("/dev")
        }

        # Run the build script inside fboss_builder container
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE,
            command=["/image_builder/bin/build_image_in_container.sh"],
            volumes=volumes,
            privileged=True
        )

        if exit_code != 0:
            logger.error(f"Build script failed with exit code {exit_code}")
            sys.exit(1)

        self._move_distro_file(image_builder_dir, "usb", "iso")
        self._move_distro_file(image_builder_dir, "pxe", "tar")

        logger.info("Finished base OS image build")

    def _build_component(self, component: str):
        """Build a specific component."""
        logger.info(f"Building: {component}")
        logger.info(f"Done building: {component} (stub)")
