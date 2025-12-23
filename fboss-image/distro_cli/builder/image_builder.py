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

from distro_cli.builder.component import ComponentBuilder
from distro_cli.lib.artifact import ArtifactStore, find_artifact_in_dir
from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.docker.image import build_fboss_builder_image
from distro_cli.lib.exceptions import BuildError, ComponentError, ManifestError
from distro_cli.lib.paths import get_root_dir

logger = logging.getLogger(__name__)

# Component-specific artifact patterns
# These are used when the manifest doesn't specify an "artifact" field
COMPONENT_ARTIFACT_PATTERNS = {
    "kernel": "kernel-*.rpms.tar.gz",
    "sai": "sai-*.tar.gz",
    "fboss-platform-stack": "fboss-platform-stack-*.tar.gz",
    "fboss-forwarding-stack": "fboss-forwarding-stack-*.tar.gz",
    "bsps": "bsp-*.tar.gz",
}


def _get_component_directory(component_name: str, script_path: str) -> str:
    """Determine the component directory for build artifacts.

    For scripts_path that has the component_name, we return the path in script_path
    leading to the component_name. Otherwise, the script's parent directory is returned.

    Args:
        component_name: Base component name (without array index)
        script_path: Path to the build script from the execute directive

    Returns:
        Component directory path (relative to workspace root)

    """
    script_path_obj = Path(script_path)

    # Check if component_name appears in the script path
    if component_name in script_path_obj.parts:
        # Find the index of component_name in the path
        parts = script_path_obj.parts
        component_index = parts.index(component_name)
        # Return the path up to and including the component_name
        return str(Path(*parts[: component_index + 1]))

    # Fall back to script's parent directory
    return str(script_path_obj.parent)


class ImageBuilder:
    """Handles building FBOSS images from manifests."""

    # Component list - build order based on dependencies
    # TODO: Convert to DAG for parallel builds and easier extensibility
    COMPONENTS: ClassVar[list[str]] = [
        "kernel",
        "other_dependencies",
        "fboss-platform-stack",
        "bsps",
        "sai",
        "fboss-forwarding-stack",
    ]

    def __init__(self, manifest):
        self.manifest = manifest
        self.workspace_root = manifest.manifest_dir
        self.store = ArtifactStore()
        self.component_artifacts = {}
        # Setup the image builder directory
        root_dir = get_root_dir()
        self.image_builder_dir = root_dir / "fboss-image" / "image_builder"

    def _create_component_builder(
        self, component_name: str, component_data: dict
    ) -> ComponentBuilder:
        """Create a ComponentBuilder for the given component.

        Build artifacts (.build and dist directories) are created at the component
        root directory if known, otherwise beside the component's build script.

        Args:
            component_name: Name of the component (from JSON key)
            component_data: Component data dict from manifest

        Returns:
            ComponentBuilder instance configured for the component
        """
        root_dir = get_root_dir()

        # For array elements, extract the base name
        base_name = (
            component_name.split("[")[0] if "[" in component_name else component_name
        )

        # Derive build_artifact_subdir from the execute directive path
        build_artifact_subdir = None
        if "execute" in component_data:
            execute_cmd = component_data["execute"]
            # Get the first element (script path) whether it's a string or list
            script_path = (
                execute_cmd if isinstance(execute_cmd, str) else execute_cmd[0]
            )
            # Determine component directory (component root if known, else script's parent)
            build_artifact_subdir = _get_component_directory(base_name, script_path)

        # Get artifact pattern from the predefined patterns
        artifact_pattern = COMPONENT_ARTIFACT_PATTERNS.get(base_name)

        return ComponentBuilder(
            component_name=component_name,
            component_data=component_data,
            manifest_dir=self.manifest.manifest_dir,
            store=self.store,
            root_dir=root_dir,
            build_artifact_subdir=build_artifact_subdir,
            artifact_pattern=artifact_pattern,
        )

    def build_all(self):
        """Build all components and distribution artifacts."""
        logger.info("Building FBOSS Image")

        for component in self.COMPONENTS:
            if self.manifest.has_component(component):
                self._build_component(component)

        self._build_base_image()

    def build_components(self, component_names: list[str]):
        """Build specific components."""
        logger.info(f"Building components: {', '.join(component_names)}")

        for component in component_names:
            if not self.manifest.has_component(component):
                raise ComponentError(f"Component '{component}' not found in manifest")

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
            component_name="Base image",
        )
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
            Path("/dev"): Path("/dev"),
        }

        cmd = ["/image_builder/bin/build_image_in_container.sh"]
        if "pxe" in dist_formats or "usb" in dist_formats:
            cmd.append("--build-pxe-usb")
        if "onie" in dist_formats:
            cmd.append("--build-onie")

        # Run the build script inside fboss_builder container
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE, command=cmd, volumes=volumes, privileged=True
        )

        if exit_code != 0:
            raise BuildError(f"Base image build failed with exit code {exit_code}")

        self._move_distro_file("usb", "iso")
        self._move_distro_file("pxe", "tar")
        self._move_distro_file("onie", "bin")

        logger.info("Finished base OS image build")

    def _build_component(self, component: str):
        """Build a specific component by delegating to component builder."""
        logger.info(f"Building: {component}")

        component_data = self.manifest.get_component(component)

        # Check if component is an array - if so, build each element
        if isinstance(component_data, list):
            artifact_paths = []
            for idx, element_data in enumerate(component_data):
                element_name = f"{component}[{idx}]"
                logger.info(f"Building: {element_name}")

                # Create a ComponentBuilder for this array element
                component_builder = self._create_component_builder(
                    element_name, element_data
                )
                artifact_path = component_builder.build()
                if artifact_path:
                    artifact_paths.append(artifact_path)

            self.component_artifacts[component] = (
                artifact_paths if artifact_paths else None
            )
            return

        # Create the component builder and build it
        component_builder = self._create_component_builder(component, component_data)
        artifact_path = component_builder.build()
        self.component_artifacts[component] = artifact_path
