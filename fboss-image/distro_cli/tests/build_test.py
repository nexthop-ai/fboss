#!/usr/bin/env python3

# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""
Unit tests for build command

NOTE: These are skeleton tests for stub implementations.
When build command is fully implemented, these tests should be expanded.
"""

import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from distro_cli.cmds.build import build_command, setup_build_command
from distro_cli.lib.docker.image import get_root_dir
from distro_cli.lib.manifest import ImageManifest
from distro_cli.tests.test_helpers import ensure_test_docker_image


class TestBuildCommand(unittest.TestCase):
    """Test build command"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(__file__).parent
        self.manifest_path = self.test_dir / "dev_image.json"
        ensure_test_docker_image()

    def test_build_command_exists(self):
        """Test that build command exists"""
        self.assertTrue(callable(build_command))
        self.assertTrue(callable(setup_build_command))

    @patch('distro_cli.builder.image_builder.shutil.move')
    @patch('distro_cli.builder.image_builder.find_artifact_in_dir')
    @patch('distro_cli.builder.image_builder.build_fboss_builder_image')
    @patch('distro_cli.builder.image_builder.run_container')
    def test_build_all_stub(self, mock_run_container, mock_build_image, mock_exists, mock_move):
        """Test build command with no components (build all)"""
        # Mock Docker operations to avoid actual builds
        mock_build_image.return_value = None
        mock_run_container.return_value = 0
        mock_exists.return_value = Path("/fake/output.iso")
        mock_move.return_value = None

        # Create mock args object
        args = argparse.Namespace(
            manifest=str(self.manifest_path),
            components=[]
        )
        build_command(args)

        # Verify Docker image build was called
        mock_build_image.assert_called_once()
        # Verify container was run
        self.assertTrue(mock_run_container.called)

    def test_build_components(self):
        """Test build command with specific components"""
        manifest_path = self.test_dir / "echo.json"
        args = argparse.Namespace(
            manifest=str(manifest_path),
            components=['kernel']
        )

        # Load manifest to extract expected output file from execute command
        manifest = ImageManifest(manifest_path)
        execute_cmd = manifest.get_component("kernel")["execute"]
        # Execute command is now a list like ["sh", "-c", "echo 'test' > /image_builder/kernel-component.output"]
        # Extract output filename from the shell command (last element of the list)
        shell_cmd = execute_cmd[-1]  # Get the actual command string
        output_file = shell_cmd.split(">")[1].strip().split()[0].split("/")[-1]

        build_command(args)

        # Verify the output file was created
        root_dir = get_root_dir()
        output_path = root_dir / "fboss-image" / "image_builder" / output_file
        self.assertTrue(output_path.exists(), f"Expected output file not found: {output_path}")

if __name__ == '__main__':
    unittest.main()
