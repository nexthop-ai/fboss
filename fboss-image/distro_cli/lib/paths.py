# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Path resolution utilities for FBOSS image builder."""

from pathlib import Path


def get_root_dir(dir_name: str = "fboss-image") -> Path:
    """Find the root directory containing the specified directory.

    This works by walking up from the current file until we find
    the specified directory, then returning its parent.

    Args:
        dir_name: Name of the directory to search for (default: "fboss-image")

    Returns:
        Path to root directory (parent of dir_name)

    Raises:
        RuntimeError: If the root directory cannot be determined
    """
    current = Path(__file__).resolve()

    # Walk up the directory tree looking for dir_name
    for parent in current.parents:
        if (parent / dir_name).is_dir():
            return parent

    raise RuntimeError(
        f"Could not find root from {current}. "
        f"Expected to find '{dir_name}' directory in parent path."
    )
