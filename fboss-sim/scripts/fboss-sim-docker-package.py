#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.

"""
Package fboss-sim build artifacts into a minimal runtime Docker image.

This script collects FBOSS binaries from the build output directory, resolves
their shared library dependencies via ldd, and copies everything into a Docker
build context for the runtime image.

Two build back-ends are supported:
  cmake (default): binaries in .build_dir/build/fboss/
    Build with: ./fboss/oss/scripts/nhfboss-build.sh SAI_IMPL=fake
  bazel (--bazel): binaries in bazel-bin/ (symlinks resolved in-container)
    Build with: ./fboss/oss/scripts/bazel.sh build --sai fake <targets>

This script is environment-agnostic: it does not assume any particular build
container or repo mount. The only requirement is that the `--collect-only`
phase runs where the resolved shared libraries match the runtime image base OS
(CentOS Stream 9). See `--help` for the collect/build phase split.

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

REQUIRED_BINARIES = [
    "wedge_agent-sai_impl",
    "fboss_sw_agent",
    "fboss_hw_agent-sai_impl",
    "fboss2",
    "fboss2-dev",
    "fboss2_integration_test",
    "fsdb",
]

# bgp++ (bgpd) RPM, the same artifact the distro image installs. Optional, and
# never produced here: this script only stages an RPM that is already on disk,
# at --bgpd-rpm or .build_dir/downloads/. Absent → image without BGP.
BGPD_RPM_NAME = "distro_bgpd.rpm"

# Upstream facebook/fboss cmake names the fake-SAI agents with a "-fake" suffix;
# Nexthop's fork renames them to "-sai_impl" (cmake/AgentPlatformsSai.cmake) so
# fake and real builds drop identically-named binaries at the /opt/fboss/bin/
# paths the systemd units reference. When we build a rebased *upstream* PR, the
# NH CI harness overlay carries this packaging script but not that cmake rename,
# so the agents come out as "-fake". Accept either name and always install under
# the canonical "-sai_impl" name the runtime units expect.
BINARY_ALIASES = {
    "wedge_agent-sai_impl": ["wedge_agent-fake"],
    "fboss_hw_agent-sai_impl": ["fboss_hw_agent-fake"],
}


def resolve_binary(build_dir: Path, name: str) -> "Path | None":
    """Return the source path for a required binary, honoring known aliases.

    Prefers the canonical name; falls back to alternate names some build
    configurations emit (e.g. upstream's "-fake" fake-SAI suffix).
    """
    for candidate in (name, *BINARY_ALIASES.get(name, [])):
        path = build_dir / candidate
        if path.exists():
            return path
    return None


# bazel-bin-relative paths for each required binary.
# Must match the cc_binary target locations produced by bazelify.
BAZEL_BINARY_PATHS = {
    "wedge_agent-sai_impl":   "fboss/agent/platforms/sai/wedge_agent-sai_impl",
    "fboss_hw_agent-sai_impl": "fboss/agent/platforms/sai/fboss_hw_agent-sai_impl",
    "fboss_sw_agent":          "fboss/agent/fboss_sw_agent",
    "fboss2":                  "fboss/cli/fboss2/fboss2",
    "fboss2-dev":              "fboss/cli/fboss2/fboss2-dev",
    "fboss2_integration_test": "fboss/cli/fboss2/test/integration_test/fboss2_integration_test",
    "fsdb":                    "fboss/fsdb/server/fsdb",
}

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
    """Get the cmake FBOSS build output directory."""
    return repo_path / ".build_dir" / "build" / "fboss"


def get_installed_dir(repo_path: Path) -> Path:
    """Get the getdeps installed directory (contains dependency libs)."""
    return repo_path / ".build_dir" / "installed"


def stage_bazel_binaries(repo_path: Path, staging_dir: Path) -> None:
    """Copy real ELF files from bazel-bin/ into a flat staging_dir.

    Must run inside the build container so bazel-bin/ symlink targets resolve.
    """
    bazel_bin = repo_path / "bazel-bin"
    staging_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for name, rel_path in BAZEL_BINARY_PATHS.items():
        src = (bazel_bin / rel_path).resolve()
        if not src.exists():
            missing.append(f"{name} (expected {bazel_bin / rel_path})")
            continue
        shutil.copy2(src, staging_dir / name)
        print(f"  staged {name}  ←  {src}")

    if missing:
        print("\nError: Bazel binaries not found (build --sai fake first):")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)


def verify_binaries(build_dir: Path) -> None:
    """Verify all required binaries are present in the build directory."""
    print("\n🔍 Verifying required binaries...")
    missing = []
    for binary in REQUIRED_BINARIES:
        if resolve_binary(build_dir, binary) is None:
            missing.append(binary)

    if missing:
        print("❌ Error: Missing required binaries in build directory:")
        for b in missing:
            print(f"   - {b}")
        print(f"\n   Build directory: {build_dir}")
        print("   Please build FBOSS first with SAI_IMPL=fake")
        sys.exit(1)

    print(f"  ✓ All {len(REQUIRED_BINARIES)} required binaries present")


def resolve_dependencies(binary_path: Path) -> set[str]:
    """Use ldd to find shared library dependencies for a binary."""
    dependencies = set()

    # Check it's actually an ELF binary
    try:
        output = subprocess.check_output(["file", str(binary_path)])
        if b"executable" not in output and b"shared object" not in output:
            return dependencies
    except subprocess.CalledProcessError:
        return dependencies

    # Resolve via the binary's own RUNPATH; strip any inherited LD_LIBRARY_PATH
    # so a stale dep generation under installed/ can't shadow the correct one.
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)

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
        # verify_binaries() already guaranteed every required binary resolves.
        src = resolve_binary(build_dir, binary)
        shutil.copy2(src, bin_dir / binary)
        note = "" if src.name == binary else f" (from {src.name})"
        print(f"    ✓ {binary}{note}")

    # 2. Copy setup_fboss_env from run_scripts
    run_scripts_dir = repo_path / "fboss" / "oss" / "scripts" / "run_scripts"
    setup_env = run_scripts_dir / "setup_fboss_env"
    if setup_env.exists():
        shutil.copy2(setup_env, bin_dir / "setup_fboss_env")
        print("    ✓ setup_fboss_env")
    else:
        print("    ⚠ setup_fboss_env not found in run_scripts/")

    # 3. Resolve and copy shared library dependencies. ldd resolves each binary
    # via its own RUNPATH plus default system paths.
    # NOTE: this step must run inside the build container (CentOS) so that ldd
    # resolves system libs (libre2.so.9, libnl, libsodium, etc.) correctly.
    # The host invocation handles this via docker exec --collect-only.
    print("\n  → Resolving shared library dependencies...")

    all_deps: set[str] = set()
    for binary in REQUIRED_BINARIES:
        binary_path = resolve_binary(build_dir, binary)
        all_deps.update(resolve_dependencies(binary_path))

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


def stage_bgpd_rpm(repo_path: Path, dest_dir: Path, rpm_override: "str | None") -> None:
    """Stage the bgp++ RPM into tmp_build_dir/bgpd/ if one is present.

    Sources: --bgpd-rpm path, else the .build_dir/downloads/ cache. Producing
    the RPM is somebody else's job — whoever builds it stages it at one of
    those two paths. Absent → empty bgpd/ dir → the Dockerfile's bgpd layer is
    a no-op.
    """
    bgpd_dir = dest_dir / "bgpd"
    bgpd_dir.mkdir(parents=True, exist_ok=True)
    target = bgpd_dir / BGPD_RPM_NAME

    if rpm_override:
        src = Path(rpm_override)
        if not src.is_file():
            print(f"❌ Error: --bgpd-rpm not found: {src}")
            sys.exit(1)
        shutil.copy2(src, target)
        print(f"  ✓ Using provided bgpd RPM: {src}")
        return

    cache = repo_path / ".build_dir" / "downloads" / BGPD_RPM_NAME
    if cache.is_file():
        shutil.copy2(cache, target)
        print(f"  ✓ Using staged bgpd RPM: {cache}")
        return

    print(f"  ⏭  No bgpd RPM at {cache}; building the image without BGP")


def build_runtime_image(repo_path: Path) -> int:
    """Build the runtime Docker image.

    When FBOSS_SIM_CACHE_REF is set (e.g. in CI), uses docker buildx with a
    registry cache so stable layers (dnf install, rootfs, configs) are cache
    hits on fresh GARM runners.  Falls back to plain docker build for dev
    environments without registry access.
    """
    image_tag = f"{DEFAULT_IMAGE_NAME}:latest"
    dockerfile = repo_path / "fboss-sim" / "docker" / "Dockerfile.runtime"
    cache_ref = os.environ.get("FBOSS_SIM_CACHE_REF", "")

    print(f"\n🔨 Building {image_tag}...")

    if cache_ref:
        # Ensure a buildx builder with the docker-container driver exists so
        # registry cache export works (the default "docker" driver cannot export).
        subprocess.run(
            [
                "docker", "buildx", "create",
                "--name", "fboss-sim-cache",
                "--driver", "docker-container",
                "--use",
                "--bootstrap",
            ],
            check=False,
            capture_output=True,
        )
        cmd = [
            "docker", "buildx", "build",
            "--load",  # load the result into the local docker daemon
            "--cache-from", f"type=registry,ref={cache_ref}",
            "--cache-to", f"type=registry,ref={cache_ref},mode=max",
            "-f", str(dockerfile),
            "-t", image_tag,
            str(repo_path),
        ]
    else:
        cmd = [
            "docker", "build",
            "-f", str(dockerfile),
            "-t", image_tag,
            str(repo_path),
        ]

    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print("  ✓ Image built successfully")
    else:
        print(f"  ✗ Build failed (exit {result.returncode})")
    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Build fboss-sim runtime Docker image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Phases:\n"
            "  --collect-only  Resolve binaries+libs+configs into tmp_build_dir/.\n"
            "                  MUST run in an environment whose libc/system libs\n"
            "                  match the runtime image base (CentOS Stream 9), so\n"
            "                  ldd resolves the right .so files. On a host that\n"
            "                  built FBOSS in a CentOS build container, run this\n"
            "                  step inside that container.\n"
            "  --build-only    docker build the runtime image from tmp_build_dir/.\n"
            "                  Run wherever the Docker daemon lives (the host).\n"
            "  (no flag)       Run both phases in the current environment. Use this\n"
            "                  when you built FBOSS natively on a CentOS-9 host.\n"
            "\n"
            "Split-environment example (Ubuntu host + CentOS build container):\n"
            "  docker exec <build-container> python3 \\\n"
            "      fboss-sim/scripts/fboss-sim-docker-package.py --collect-only\n"
            "  python3 fboss-sim/scripts/fboss-sim-docker-package.py --build-only\n"
        ),
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect binaries/libs/configs into tmp_build_dir/ (no docker build)",
    )
    group.add_argument(
        "--build-only",
        action="store_true",
        help="Only docker build the image from an existing tmp_build_dir/ (no collect)",
    )
    parser.add_argument(
        "--bazel",
        action="store_true",
        help="Source binaries from bazel-bin/ (--sai fake build) instead of .build_dir/",
    )
    bgpd_group = parser.add_mutually_exclusive_group()
    bgpd_group.add_argument(
        "--bgpd-rpm",
        metavar="PATH",
        help=f"Use this bgpd RPM instead of .build_dir/downloads/{BGPD_RPM_NAME}",
    )
    bgpd_group.add_argument(
        "--no-bgpd",
        action="store_true",
        help="Build the image without the bgpd (bgp++) routing daemon",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("fboss-sim Runtime Image Builder")
    print("=" * 60)

    repo_path = get_repo_path()
    installed_dir = get_installed_dir(repo_path)
    dest_dir = repo_path / "tmp_build_dir"

    if args.bazel:
        # Stage Bazel binaries into a flat dir so the rest of the pipeline is unchanged.
        bazel_staging = repo_path / "tmp_bazel_stage"
        print(f"\nBazel mode: staging binaries from bazel-bin/ → {bazel_staging}")
        stage_bazel_binaries(repo_path, bazel_staging)
        build_dir = bazel_staging
    else:
        build_dir = get_build_dir(repo_path)

    print(f"Repository:  {repo_path}")
    print(f"Build dir:   {build_dir}")
    print(f"Installed:   {installed_dir}")

    # --- Collect phase ---
    if args.collect_only or not args.build_only:
        if not build_dir.exists():
            print(f"\n❌ Error: Build directory not found: {build_dir}")
            if args.bazel:
                print("   Build first: bazel.sh build --sai fake <targets>")
            else:
                print("   Please build FBOSS first with SAI_IMPL=fake")
            sys.exit(1)
        verify_binaries(build_dir)
        copy_artifacts(repo_path, build_dir, installed_dir, dest_dir)
        # In --collect-only mode the staging dir was created by this process
        # (it didn't exist before main() ran), so clean it up here.  In the
        # full (non-collect-only) path the same cleanup happens in the finally
        # block below, after collect_inside_container() recreates the staging
        # dir inside the container.
        if args.bazel:
            shutil.rmtree(build_dir, ignore_errors=True)
        if args.collect_only:
            print(f"\n✅ Collected artifacts into {dest_dir}")
            print("   Next: run `--build-only` where the Docker daemon is available.")
            return

    # --- Build phase ---
    if not dest_dir.exists():
        print(f"\n❌ Error: {dest_dir} not found.")
        print("   Run the `--collect-only` phase first (in a CentOS-9 environment).")
        sys.exit(1)

    if args.no_bgpd:
        # Empty bgpd/ dir keeps the Dockerfile's unconditional COPY a no-op.
        (dest_dir / "bgpd").mkdir(parents=True, exist_ok=True)
        print("\n⏭  Skipping bgpd (--no-bgpd)")
    else:
        stage_bgpd_rpm(repo_path, dest_dir, args.bgpd_rpm)

    try:
        ret = build_runtime_image(repo_path)
    finally:
        shutil.rmtree(dest_dir, ignore_errors=True)
        if args.bazel:
            shutil.rmtree(repo_path / "tmp_bazel_stage", ignore_errors=True)

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
