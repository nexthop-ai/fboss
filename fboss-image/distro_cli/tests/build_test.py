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


class TestBuildCommand(unittest.TestCase):
    """Test build command"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(__file__).parent
        self.manifest_path = self.test_dir / "dev_image.json"

    def test_build_command_exists(self):
        """Test that build command exists"""
        self.assertTrue(callable(build_command))
        self.assertTrue(callable(setup_build_command))

    @patch('distro_cli.lib.builder.shutil.move')
    @patch('distro_cli.lib.builder.Path.exists')
    @patch('distro_cli.lib.builder.build_fboss_builder_image')
    @patch('distro_cli.lib.builder.run_container')
    def test_build_all_stub(self, mock_run_container, mock_build_image, mock_exists, mock_move):
        """Test build command with no components (build all)"""
        # Mock Docker operations to avoid actual builds
        mock_build_image.return_value = None
        mock_run_container.return_value = 0
        mock_exists.return_value = True
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

    def test_build_specific_components_stub(self):
        """Test build command with specific components"""
        # Create mock args object
        args = argparse.Namespace(
            manifest=str(self.manifest_path),
            components=['kernel', 'sai']
        )
        # Call build command with components - just verify it doesn't crash
        # When implemented, should verify component-specific builds
        build_command(args)


if __name__ == '__main__':
    unittest.main()
