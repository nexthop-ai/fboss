# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Artifact storage with file caching for FBOSS image builder."""

import hashlib
import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from distro_cli.lib.docker.image import get_root_dir

from .exceptions import ArtifactError

logger = logging.getLogger(__name__)


class ArtifactStore:
    """Artifact storage with external cache evaluation.

    get() delegates cache evaluation and related fetching to a caller-provided function.
    store() persists data and metadata files separately in storage subdirectories.
    """

    def __init__(self, store_dir: Path | None = None):
        """Initialize artifact store.

        Args:
            store_dir: Directory to use for storage. Defaults to .artifacts in distro_cli directory.
        """
        if store_dir is None:
            store_dir = get_root_dir() / "fboss-image" / "distro_cli" / ".artifacts"
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Artifact store initialized at: {self.store_dir}")

    def get(
        self,
        store_key: str,
        fetch_fn: Callable[[list[Path], list[Path]], tuple[bool, list[Path], list[Path]]]
    ) -> tuple[list[Path], list[Path]]:
        """Retrieve artifact files using caller-provided fetch function.

        Args:
            store_key: Unique identifier for the artifact
            fetch_fn: Evaluates stored files and returns (store_hit, data_files, metadata_files)

        Returns:
            Tuple of (data_files, metadata_files)
        """
        store_subdir = self._get_store_subdir(store_key)
        stored_data_files = self._get_stored_files_in_dir(store_subdir / "data")
        stored_metadata_files = self._get_stored_files_in_dir(store_subdir / "metadata")

        logger.info(f"Executing fetch function for: {store_key}")
        store_hit, new_data_files, new_metadata_files = fetch_fn(stored_data_files, stored_metadata_files)

        if store_hit:
            logger.info(f"Store hit: {store_key}")
            return (stored_data_files, stored_metadata_files)

        logger.info(f"Store miss: {store_key}, storing new files")
        return self.store(store_key, new_data_files, new_metadata_files)

    def _get_store_subdir(self, store_key: str) -> Path:
        """Get the storage subdirectory for a given store key.

        Args:
            store_key: Store key for the artifact

        Returns:
            Path to the storage subdirectory
        """
        # Use full SHA256 hash to create a directory name
        key_hash = hashlib.sha256(store_key.encode()).hexdigest()
        return self.store_dir / key_hash

    def _get_stored_files_in_dir(self, dir_path: Path) -> list[Path]:
        """Get files from a directory.

        Args:
            dir_path: Directory path

        Returns:
            List of file paths
        """
        if not dir_path.exists():
            return []
        return [f for f in dir_path.iterdir() if f.is_file()]

    def store(
        self,
        store_key: str,
        data_files: list[Path],
        metadata_files: list[Path]
    ) -> tuple[list[Path], list[Path]]:
        """Store data and metadata files in the storage.

        Files/directories are copied to store_subdir/data/ and store_subdir/metadata/.
        If a path is a file, it's copied directly.
        If a path is a directory, all its contents are copied.

        Args:
            store_key: Store key for the artifact
            data_files: List of data file/directory paths to store
            metadata_files: List of metadata file/directory paths to store

        Returns:
            Tuple of (stored_data_files, stored_metadata_files)
        """
        store_subdir = self._get_store_subdir(store_key)
        data_dir = store_subdir / "data"
        metadata_dir = store_subdir / "metadata"

        # Store data files
        if data_files:
            data_dir.mkdir(parents=True, exist_ok=True)
            for file_path in data_files:
                self._copy_to_dir(file_path, data_dir)
            logger.info(f"Stored {len(data_files)} data file(s): {store_key}")

        # Store metadata files
        if metadata_files:
            metadata_dir.mkdir(parents=True, exist_ok=True)
            for file_path in metadata_files:
                self._copy_to_dir(file_path, metadata_dir)
            logger.info(f"Stored {len(metadata_files)} metadata file(s): {store_key}")

        # Return all stored files
        return (
            self._get_stored_files_in_dir(data_dir),
            self._get_stored_files_in_dir(metadata_dir)
        )

    def _copy_to_dir(self, source: Path, dest_dir: Path) -> None:
        """Copy a file or directory contents to destination directory.

        Args:
            source: Source file or directory
            dest_dir: Destination directory
        """
        if source.is_dir():
            shutil.copytree(source, dest_dir, dirs_exist_ok=True)
        else:
            shutil.copy2(source, dest_dir / source.name)

    def invalidate(self, store_key: str) -> None:
        """Remove an artifact from the store.

        Args:
            store_key: Store key for the artifact to remove
        """
        store_subdir = self._get_store_subdir(store_key)
        if store_subdir.exists():
            shutil.rmtree(store_subdir)
            logger.info(f"Invalidated store entry: {store_key}")

    def clear(self) -> None:
        """Clear all stored artifacts."""
        if self.store_dir.exists():
            shutil.rmtree(self.store_dir)
            self.store_dir.mkdir(parents=True, exist_ok=True)
            logger.info("All stored artifacts cleared")


def find_artifact_in_dir(output_dir: Path, pattern: str, component_name: str = "Component") -> Path:
    """Find a single artifact matching a glob pattern in a directory.

    Args:
        output_dir: Directory to search in
        pattern: Glob pattern to match (e.g., "kernel-*.rpms.tar.gz")
        component_name: Name of component for error messages

    Returns:
        Path to the found artifact

    Raises:
        ArtifactError: If no artifacts found

    Note:
        If multiple artifacts match, returns the first one with a warning.
    """
    artifacts = list(output_dir.glob(pattern))

    if not artifacts:
        raise ArtifactError(f"{component_name} build output not found in: {output_dir} (pattern: {pattern})")

    if len(artifacts) > 1:
        logger.warning(f"Multiple artifacts found matching '{pattern}', using first: {artifacts[0]}")

    artifact_path = artifacts[0]
    logger.info(f"Found {component_name} artifact: {artifact_path}")
    return artifact_path
