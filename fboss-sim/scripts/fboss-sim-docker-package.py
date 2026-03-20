#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.

"""
Package fboss-sim build artifacts into a minimal runtime Docker image.

This script packages the build artifacts from fboss_bins.tar.zst into a lightweight
runtime image suitable for deployment and testing.

Prerequisites:
- Run fboss/oss/scripts/package-fboss.py first to create fboss_bins.tar.zst:
    ./fboss/oss/scripts/package-fboss.py --scratch-path /var/FBOSS/tmp_bld_dir/ --copy-root-libs --compress

  This creates fboss_bins.tar.zst containing:
    ├── bin/          (all FBOSS binaries including agents, CLI tools, tests)
    ├── lib/          (shared libraries discovered via ldd)
    └── share/        (config files, test configs, run scripts)

The runtime image:
- Contains only essential runtime dependencies (systemd, iproute, jemalloc)
- Includes FBOSS agents and CLI tools
- Supports both monolithic and split agent modes
- Uses jemalloc to prevent memory corruption in fake SAI
- Size: ~1.2 GB
"""

import getpass
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

USERNAME = getpass.getuser()
DEFAULT_IMAGE_NAME = f"fboss_sim_runtime_{USERNAME}"


def get_repo_path():
    """Get the repository root path (~/nh/fboss)"""
    # Use absolute path to handle cases where __file__ is relative
    scripts_path = os.path.dirname(os.path.abspath(__file__))
    # Go up 2 levels: scripts -> fboss-sim -> fboss (which is ~/nh/fboss)
    return Path(scripts_path).parent.parent.absolute()


REQUIRED_BINARIES = [
    "wedge_agent-fake",
    "fboss_sw_agent",
    "fboss_hw_agent-fake",
    "fboss2",
    "fboss2-dev",
    "cli_test",
    "setup_fboss_env",
]


def extract_tarball(tarball: Path) -> Path:
    """Extract tarball to /tmp and return extraction directory"""
    temp_extract_dir = Path(tempfile.mkdtemp(prefix="fboss_extract_"))
    print(f"\n📦 Extracting tarball to {temp_extract_dir}...")

    cmd = ["tar", "-xf", str(tarball), "-C", str(temp_extract_dir)]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ❌ Failed to extract tarball: {result.stderr}")
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        sys.exit(1)

    print("  ✓ Extracted successfully")
    return temp_extract_dir


def verify_binaries(temp_extract_dir: Path) -> None:
    """Verify all required binaries are present"""
    print("\n🔍 Verifying required binaries...")
    missing_binaries = []
    for binary in REQUIRED_BINARIES:
        if not (temp_extract_dir / "bin" / binary).exists():
            missing_binaries.append(binary)

    if missing_binaries:
        print("❌ Error: Missing required binaries in extracted tarball:")
        for binary in missing_binaries:
            print(f"   - {binary}")
        print("\n   The tarball may be incomplete or from an incorrect build.")
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        sys.exit(1)

    print(f"  ✓ All {len(REQUIRED_BINARIES)} required binaries present")


def copy_artifacts(temp_extract_dir: Path, build_dir: Path) -> None:
    """Copy required artifacts to build directory"""
    print(f"\n📁 Copying artifacts to Docker build context: {build_dir}")

    # Remove existing build_dir if it exists
    if build_dir.exists():
        print(f"  → Removing existing {build_dir}")
        shutil.rmtree(build_dir)

    # Create directory structure
    (build_dir / "bin").mkdir(parents=True, exist_ok=True)
    (build_dir / "lib").mkdir(parents=True, exist_ok=True)
    (build_dir / "share").mkdir(parents=True, exist_ok=True)

    # Copy only the 7 required binaries
    print(f"  → Copying {len(REQUIRED_BINARIES)} required binaries...")
    for binary in REQUIRED_BINARIES:
        src = temp_extract_dir / "bin" / binary
        dst = build_dir / "bin" / binary
        shutil.copy2(src, dst)
        print(f"    ✓ {binary}")

    # Copy all libraries from the tarball
    print("\n  → Copying libraries from tarball...")
    if (temp_extract_dir / "lib").exists():
        lib_files = list((temp_extract_dir / "lib").iterdir())
        lib_count = len(lib_files)
        if lib_count > 0:
            shutil.copytree(
                temp_extract_dir / "lib", build_dir / "lib", dirs_exist_ok=True
            )
            print(f"    ✓ Copied {lib_count} libraries")
        else:
            print("    ⚠ Warning: No libraries found in tarball!")
            print(
                "    ⚠ This likely means package-fboss.py couldn't resolve dependencies."
            )
            print(
                "    ⚠ The Docker image will be missing shared libraries and won't work!"
            )

    # Copy share/ directory (if exists)
    if (temp_extract_dir / "share").exists():
        print("  → Copying shared files...")
        shutil.copytree(
            temp_extract_dir / "share", build_dir / "share", dirs_exist_ok=True
        )


def verify_and_extract_tarball(repo_path: Path):
    """Extract tarball to /tmp, verify, then copy needed files to tmp_build_dir"""
    print("🔍 Verifying build artifacts...")

    tarball = repo_path / ".build_dir" / "fboss_bins.tar.zst"

    if not tarball.exists():
        print("❌ Error: fboss_bins.tar.zst not found in .build_dir/")
        print(f"   Expected location: {tarball}")
        print("\n   Please run package-fboss.py first:")
        print("   docker exec FBOSS_build_${USER} bash -c \\")
        print("     'cd /var/FBOSS/fboss && \\")
        print("      ./fboss/oss/scripts/package-fboss.py \\")
        print("        --scratch-path /var/FBOSS/tmp_bld_dir/ \\")
        print("        --copy-root-libs \\")
        print("        --compress'")
        print("\n   Then copy the tarball to host:")
        print("   docker cp FBOSS_build_${USER}:/var/FBOSS/tmp_bld_dir/fboss_bins.tar.zst .build_dir/")
        sys.exit(1)

    print(f"  ✓ Found tarball: {tarball}")

    # Extract tarball
    temp_extract_dir = extract_tarball(tarball)

    # Debug: Show what was extracted
    print("\n🔍 Inspecting extracted contents...")
    for item in temp_extract_dir.iterdir():
        if item.is_dir():
            item_count = len(list(item.iterdir()))
            print(f"  → {item.name}/: {item_count} items")
        else:
            print(f"  → {item.name}")

    # Verify required binaries
    verify_binaries(temp_extract_dir)

    # Copy artifacts to build directory
    build_dir = repo_path / "tmp_build_dir"
    copy_artifacts(temp_extract_dir, build_dir)

    # Clean up temporary extraction directory
    print("\n🧹 Cleaning up temporary extraction directory...")
    shutil.rmtree(temp_extract_dir, ignore_errors=True)

    print(f"  ✓ Build artifacts ready in {build_dir}")

    return build_dir


def build_runtime_image(repo_path: Path):
    """Build the runtime Docker image"""
    print("\n🔨 Building fboss-sim runtime image...")

    docker_dir = repo_path / "fboss-sim" / "docker"
    dockerfile = docker_dir / "Dockerfile.runtime"

    if not dockerfile.exists():
        print(f"  ❌ Error: Dockerfile not found: {dockerfile}")
        sys.exit(1)

    print(f"  Dockerfile: {dockerfile}")
    print(f"  Build context: {repo_path}")
    print("  Build artifacts: tmp_build_dir/ (in build context)")

    image_tag = f"{DEFAULT_IMAGE_NAME}:latest"
    print(f"  Image tag: {image_tag}")

    cmd = [
        "docker",
        "build",
        "-f",
        str(dockerfile),
        "-t",
        image_tag,
        str(repo_path),  # Build context is repo root
    ]

    print("\n  → Running docker build...")
    result = subprocess.run(cmd, check=False, capture_output=False)

    if result.returncode == 0:
        print("\n  ✓ Image built successfully")
    else:
        print(f"\n  ✗ Build failed with exit code {result.returncode}")

    return result.returncode, image_tag


def main():
    print("=" * 60)
    print("fboss-sim Runtime Image Builder")
    print("=" * 60)

    repo_path = get_repo_path()
    print(f"Repository: {repo_path}\n")

    # Verify tarball exists and extract to .build_dir
    verify_and_extract_tarball(repo_path)

    # Build runtime image
    ret, image_tag = build_runtime_image(repo_path)

    if ret == 0:
        print(f"\n{'=' * 60}")
        print("✅ Runtime image created successfully!")
        print(f"{'=' * 60}")
        print(f"\nImage: {image_tag}")
        print("\nNext steps:")
        print("  • Run container: ./fboss-sim/scripts/fboss-sim-docker-run.py")
        print(
            f"  • Or manually:   docker run -d --privileged --name fboss_sim_runtime_{getpass.getuser()} {image_tag}"
        )
        print()
    else:
        print("\n❌ Failed to create runtime image")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
