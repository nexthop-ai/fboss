# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Image Builder - handles building FBOSS images from manifests."""

import logging
import shutil
from pathlib import Path
from typing import ClassVar

from distro_cli.lib.artifact import find_artifact_in_dir
from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.docker.image import build_fboss_builder_image, get_root_dir
from distro_cli.lib.exceptions import BuildError, ComponentError, ManifestError

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
        # Setup the image builder directory
        root_dir = get_root_dir()
        self.image_builder_dir = root_dir / "fboss-image" / "image_builder"

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

    def _move_distro_file(self, format_name: str, file_extension: str):
        dist_formats = self.manifest.data.get("distribution_formats")
        if not dist_formats or format_name not in dist_formats:
            return

        output = find_artifact_in_dir(
                output_dir=self.image_builder_dir / "output",
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

        if not any(k in dist_formats for k in ["usb", "pxe", "onie"]):
            raise ManifestError("No distribution format specified in manifest")

        logger.info(f"Using image builder: {self.image_builder_dir}")

        # Ensure fboss_builder Docker image is available
        build_fboss_builder_image()

        # Set up volume mounts for the container
        # Mount /dev from host to allow loop device partition management
        volumes = {
            self.image_builder_dir: Path("/image_builder"),
            Path("/dev"): Path("/dev")
        }

        cmd = ["/image_builder/bin/build_image_in_container.sh"]
        if "pxe" in dist_formats or "usb" in dist_formats:
            cmd.append("--build-pxe-usb")
        if "onie" in dist_formats:
            cmd.append("--build-onie")

        # Run the build script inside fboss_builder container
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE,
            command=cmd,
            volumes=volumes,
            privileged=True
        )

        if exit_code != 0:
            raise BuildError(f"Base image build failed with exit code {exit_code}")

        self._move_distro_file("usb", "iso")
        self._move_distro_file("pxe", "tar")
        self._move_distro_file("onie", "bin")

        logger.info("Finished base OS image build")

    def _build_component(self, component: str):
        """Build a specific component."""
        logger.info(f"Building: {component}")

        comp_data = self.manifest.get_component(component)
        if comp_data is None:
            raise ComponentError(f"Component '{component}' not found in manifest")

        # Skip components with no directives
        if not comp_data:
            logger.info(f"Skipping empty component: {component}")
            return

        volumes = {
            self.image_builder_dir: Path("/image_builder"),
        }

        if "execute" in comp_data:
            cmd = comp_data["execute"]
            if not isinstance(cmd, list):
                raise ComponentError(
                    f"Component '{component}' execute directive must be a list, got {type(cmd).__name__}. "
                    "Use a wrapper script for complex shell commands."
                )

            exit_code = run_container(
                image=FBOSS_BUILDER_IMAGE,
                command=cmd,
                volumes=volumes,
                privileged=True,
                ephemeral=True
            )

            if exit_code != 0:
                raise BuildError(f"Build for component '{component}' failed with exit code {exit_code}")

        logger.info(f"Done building: {component}")
