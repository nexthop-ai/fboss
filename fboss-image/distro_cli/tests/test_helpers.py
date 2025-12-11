# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Test helper utilities."""

import logging

from distro_cli.lib.docker.image import build_fboss_builder_image

logger = logging.getLogger(__name__)

def ensure_test_docker_image():
    """Ensure fboss_builder Docker image is available for tests.

    Utilize the production build_fboss_builder_image() to ensure
    that the fboss builder image is available.

    Raises:
        RuntimeError: If image is not available.
    """
    build_fboss_builder_image()
