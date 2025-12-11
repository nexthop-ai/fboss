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

from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.docker.image import build_fboss_builder_image

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
                logger.error(f"Component '{component}' not found in manifest")
                sys.exit(1)

        # Build requested components in dependency order
        for component in self.COMPONENTS:
            if component in component_names:
                self._build_component(component)


    def _mv_distro_file(self, image_builder_dir: Path, format_name: str, file_extension: str):
        dist_formats = self.manifest.data.get("distribution_formats")
        if not dist_formats or format_name not in dist_formats:
            return

        output = image_builder_dir / "output" / f"FBOSS-Distro-Image.x86_64-1.0.install.{file_extension}"
        image = Path(dist_formats[format_name])

        if not output.exists():
            logger.error(f"Image build output not found: {output}")
            sys.exit(1)

        shutil.move(str(output), str(image))


    def _build_base_image(self):
        """Build the base OS image and create distribution artifacts."""
        logger.info("Starting base OS image build")

        # Validate distribution formats are specified
        dist_formats = self.manifest.data.get("distribution_formats")
        if not dist_formats:
            logger.error("No distribution formats specified in manifest")
            sys.exit(1)

        if not any(k in dist_formats for k in ["usb", "pxe"]):
            logger.error("No distribution format specified in manifest")
            sys.exit(1)

        # Locate the image builder directory
        script_dir = Path(__file__).parent.resolve()
        distro_cli_dir = script_dir.parent
        fboss_image_dir = distro_cli_dir.parent
        image_builder_dir = fboss_image_dir / "image_builder"

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

        self._mv_distro_file(image_builder_dir, "usb", "iso")
        self._mv_distro_file(image_builder_dir, "pxe", "tar")

        logger.info("Finished base OS image build")


    def _build_component(self, component: str):
        """Build a specific component."""
        logger.info(f"Building: {component}")
        logger.info(f"Done building: {component} (stub)")
