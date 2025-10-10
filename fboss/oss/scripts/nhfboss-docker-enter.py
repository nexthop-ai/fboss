#!/usr/bin/env python3

# Enter the FBOSS build container with the following mounts:
# - the fboss repository at /var/FBOSS/fboss
# - a temporary directory at ~/work for a scratch path used to download
#   dependencies needed for building
# - the ~work cache for speeding up the build
# - optional SDK path at /opt/sdk if the --sdk-path argument is provided
# Once the container is ran, rerunning this script will just reenter the
# existing container with its mount points. If mount points need to be changed,
# use the --reset-mount argument to recreate the container with the new mounts.

import os.path
import importlib
import subprocess
import argparse
import re

docker_build = importlib.import_module("docker-build")

parser = argparse.ArgumentParser(description="Enter FBOSS build container")
parser.add_argument(
    "--sdk-path", help="Path to SDK directory to mount into container", type=str
)
parser.add_argument(
    "--reset-mount", action="store_true", help="Reset the mount points in the container"
)
args = parser.parse_args()

if args.reset_mount:
    # Stop and remove the container if it's running
    stop_proc = subprocess.run(
        ["docker", "stop", docker_build.FBOSS_CONTAINER_NAME], capture_output=True
    )
    subprocess.run(
        ["docker", "rm", docker_build.FBOSS_CONTAINER_NAME], capture_output=True
    )


def is_container_available(check_all: bool = False) -> bool:
    """Check if the FBOSS build container is available.
    Args:
        check_all: If True, check if the container exists but might not be running.
    Returns:
        True if the container is available, False otherwise.
    """
    proc = subprocess.run(
        ["docker", "ps", "-a" if check_all else ""], capture_output=True
    )
    return (
        proc.returncode == 0
        and re.search(rf"\b{docker_build.FBOSS_CONTAINER_NAME}\b", proc.stdout.decode())
        is not None
    )


proc = subprocess.run(["docker", "ps", "-a"], capture_output=True)
if not is_container_available(check_all=True):
    # If the container does not exist, create it with the appropriate mounts
    sdk_path = None
    if args.sdk_path:
        if os.path.exists(args.sdk_path):
            sdk_path = args.sdk_path
        else:
            print(f"Warning: SDK path {args.sdk_path} does not exist")
    branch_name = (
        subprocess.run(
            "git status | awk '/On branch/ {print $3}'", shell=True, capture_output=True
        )
        .stdout.decode()
        .strip()
    )
    extra_cmake_defines = (
        '{"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"}',
    )
    docker_build.run_fboss_build(
        scratch_path=os.path.expandvars(
            "$HOME/work/fboss_build-" + branch_name
        ),  # Used for downloading dependencies to for building
        target=None,
        docker_output=True,
        use_system_deps=True,
        env_vars=[
            "SCCACHE_DIR:/var/extras/sccache",
            "SCCACHE_CACHE_SIZE:30G",
        ],  # Caching to speed up build within container
        use_local=True,
        num_jobs=None,
        schedule_type=None,
        cache_config=None,
        extras_dir=os.path.expandvars("$HOME/work/caches"),
        extra_cmake_defines=extra_cmake_defines,
        dot_files=True,
        build=False,
        sdk_path=sdk_path,
    )
else:
    # If the container exists, start it if it's not running, and enter it
    proc = subprocess.run(["docker", "ps"], capture_output=True)
    if not is_container_available():
        subprocess.run(["docker", "start", docker_build.FBOSS_CONTAINER_NAME])

    subprocess.run(["docker", "exec", "-it", docker_build.FBOSS_CONTAINER_NAME, "bash"])
