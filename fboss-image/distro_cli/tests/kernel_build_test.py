"""Test kernel build functionality with Docker infrastructure."""

import unittest
from pathlib import Path

import pytest
from distro_cli.builder.component import ComponentBuilder
from distro_cli.lib.artifact import ArtifactStore
from distro_cli.lib.constants import FBOSS_BUILDER_IMAGE
from distro_cli.lib.docker.container import run_container
from distro_cli.lib.manifest import ImageManifest
from distro_cli.tests.test_helpers import ensure_test_docker_image, enter_tempdir


class TestDockerInfrastructure(unittest.TestCase):
    """Test Docker infrastructure for building."""

    @classmethod
    def setUpClass(cls):
        """Ensure fboss_builder image exists before running tests."""
        ensure_test_docker_image()

    def test_simple_container_execution(self):
        """Test running a simple command in a container."""
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE, command=["echo", "hello world"], ephemeral=True
        )
        self.assertEqual(exit_code, 0)

    def test_container_with_volume_mount(self):
        """Test container with volume mount - simulates build output."""
        with enter_tempdir("volume_test_") as tmpdir_path:
            output_file = tmpdir_path / "build_output.txt"

            # Run container that writes to mounted volume (simulates build)
            exit_code = run_container(
                image=FBOSS_BUILDER_IMAGE,
                command=[
                    "sh",
                    "-c",
                    "echo 'build artifact' > /output/build_output.txt",
                ],
                volumes={tmpdir_path: Path("/output")},
                ephemeral=True,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_text().strip(), "build artifact")

    def test_container_with_env_vars(self):
        """Test container with environment variables."""
        with enter_tempdir("env_test_") as tmpdir_path:
            output_file = tmpdir_path / "env_output.txt"

            # Run container that uses env var
            exit_code = run_container(
                image=FBOSS_BUILDER_IMAGE,
                command=["sh", "-c", "echo $BUILD_VERSION > /output/env_output.txt"],
                volumes={tmpdir_path: Path("/output")},
                env={"BUILD_VERSION": "6.11.1"},
                ephemeral=True,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.read_text().strip(), "6.11.1")

    def test_container_with_working_dir(self):
        """Test container with custom working directory."""
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE,
            command=["pwd"],
            working_dir="/tmp",
            ephemeral=True,
        )
        self.assertEqual(exit_code, 0)

    def test_container_failure_returns_nonzero(self):
        """Test that container failures return non-zero exit code."""
        exit_code = run_container(
            image=FBOSS_BUILDER_IMAGE, command=["sh", "-c", "exit 42"], ephemeral=True
        )
        self.assertEqual(exit_code, 42)


class TestKernelBuildE2E(unittest.TestCase):
    """End-to-end test for actual kernel build."""

    @classmethod
    def setUpClass(cls):
        """Ensure fboss_builder image exists before running tests."""
        ensure_test_docker_image()

    @unittest.skip("E2E test - run manually, takes ~10 minutes")
    @pytest.mark.e2e
    def test_real_kernel_build(self):
        """E2E test: Build kernel

        This test verifies that the kernel build produces a .tar artifact.

        To run:
        python3 -m pytest distro_cli/tests/kernel_build_test.py::TestKernelBuildE2E::\
test_real_kernel_build -v -s  # noqa: E501
        """
        # Selectively delete the specific artifact if present in store
        store = ArtifactStore()
        store_dir = store.store_dir / "kernel"
        if store_dir.exists():
            # Delete any kernel-*.rpms.tar files
            for artifact in store_dir.glob("kernel-*.rpms.tar"):
                # Skip .tar.zst files - only delete plain .tar
                if not artifact.name.endswith(".tar.zst"):
                    artifact.unlink()

        # Use the test manifest
        test_manifest_path = Path(__file__).parent / "data" / "test-kernel-execute.json"
        self.assertTrue(
            test_manifest_path.exists(),
            f"Test manifest not found: {test_manifest_path}",
        )

        # Load manifest
        manifest = ImageManifest(test_manifest_path)

        # Get kernel component data
        kernel_data = manifest.get_component("kernel")

        # Build kernel
        builder = ComponentBuilder(
            component_name="kernel",
            component_data=kernel_data,
            manifest_dir=manifest.manifest_dir,
            store=store,
            artifact_pattern="kernel-*.rpms.tar",
        )
        result = builder.build()

        # Verify result
        self.assertTrue(result.exists(), f"Kernel tarball not found: {result}")
        self.assertGreater(
            result.stat().st_size, 1024 * 1024, "Tarball seems too small"
        )

        # Verify the artifact to be .tar
        self.assertTrue(
            result.name.endswith(".tar"),
            f"Expected .tar, got: {result.name}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
