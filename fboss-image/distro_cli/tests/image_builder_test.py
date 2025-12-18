<<<<<<< HEAD
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
        self.test_dir = Path(__file__).parent
        self.manifest_path = self.test_dir / "dev_image.json"
        self.manifest = ImageManifest(self.manifest_path)
        self.builder = ImageBuilder(self.manifest)

    def test_builder_initialization(self):
        """Test that builder initializes correctly"""
        self.assertIsNotNone(self.builder)
        self.assertEqual(self.builder.manifest, self.manifest)

    @patch('distro_cli.builder.image_builder.run_container')
    @patch('distro_cli.builder.image_builder.build_fboss_builder_image')
    def test_build_all(self, mock_build_image, mock_run_container):
        """Test build_all method with mocked container execution"""
        # Mock successful container execution
        mock_run_container.return_value = 0

        # Mock the _move_distro_file method to avoid file operations
        with patch.object(self.builder, '_move_distro_file'):
            self.builder.build_all()

        # Verify Docker image build was called
        mock_build_image.assert_called_once()

        # Verify run_container was called multiple times:
        # - Once for each component with "execute" directive (fboss-platform-stack, sai, fboss-forwarding-stack)
        # - Once for the base image build script
        # Total: 4 calls
        self.assertEqual(mock_run_container.call_count, 4)

        # Verify the last call was for the base image build script
        last_call = mock_run_container.call_args_list[-1]
        command = last_call.kwargs['command']
        self.assertIn('/image_builder/bin/build_image_in_container.sh', ' '.join(command))

    @patch('distro_cli.builder.image_builder.run_container')
    def test_build_components(self, mock_run_container):
        """Test build_components method with mocked container execution"""
        # Mock successful container execution
        mock_run_container.return_value = 0

        # Request 'sai' and 'fboss-platform-stack' which both have execute commands
        components = ['sai', 'fboss-platform-stack']
        self.builder.build_components(components)

        # Verify run_container was called for each component with execute command
        # Both components have execute commands in dev_image.json
        self.assertEqual(mock_run_container.call_count, 2)

        # Verify commands are passed as lists (no shell wrapping)
        sai_call = mock_run_container.call_args_list[1]  # sai is second in COMPONENTS order
        command = sai_call.kwargs['command']
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], 'fboss_brcm_sai/build.sh')

    @patch('distro_cli.builder.image_builder.run_container')
    def test_build_component_not_found(self, mock_run_container):
        """Test building a component that doesn't exist in manifest"""
        with self.assertRaises(ComponentError) as cm:
            self.builder.build_components(['nonexistent_component'])

        # Verify error message
        self.assertIn('nonexistent_component', str(cm.exception))
        self.assertIn('not found', str(cm.exception))

        # run_container should not be called
        mock_run_container.assert_not_called()

    @patch('distro_cli.builder.image_builder.run_container')
    def test_build_component_execution_failure(self, mock_run_container):
        """Test handling of component build failure"""
        # Mock failed container execution
        mock_run_container.return_value = 1

        with self.assertRaises(BuildError) as cm:
            self.builder.build_components(['sai'])

        # Verify error message contains component name and exit code
        self.assertIn('sai', str(cm.exception))
        self.assertIn('exit code 1', str(cm.exception))

        # run_container should have been called once (for sai)
        mock_run_container.assert_called_once()


if __name__ == '__main__':
    unittest.main()
||||||| 449479b9e7
=======
#!/usr/bin/env python3

# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""
Unit tests for ImageBuilder class

NOTE: These are skeleton tests for stub implementations.
When builder is fully implemented, these tests should be expanded.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path to import the modules
test_dir = Path(__file__).parent
cli_dir = test_dir.parent
sys.path.insert(0, str(cli_dir))

from lib.builder import ImageBuilder
from lib.manifest import ImageManifest


class TestImageBuilder(unittest.TestCase):
    """Test ImageBuilder class"""

    def setUp(self):
        """Use the test manifest"""
        self.test_dir = Path(__file__).parent
        self.manifest_path = self.test_dir / "dev_image.json"
        self.manifest = ImageManifest(self.manifest_path)
        self.builder = ImageBuilder(self.manifest)

    def test_builder_initialization(self):
        """Test that builder initializes correctly"""
        self.assertIsNotNone(self.builder)
        self.assertEqual(self.builder.manifest, self.manifest)

    @patch("lib.builder.subprocess.run")
    @patch("lib.builder.Path.exists")
    @patch("lib.builder.shutil.move")
    def test_build_all_stub(self, _mock_move, mock_exists, mock_run):
        """Test build_all method (stub)"""
        # Mock the build script and output ISO existence
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # Just verify it doesn't crash
        # When implemented, this should verify actual build behavior
        self.builder.build_all()

    def test_build_components_stub(self):
        """Test build_components method (stub)"""
        # Just verify it doesn't crash
        # When implemented, this should verify component-specific builds
        components = ["kernel", "sai"]
        self.builder.build_components(components)


if __name__ == "__main__":
    unittest.main()
>>>>>>> 2e3f5259e0e7fb4791864e3939bdd38a408f7699
