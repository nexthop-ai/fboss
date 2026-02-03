#!/usr/bin/env python3

# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""
Unit tests for device commands

NOTE: These are skeleton tests for stub implementations.
When device commands are fully implemented, these tests will be expanded
to verify actual functionality.

These tests verify that:
1. Device command group exists and has expected subcommands
2. Commands can be called without crashing (stub behavior)
3. Context passing works correctly
"""

import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path

from distro_cli.cmds.device import (
    DISTRO_CONTAINER_NAME,
    getip_command,
    image_command,
    image_upstream_command,
    reprovision_command,
    setup_device_commands,
    ssh_command,
    update_command,
)
from distro_cli.lib.docker import container


class TestDeviceCommands(unittest.TestCase):
    """Test device command group and subcommands (stubs)"""

    @classmethod
    def setUpClass(cls):
        """Set up test container before all tests"""
        # Check if fboss_distro_infra image exists
        try:
            result = subprocess.run(
                ["docker", "images", "-q", "fboss_distro_infra"],
                capture_output=True,
                text=True,
                check=True,
            )
            if not result.stdout.strip():
                raise unittest.SkipTest(
                    "fboss_distro_infra Docker image not found. "
                    "Please build it with: cd fboss-image/distro_infra && ./build.sh"
                )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest("Docker not available or image not built")

        # Clean up any existing container with the same name
        if container.container_is_running(DISTRO_CONTAINER_NAME):
            container.stop_and_remove_container(DISTRO_CONTAINER_NAME)

        # Start the fboss-distro-infra container in background
        # Use a minimal command that keeps the container running
        exit_code = container.run_container(
            image="fboss_distro_infra",
            command=["sleep", "1"],
            ephemeral=False,
            name=DISTRO_CONTAINER_NAME,
            privileged=True,  # Required for network operations
        )

        if exit_code != 0:
            raise RuntimeError(f"Failed to start {DISTRO_CONTAINER_NAME} container")

    @classmethod
    def tearDownClass(cls):
        """Clean up test container after all tests"""
        if container.container_is_running(DISTRO_CONTAINER_NAME):
            container.stop_and_remove_container(DISTRO_CONTAINER_NAME)

    def setUp(self):
        """Set up test fixtures"""
        self.test_mac = "aa:bb:cc:dd:ee:ff"

        # Create a temporary manifest file for tests that need it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"test": "manifest"}')
            self.manifest_path = Path(f.name)

        # Create a temporary image file for tests that need it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".bin", delete=False) as f:
            f.write("fake image data")
            self.image_path = Path(f.name)

    def tearDown(self):
        """Clean up test fixtures"""
        self.manifest_path.unlink()
        self.image_path.unlink()

    def test_device_commands_exist(self):
        """Test that device commands exist"""
        self.assertTrue(callable(setup_device_commands))
        self.assertTrue(callable(image_upstream_command))
        self.assertTrue(callable(image_command))
        self.assertTrue(callable(reprovision_command))
        self.assertTrue(callable(update_command))
        self.assertTrue(callable(getip_command))
        self.assertTrue(callable(ssh_command))

    def test_image_upstream_stub(self):
        """Test image-upstream command (stub)"""
        args = argparse.Namespace(mac=self.test_mac, components=["kernel", "sai"])
        # Call command - just verify it doesn't crash
        image_upstream_command(args)

    def test_image_stub(self):
        """Test image command (stub)"""
        args = argparse.Namespace(mac=self.test_mac, image_path=str(self.image_path))
        # Call command - just verify it doesn't crash
        image_command(args)

    def test_reprovision_stub(self):
        """Test reprovision command (stub)"""
        args = argparse.Namespace(mac=self.test_mac)
        # Call command - just verify it doesn't crash
        reprovision_command(args)

    def test_update_stub(self):
        """Test update command (stub)"""
        args = argparse.Namespace(
            mac=self.test_mac,
            manifest=str(self.manifest_path),
            components=["kernel", "sai"],
        )
        # Call command - just verify it doesn't crash
        update_command(args)

    def test_getip_stub(self):
        """Test getip command (stub)"""
        args = argparse.Namespace(mac=self.test_mac, interface=None)
        # Call command - just verify it doesn't crash
        getip_command(args)

    def test_ssh_stub(self):
        """Test ssh command (stub)"""
        args = argparse.Namespace(mac=self.test_mac)
        # Call command - just verify it doesn't crash
        ssh_command(args)


if __name__ == "__main__":
    unittest.main()
