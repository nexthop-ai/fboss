#!/usr/bin/env python3
"""
Build entry point for component builds inside the container.

This is the standard entry point for all component builds. It:
1. Discovers dependencies mounted at /dependencies/
2. Extracts tarballs if needed
3. Installs RPMs from dependencies
4. Executes the component build script

Usage:
    python3 build_entrypoint.py <build_script> [args...]

Example:
    python3 /workspace/fboss-image/distro_cli/lib/build_entrypoint.py /workspace/fboss-image/kernel/scripts/build.sh
"""

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Standard location where dependencies are mounted
DEPENDENCIES_DIR = Path("/dependencies")


def extract_tarball(tarball_path: Path, extract_dir: Path) -> None:
    """Extract a tarball to the specified directory using tar command.

    Args:
        tarball_path: Path to the tarball file
        extract_dir: Directory to extract to
    """
    logger.info(f"Extracting {tarball_path} to {extract_dir}")
    try:
        # Use tar command for better compression support (zstd) and multithreading
        cmd = ["tar", "-xf", str(tarball_path), "-C", str(extract_dir)]
        logger.info(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        logger.info(f"Successfully extracted {tarball_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract {tarball_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to extract {tarball_path}: {e}")
        raise


def find_rpms(directory: Path) -> list[Path]:
    """Find all RPM files in a directory (recursively).

    Args:
        directory: Directory to search

    Returns:
        List of paths to RPM files
    """
    rpms = list(directory.rglob("*.rpm"))
    logger.info(f"Found {len(rpms)} RPM(s) in {directory}")
    return rpms


def install_rpms(rpm_paths: list[Path]) -> None:
    """Install RPMs using dnf.

    Args:
        rpm_paths: List of paths to RPM files
    """
    if not rpm_paths:
        logger.info("No RPMs to install")
        return

    rpm_str_paths = [str(rpm) for rpm in rpm_paths]
    logger.info(
        f"Installing {len(rpm_paths)} RPM(s): {', '.join([rpm.name for rpm in rpm_paths])}"
    )

    cmd = ["dnf", "install", "-y", *rpm_str_paths]
    logger.info(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=False)
    logger.info("Successfully installed RPMs")


def discover_dependencies() -> list[Path]:
    """Discover all dependencies in the standard /dependencies directory.

    Returns:
        List of paths to dependency artifacts (files or directories)
    """
    if not DEPENDENCIES_DIR.exists():
        logger.info(f"No dependencies directory found at {DEPENDENCIES_DIR}")
        return []

    dependencies = []
    for dep_path in DEPENDENCIES_DIR.iterdir():
        if dep_path.name.startswith("."):
            # Skip hidden files/directories
            continue
        dependencies.append(dep_path)
        logger.info(f"Discovered dependency: {dep_path.name}")

    return dependencies


def process_dependency(dep_path: Path, temp_dir: Path) -> None:
    """Process a dependency: extract if tarball, then install RPMs.

    Args:
        dep_path: Path to the dependency (file or directory)
        temp_dir: Temporary directory for extraction
    """
    dep_name = dep_path.name
    logger.info(f"Processing dependency '{dep_name}' at {dep_path}")

    if not dep_path.exists():
        logger.warning(f"Dependency path does not exist: {dep_path}")
        return

    # Determine the directory to search for RPMs
    if dep_path.is_file():
        # It's a tarball - extract it
        extract_dir = temp_dir / dep_name
        extract_dir.mkdir(parents=True, exist_ok=True)
        extract_tarball(dep_path, extract_dir)
        search_dir = extract_dir
    else:
        # It's already a directory
        search_dir = dep_path

    # Find and install RPMs
    rpms = find_rpms(search_dir)
    if rpms:
        install_rpms(rpms)
    else:
        logger.info(f"No RPMs found in dependency '{dep_name}'")


def main():
    # Minimum required arguments: script name + build command
    min_args = 2
    if len(sys.argv) < min_args:
        logger.error("Usage: build_entrypoint.py <build_script> [args...]")
        logger.error(
            "Example: build_entrypoint.py /workspace/fboss-image/kernel/scripts/build.sh"
        )
        sys.exit(1)

    # Build command is everything after the script name
    build_command = sys.argv[1:]

    logger.info("=" * 60)
    logger.info("Dependency Installation and Build Entry Point")
    logger.info("=" * 60)

    # Create temporary directory for extractions
    with tempfile.TemporaryDirectory(prefix="dep-install-") as temp_dir:
        temp_path = Path(temp_dir)

        # Discover and process all dependencies
        dependencies = discover_dependencies()
        if dependencies:
            logger.info(f"Found {len(dependencies)} dependency/dependencies")
            for dep_path in dependencies:
                try:
                    process_dependency(dep_path, temp_path)
                except Exception as e:
                    logger.error(f"Failed to process dependency '{dep_path.name}': {e}")
                    sys.exit(1)
        else:
            logger.info("No dependencies found - proceeding with build")

        # Execute the build command
        logger.info("=" * 60)
        logger.info(f"Executing build: {' '.join(build_command)}")
        logger.info("=" * 60)
        try:
            result = subprocess.run(build_command, check=False)
            sys.exit(result.returncode)
        except Exception as e:
            logger.error(f"Failed to execute build command: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
