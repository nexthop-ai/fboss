# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Path resolution utilities for FBOSS image builder."""

from pathlib import Path


def get_root_dir() -> Path:
    """Find the repository root directory.

    This works by walking up from the current file until we find
    the 'fboss-image' directory, then returning its parent.

    Additionally verifies that both 'fboss-image' and 'fboss' directories
    exist at the root to ensure we're in the correct repository structure.

    Returns:
        Path to repository root directory

    Raises:
        RuntimeError: If the root directory cannot be determined
    """
    current = Path(__file__).resolve()

    # Walk up the directory tree looking for fboss-image
    for parent in current.parents:
        if (parent / "fboss-image").is_dir() and (parent / "fboss").is_dir():
            return parent

    raise RuntimeError(
        f"Could not find repository root from {current}. "
        f"Expected to find 'fboss-image' and 'fboss' directories in parent path."
    )
