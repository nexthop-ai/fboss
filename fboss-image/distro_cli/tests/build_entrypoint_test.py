# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Test build_entrypoint.py behavior."""

import unittest
from pathlib import Path

from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.paths import get_root_dir
from distro_cli.tests.test_helpers import ensure_test_docker_image, sandbox_tempdir


class TestBuildEntrypoint(unittest.TestCase):
    """Test build_entrypoint.py as universal build entry point."""

    @classmethod
    def setUpClass(cls):
        """Ensure fboss_builder image exists before running tests."""
        ensure_test_docker_image()

    def test_entrypoint_without_dependencies(self):
        """Test build_entrypoint.py executes build command when no dependencies exist."""
        with sandbox_tempdir("entrypoint_no_deps_") as tmpdir_path:
            output_file = tmpdir_path / "build_output.txt"

            # Mount workspace (contains build_entrypoint.py)
            # No /dependencies mount - simulates build without dependencies
            exit_code = run_container(
                image=FBOSS_BUILDER_IMAGE,
                command=[
                    "python3",
                    "/workspace/fboss-image/distro_cli/lib/build_entrypoint.py",
                    "sh",
                    "-c",
                    "echo 'build completed' > /output/build_output.txt",
                ],
                volumes={
                    get_root_dir(): Path("/workspace"),  # Mount repo root
                    tmpdir_path: Path("/output"),
                },
                ephemeral=True,
            )

            self.assertEqual(exit_code, 0, "Build should succeed without dependencies")
            self.assertTrue(output_file.exists(), "Build output should be created")
            self.assertEqual(output_file.read_text().strip(), "build completed")

    def test_entrypoint_with_empty_dependencies(self):
        """Test build_entrypoint.py handles empty /dependencies directory gracefully."""
        with sandbox_tempdir("entrypoint_empty_deps_") as tmpdir_path:
            output_file = tmpdir_path / "build_output.txt"
            deps_dir = tmpdir_path / "deps"
            deps_dir.mkdir(exist_ok=True)

            # Mount empty /dependencies directory
            exit_code = run_container(
                image=FBOSS_BUILDER_IMAGE,
                command=[
                    "python3",
                    "/workspace/fboss-image/distro_cli/lib/build_entrypoint.py",
                    "sh",
                    "-c",
                    "echo 'build with empty deps' > /output/build_output.txt",
                ],
                volumes={
                    get_root_dir(): Path("/workspace"),
                    tmpdir_path: Path("/output"),
                    deps_dir: Path("/dependencies"),
                },
                ephemeral=True,
            )

            self.assertEqual(
                exit_code, 0, "Build should succeed with empty dependencies"
            )
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_text().strip(), "build with empty deps")


if __name__ == "__main__":
    unittest.main(verbosity=2)
