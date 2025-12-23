#!/usr/bin/env python3

# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""
Unit tests for ImageBuilder class
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from distro_cli.builder.image_builder import ImageBuilder
from distro_cli.lib.exceptions import BuildError, ComponentError
from distro_cli.lib.manifest import ImageManifest


class TestImageBuilder(unittest.TestCase):
    """Test ImageBuilder class"""

    def setUp(self):
        """Use the test manifest"""
        self.test_dir = Path(__file__).parent / "data"
        self.manifest_path = self.test_dir / "dev_image.json"
        self.manifest = ImageManifest(self.manifest_path)
        self.builder = ImageBuilder(self.manifest)

    def test_builder_initialization(self):
        """Test that builder initializes correctly"""
        self.assertIsNotNone(self.builder)
        self.assertEqual(self.builder.manifest, self.manifest)

    @patch("distro_cli.builder.image_builder.run_container")
    @patch("distro_cli.builder.image_builder.build_fboss_builder_image")
    @patch("distro_cli.builder.component.ComponentBuilder.build")
    def test_build_all(
        self, mock_component_build, mock_build_image, mock_run_container
    ):
        """Test build_all method with mocked component builds"""
        # Mock component builds to return fake artifact paths
        mock_component_build.return_value = Path("/fake/artifact.tar.gz")

        # Mock successful container execution for base image build
        mock_run_container.return_value = 0

        # Mock the _move_distro_file method to avoid file operations
        with patch.object(self.builder, "_move_distro_file"):
            self.builder.build_all()

        # Verify Docker image build was called
        mock_build_image.assert_called_once()

        # Verify component build was called for each component element in manifest
        # dev_image.json has: kernel (1), other_dependencies (2 elements), fboss-platform-stack (1),
        # bsps (2 elements), sai (1), fboss-forwarding-stack (1) = 8 total
        self.assertEqual(mock_component_build.call_count, 8)

        # Verify run_container was called once for the base image build script
        mock_run_container.assert_called_once()
        command = mock_run_container.call_args.kwargs["command"]
        self.assertIn(
            "/image_builder/bin/build_image_in_container.sh", " ".join(command)
        )

    @patch("distro_cli.builder.component.ComponentBuilder.build")
    def test_build_components(self, mock_component_build):
        """Test build_components method with mocked component builds"""
        # Mock component builds to return fake artifact paths
        mock_component_build.return_value = Path("/fake/artifact.tar.gz")

        # Request 'sai' and 'fboss-platform-stack' which both have execute commands
        components = ["sai", "fboss-platform-stack"]
        self.builder.build_components(components)

        # Verify component build was called for each requested component
        self.assertEqual(mock_component_build.call_count, 2)

        # Verify artifacts were stored
        self.assertIn("sai", self.builder.component_artifacts)
        self.assertIn("fboss-platform-stack", self.builder.component_artifacts)

    def test_build_component_not_found(self):
        """Test building a component that doesn't exist in manifest"""
        with self.assertRaises(ComponentError) as cm:
            self.builder.build_components(["nonexistent_component"])

        # Verify error message
        self.assertIn("nonexistent_component", str(cm.exception))
        self.assertIn("not found", str(cm.exception))

    @patch("distro_cli.builder.component.ComponentBuilder.build")
    def test_build_component_execution_failure(self, mock_component_build):
        """Test handling of component build failure"""
        # Mock failed component build
        mock_component_build.side_effect = BuildError(
            "sai build failed with exit code 1"
        )

        with self.assertRaises(BuildError) as cm:
            self.builder.build_components(["sai"])

        # Verify error message contains component name and exit code
        self.assertIn("sai", str(cm.exception))
        self.assertIn("exit code 1", str(cm.exception))

        # Component build should have been called once (for sai)
        mock_component_build.assert_called_once()


if __name__ == "__main__":
    unittest.main()
