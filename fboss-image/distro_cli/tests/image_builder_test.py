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
from distro_cli.tests.test_helpers import enter_tempdir, override_artifact_store_dir


class TestImageBuilder(unittest.TestCase):
    """Test ImageBuilder class"""

    def setUp(self):
        """Use the test manifest"""
        self.test_dir = Path(__file__).parent / "data"
        self.manifest_path = self.test_dir / "dev_image.json"
        self.manifest = ImageManifest(self.manifest_path)

        # Use sandbox-safe temporary directory
        self._tempdir_ctx = enter_tempdir("image_builder_test_")
        self.temp_dir = self._tempdir_ctx.__enter__()

        # Override artifact store directory for testing
        self._artifact_store_ctx = override_artifact_store_dir(self.temp_dir)
        self._artifact_store_ctx.__enter__()

        self.builder = ImageBuilder(self.manifest)

    def tearDown(self):
        """Clean up test fixtures"""
        # Exit context managers in reverse order
        self._artifact_store_ctx.__exit__(None, None, None)
        self._tempdir_ctx.__exit__(None, None, None)

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

        # Mock _build_base_image and _move_distro_file to avoid file operations
        with patch.object(
            self.builder, "_build_base_image"
        ) as mock_build_base, patch.object(self.builder, "_move_distro_file"):
            self.builder.build_all()

        # Verify _build_base_image was called (we mock it to avoid file writes)
        mock_build_base.assert_called_once()

        # Verify component build was called for each component element in manifest
        # dev_image.json has: kernel (1), other_dependencies (2 elements), fboss-platform-stack (1),
        # bsps (2 elements), sai (1), fboss-forwarding-stack (1), image_build_hooks (1) = 9 total
        self.assertEqual(mock_component_build.call_count, 9)

    @patch("distro_cli.builder.image_builder.ImageBuilder._compress_artifact")
    @patch("distro_cli.builder.component.ComponentBuilder.build")
    def test_build_components(self, mock_component_build, mock_compress):
        """Test build_components method with mocked component builds"""
        # Mock component builds to return fake artifact paths
        mock_component_build.return_value = Path("/fake/artifact.tar")

        # Mock compression to return compressed path
        mock_compress.side_effect = lambda path, _: Path(
            str(path).replace(".tar", ".tar.zst")
        )

        # Request 'sai' and 'fboss-platform-stack' which both have execute commands
        # Note: 'sai' depends on 'kernel', so kernel will be built first
        # 'fboss-forwarding-stack' depends on 'sai', so sai will be built first
        components = ["sai", "fboss-platform-stack"]
        self.builder.build_components(components)

        # Verify component build was called for:
        # 1. kernel (dependency of sai)
        # 2. sai (requested)
        # 3. fboss-platform-stack (requested)
        self.assertEqual(mock_component_build.call_count, 3)

        # Verify compression was called for each component (component mode enables compression)
        self.assertEqual(mock_compress.call_count, 3)

        # Verify artifacts were stored
        self.assertIn("kernel", self.builder.component_artifacts)  # Built as dependency
        self.assertIn("sai", self.builder.component_artifacts)
        self.assertIn("fboss-platform-stack", self.builder.component_artifacts)

    @patch("distro_cli.builder.image_builder.ImageBuilder._compress_artifact")
    @patch("distro_cli.builder.image_builder.ComponentBuilder")
    def test_component_builder_receives_correct_salt_in_component_mode(
        self, mock_component_builder_class, mock_compress
    ):
        """Test that ComponentBuilder receives 'compressed' salt in component mode."""
        # Mock the ComponentBuilder instance and its build method
        mock_instance = mock_component_builder_class.return_value
        mock_instance.build.return_value = Path("/fake/artifact.tar")

        # Mock compression to return compressed path
        mock_compress.side_effect = lambda path, _: Path(
            str(path).replace(".tar", ".tar.zst")
        )

        # Build components (which enables compression)
        self.builder.build_components(["kernel"])

        # Verify ComponentBuilder was instantiated with artifact_key_salt='compressed'
        mock_component_builder_class.assert_called()
        call_kwargs = mock_component_builder_class.call_args.kwargs
        self.assertEqual(
            call_kwargs.get("artifact_key_salt"),
            "compressed",
            "ComponentBuilder should receive 'compressed' salt in component mode",
        )

    @patch("distro_cli.builder.image_builder.ComponentBuilder")
    @patch("distro_cli.builder.image_builder.run_container")
    @patch("distro_cli.builder.image_builder.build_fboss_builder_image")
    def test_component_builder_receives_correct_salt_in_full_build_mode(
        self, mock_build_image, mock_run_container, mock_component_builder_class
    ):
        """Test that ComponentBuilder receives 'uncompressed' salt in full build mode."""
        # Mock the ComponentBuilder instance and its build method
        mock_instance = mock_component_builder_class.return_value
        mock_instance.build.return_value = Path("/fake/artifact.tar")

        # Mock successful container execution
        mock_run_container.return_value = 0

        # Mock _build_base_image and _move_distro_file to avoid file operations
        with patch.object(self.builder, "_build_base_image"), patch.object(
            self.builder, "_move_distro_file"
        ):
            # Build all (which keeps artifacts uncompressed)
            self.builder.build_all()

        # Verify ComponentBuilder was instantiated with artifact_key_salt='uncompressed'
        # Check the first call (should be for kernel component)
        mock_component_builder_class.assert_called()
        call_kwargs = mock_component_builder_class.call_args.kwargs
        self.assertEqual(
            call_kwargs.get("artifact_key_salt"),
            "uncompressed",
            "ComponentBuilder should receive 'uncompressed' salt in full build mode",
        )

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
