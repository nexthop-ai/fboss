#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.

"""
Package fboss-sim build artifacts into a minimal runtime Docker image.

This script collects FBOSS binaries directly from the build output directory
(.build_dir/build/fboss/), resolves their shared library dependencies via ldd,
and copies everything into a Docker build context for the runtime image.

Prerequisites:
- Build FBOSS with SAI_IMPL=fake (binaries will be in .build_dir/build/fboss/)

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
from pathlib import Path

USERNAME = getpass.getuser()
DEFAULT_IMAGE_NAME = f"fboss_sim_runtime_{USERNAME}"
BUILD_CONTAINER_NAME = f"FBOSS_build_{USERNAME}"
CONTAINER_REPO_PATH = "/var/FBOSS/fboss"  # repo mount point inside the build container

REQUIRED_BINARIES = [
    "wedge_agent-fake",
    "fboss_sw_agent",
    "fboss_hw_agent-fake",
    "fboss2",
    "fboss2-dev",
    "fboss2_integration_test",
]

# Libraries to exclude from collection — these are provided by the base OS image
# (CentOS Stream 9) and must NOT be overridden with host versions (Ubuntu).
# Mixing glibc-family libs across OS versions causes GLIBC_ABI_* version errors.
EXCLUDE_LIB_PATTERNS = [
    "libc.so",        # glibc core
    "libresolv.so",   # glibc DNS resolver
    "libdl.so",       # glibc dynamic linking
    "libpthread.so",  # glibc pthreads (merged into libc on glibc 2.34+)
    "libm.so",        # glibc math
    "librt.so",       # glibc POSIX real-time
    "libutil.so",     # glibc login utilities
    "libnss_",        # glibc name service switch modules
    "libgcc_s.so",    # GCC runtime
    "libstdc++.so",   # GCC C++ runtime
    "libsystemd.so",  # systemd (provided by container's systemd package)
]


def get_repo_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_build_dir(repo_path: Path) -> Path:
    """Get the FBOSS build output directory."""
    return repo_path / ".build_dir" / "build" / "fboss"


def get_installed_dir(repo_path: Path) -> Path:
    """Get the getdeps installed directory (contains dependency libs)."""
    return repo_path / ".build_dir" / "installed"


def verify_binaries(build_dir: Path) -> None:
    """Verify all required binaries are present in the build directory."""
    print("\n🔍 Verifying required binaries...")
    missing = []
    for binary in REQUIRED_BINARIES:
        if not (build_dir / binary).exists():
            missing.append(binary)

    if missing:
        print("❌ Error: Missing required binaries in build directory:")
        for b in missing:
            print(f"   - {b}")
        print(f"\n   Build directory: {build_dir}")
        print("   Please build FBOSS first with SAI_IMPL=fake")
        sys.exit(1)

    print(f"  ✓ All {len(REQUIRED_BINARIES)} required binaries present")


def get_lib_search_paths(installed_dir: Path) -> list[str]:
    """Find all lib/ and lib64/ directories under the getdeps installed dir.

    Mirrors package-fboss.py's _update_ld_library_path logic.
    """
    paths = []
    if not installed_dir.exists():
        return paths
    result = subprocess.run(
        ["find", str(installed_dir), "-type", "d", "-regex", r".*/\(lib\|lib64\)"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        paths = [p for p in result.stdout.strip().splitlines() if p]
    return paths


def resolve_dependencies(binary_path: Path, lib_search_paths: list[str]) -> set[str]:
    """Use ldd to find shared library dependencies for a binary."""
    dependencies = set()

    # Check it's actually an ELF binary
    try:
        output = subprocess.check_output(["file", str(binary_path)])
        if b"executable" not in output and b"shared object" not in output:
            return dependencies
    except subprocess.CalledProcessError:
        return dependencies

    # Set up LD_LIBRARY_PATH so ldd can find libs from the build
    env = os.environ.copy()
    extra_paths = ":".join(lib_search_paths)
    if env.get("LD_LIBRARY_PATH"):
        env["LD_LIBRARY_PATH"] = f"{extra_paths}:{env['LD_LIBRARY_PATH']}"
    else:
        env["LD_LIBRARY_PATH"] = extra_paths

    try:
        output = subprocess.check_output(
            ["ldd", str(binary_path)], env=env, stderr=subprocess.DEVNULL
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        print(f"  ⚠ Could not run ldd on {binary_path.name}")
        return dependencies

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # Parse ldd output:
        #   libfoo.so => /path/to/libfoo.so (0x...)
        #   /lib64/ld-linux-x86-64.so.2 (0x...)
        parts = line.split("=>")
        if len(parts) > 1:
            lib_path = parts[1].split("(")[0].strip()
        else:
            lib_path = parts[0].split("(")[0].strip()

        if not lib_path or lib_path == "not found":
            continue

        if any(pattern in lib_path for pattern in EXCLUDE_LIB_PATTERNS):
            continue

        # Include libs from installed dir and /lib*/ (system libs needed in container)
        if os.path.isfile(lib_path):
            dependencies.add(lib_path)

    return dependencies


def copy_artifacts(
    repo_path: Path,
    build_dir: Path,
    installed_dir: Path,
    dest_dir: Path,
) -> None:
    """Copy binaries, libraries, and configs to the Docker build context."""
    print(f"\n📁 Copying artifacts to Docker build context: {dest_dir}")

    if dest_dir.exists():
        print(f"  → Removing existing {dest_dir}")
        shutil.rmtree(dest_dir)

    bin_dir = dest_dir / "bin"
    lib_dir = dest_dir / "lib"
    share_dir = dest_dir / "share"
    for d in (bin_dir, lib_dir, share_dir):
        d.mkdir(parents=True)

    # 1. Copy required binaries
    print(f"\n  → Copying {len(REQUIRED_BINARIES)} required binaries...")
    for binary in REQUIRED_BINARIES:
        src = build_dir / binary
        shutil.copy2(src, bin_dir / binary)
        print(f"    ✓ {binary}")

    # 2. Copy setup_fboss_env from run_scripts
    run_scripts_dir = repo_path / "fboss" / "oss" / "scripts" / "run_scripts"
    setup_env = run_scripts_dir / "setup_fboss_env"
    if setup_env.exists():
        shutil.copy2(setup_env, bin_dir / "setup_fboss_env")
        print("    ✓ setup_fboss_env")
    else:
        print("    ⚠ setup_fboss_env not found in run_scripts/")

    # 3. Resolve and copy shared library dependencies
    # Mirrors package-fboss.py exactly: set LD_LIBRARY_PATH to all lib/lib64 dirs
    # under the getdeps installed/ tree, then run ldd per binary.
    # NOTE: this step must run inside the build container (CentOS) so that ldd
    # resolves system libs (libre2.so.9, libnl, libsodium, etc.) correctly.
    # The host invocation handles this via docker exec --collect-only.
    print("\n  → Resolving shared library dependencies...")
    lib_search_paths = get_lib_search_paths(installed_dir)
    print(f"    {len(lib_search_paths)} library search paths")

    all_deps: set[str] = set()
    for binary in REQUIRED_BINARIES:
        binary_path = build_dir / binary
        all_deps.update(resolve_dependencies(binary_path, lib_search_paths))

    for lib_path in sorted(all_deps):
        lib_name = os.path.basename(lib_path)
        dst = lib_dir / lib_name
        if not dst.exists() and not dst.is_symlink():
            try:
                shutil.copy2(lib_path, dst)
            except OSError as e:
                print(f"    ⚠ Skipping {lib_name}: {e}")

    print(f"    ✓ {len(all_deps)} libraries resolved and copied")

    # 4. Copy share/ configs from oss directories
    print("\n  → Copying config files...")

    # run_configs (default_configs, platform dirs)
    run_configs_dir = repo_path / "fboss" / "oss" / "scripts" / "run_configs"
    if run_configs_dir.exists():
        for item in run_configs_dir.iterdir():
            dst = share_dir / item.name
            shutil.copytree(item, dst)
            print(f"    ✓ {item.name}/")

    # oss config directories
    oss_dir = repo_path / "fboss" / "oss"
    config_dirs = [
        "hw_test_configs",
        "qsfp_test_configs",
        "link_test_configs",
        "hw_sanity_tests",
        "hw_benchmark_tests",
        "hw_known_bad_tests",
        "qsfp_known_bad_tests",
        "link_known_bad_tests",
        "qsfp_unsupported_tests",
        "sai_hw_unsupported_tests",
        "production_features",
    ]
    for config_dir_name in config_dirs:
        src = oss_dir / config_dir_name
        if src.exists():
            shutil.copytree(src, share_dir / config_dir_name)
            print(f"    ✓ {config_dir_name}/")

    print(f"\n  ✓ Build artifacts ready in {dest_dir}")


def build_runtime_image(repo_path: Path) -> int:
    """Build the runtime Docker image."""
    image_tag = f"{DEFAULT_IMAGE_NAME}:latest"
    dockerfile = repo_path / "fboss-sim" / "docker" / "Dockerfile.runtime"
    print(f"\n🔨 Building {image_tag}...")
    result = subprocess.run(
        ["docker", "build", "-f", str(dockerfile), "-t", image_tag, str(repo_path)],
        check=False,
    )
    if result.returncode == 0:
        print("  ✓ Image built successfully")
    else:
        print(f"  ✗ Build failed (exit {result.returncode})")
    return result.returncode


def is_container_running(container_name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def ensure_container_running() -> bool:
    """Ensure the build container is running, using nhfboss-docker-enter.py.

    That script handles both cases: create the container if it doesn't exist,
    or start it if it's stopped. When run non-interactively (no TTY) it starts
    the container as a daemon and returns.
    """
    if is_container_running(BUILD_CONTAINER_NAME):
        return True

    enter_script = Path(__file__).parent.parent.parent / "fboss" / "oss" / "scripts" / "nhfboss-docker-enter.py"
    if not enter_script.exists():
        return False

    print(f"  → Starting build container via {enter_script.name}...")
    # Run non-interactively: nhfboss-docker-enter.py checks sys.stdout.isatty() to
    # decide whether to run as a daemon and whether to exec into a shell.
    # Redirect both stdin and stdout so isatty()==False in both checks, which causes
    # it to start the container as a daemon and return instead of blocking.
    subprocess.run(
        ["python3", str(enter_script)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        check=False,
    )
    return is_container_running(BUILD_CONTAINER_NAME)


def collect_inside_container() -> None:
    """Run --collect-only inside the build container via docker exec.

    The build container runs CentOS so ldd resolves system libs correctly
    (libre2.so.9, libnl, libsodium, etc.) rather than Ubuntu host libs.
    """
    container_script = f"{CONTAINER_REPO_PATH}/fboss-sim/scripts/fboss-sim-docker-package.py"
    print(f"  → Running collect step inside {BUILD_CONTAINER_NAME}...")
    result = subprocess.run(
        ["docker", "exec", BUILD_CONTAINER_NAME, "python3", container_script, "--collect-only"],
        check=False,
    )
    if result.returncode != 0:
        print(f"  ✗ Collection failed (exit {result.returncode})")
        sys.exit(1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build fboss-sim runtime Docker image")
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect binaries/libs into tmp_build_dir (run inside build container)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("fboss-sim Runtime Image Builder")
    print("=" * 60)

    repo_path = get_repo_path()
    build_dir = get_build_dir(repo_path)
    installed_dir = get_installed_dir(repo_path)
    dest_dir = repo_path / "tmp_build_dir"

    print(f"Repository:  {repo_path}")
    print(f"Build dir:   {build_dir}")
    print(f"Installed:   {installed_dir}")

    if not build_dir.exists():
        print(f"\n❌ Error: Build directory not found: {build_dir}")
        print("   Please build FBOSS first with SAI_IMPL=fake")
        sys.exit(1)

    verify_binaries(build_dir)

    if args.collect_only:
        copy_artifacts(repo_path, build_dir, installed_dir, dest_dir)
        return

    # Host path: collect inside build container (correct CentOS libs for ldd),
    # then run docker build here where the Docker daemon is available.
    try:
        if not ensure_container_running():
            print(f"\n❌ Error: Could not start build container '{BUILD_CONTAINER_NAME}'.")
            print("   Try manually: ./fboss/oss/scripts/nhfboss-docker-enter.py")
            sys.exit(1)
        collect_inside_container()
        ret = build_runtime_image(repo_path)
    finally:
        shutil.rmtree(dest_dir, ignore_errors=True)

    if ret == 0:
        image_tag = f"{DEFAULT_IMAGE_NAME}:latest"
        print(f"\n{'=' * 60}")
        print("✅ Runtime image created successfully!")
        print(f"{'=' * 60}")
        print(f"\nImage: {image_tag}")
        print("\nNext steps:")
        print("  • Run container: ./fboss-sim/scripts/fboss-sim-docker-run.py")
        print(f"  • Or manually:   docker run -d --privileged --name fboss_sim_runtime_{USERNAME} {image_tag}")
    else:
        print("\n❌ Failed to create runtime image")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
