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

import unittest
from pathlib import Path

from distro_cli.lib.builder import ImageBuilder
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

    def test_build_all_stub(self):
        """Test build_all method (stub) - just verify builder structure"""
        # TODO: Implement full integration test with real Docker calls
        # For now, just verify the builder has the expected methods
        self.assertTrue(hasattr(self.builder, 'build_all'))
        self.assertTrue(callable(self.builder.build_all))

    def test_build_components_stub(self):
        """Test build_components method (stub)"""
        # Just verify it doesn't crash
        # When implemented, this should verify component-specific builds
        components = ['kernel', 'sai']
        self.builder.build_components(components)


if __name__ == '__main__':
    unittest.main()
