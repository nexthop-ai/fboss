#!/usr/bin/env python3

# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Test SAI build functionality."""

import unittest
from pathlib import Path

import pytest
from distro_cli.builder.image_builder import ImageBuilder
from distro_cli.lib.manifest import ImageManifest
from distro_cli.tests.test_helpers import ensure_test_docker_image


class TestSAIBuildE2E(unittest.TestCase):
    """End-to-end test for SAI build.

    This test is marked as skipped by default because:
    1. It requires the SAI source code to be available (location determined by the execute path in the manifest)
    2. It takes a long time to run (60+ minutes)
    3. It requires significant disk space

    To run manually:
    python3 -m pytest distro_cli/tests/sai_build_test.py::TestSAIBuildE2E::test_real_sai_build -v -s
    """

    @classmethod
    def setUpClass(cls):
        """Ensure fboss_builder image exists before running tests."""
        ensure_test_docker_image()

    @unittest.skip("E2E test - run manually")
    @pytest.mark.e2e
    def test_real_sai_build(self):
        """Test real SAI build with actual build script.

        This test verifies that:
        1. Kernel is built first as a dependency of SAI
        2. Kernel RPMs are extracted and mounted for SAI build
        3. FBOSS_PRIVATE_KERNEL_RPMS_DIR environment variable is set
        4. The SAI build script can use the kernel RPMs
        5. The SAI build produces the expected artifact (sai-devel.tar)

        The test uses get_git_dir to find the SAI SDK directory based on the execute path
        in the manifest, so it works regardless of where the SDK is located on the filesystem
        or what it's named.

        To run manually (outside bazel to avoid read-only filesystem issues):
        PYTHONPATH=fboss-image timeout 3600 python3 -m pytest \
            fboss-image/distro_cli/tests/sai_build_test.py::TestSAIBuildE2E::test_real_sai_build -v -s
        Or to run all e2e tests:
        python3 -m pytest -m e2e -v -s

        Note: Use 60-minute timeout (3600 seconds) as the SAI build takes ~20 minutes.
        """
        # The manifest specifies the execute path (e.g., "broadcom-sai-sdk/build_fboss_sai.sh")
        # get_git_dir finds the git repository root
        # No hardcoded paths needed

        # Use the test manifest
        test_manifest_path = Path(__file__).parent / "data" / "test-sai-execute.json"
        self.assertTrue(
            test_manifest_path.exists(),
            f"Test manifest not found: {test_manifest_path}",
        )

        # Load manifest
        manifest = ImageManifest(test_manifest_path)

        # Use ImageBuilder to build SAI (which will automatically build kernel dependency)
        builder = ImageBuilder(manifest)

        # Build SAI component (kernel will be built automatically as a dependency)
        builder.build_components(["sai"])

        # Verify SAI artifact was created
        self.assertIn(
            "sai",
            builder.component_artifacts,
            "SAI artifact not found in component_artifacts",
        )
        result = builder.component_artifacts["sai"]

        # Verify kernel was also built as a dependency
        self.assertIn(
            "kernel",
            builder.component_artifacts,
            "Kernel artifact not found (should be built as dependency)",
        )

        # Verify result
        self.assertTrue(result.exists(), f"SAI tarball not found: {result}")
        self.assertTrue(
            result.name.endswith(".tar"), f"Expected .tar, got: {result.name}"
        )
        self.assertGreater(
            result.stat().st_size, 1024 * 1024, "Tarball seems too small"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
