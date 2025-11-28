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
import sys

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
    cmd = ["docker", "ps"]
    if check_all:
        cmd.append("-a")
    proc = subprocess.run(
        cmd, capture_output=True, check=True,
    )
    return (
        proc.returncode == 0
        and re.search(rf"\b{docker_build.FBOSS_CONTAINER_NAME}\b", proc.stdout.decode())
        is not None
    )

# Check if we're in an interactive environment (has a TTY)
is_interactive = sys.stdout.isatty()
if not is_container_available(check_all=True):
    # If the container does not exist, create it with the appropriate mounts
    sdk_path = None
    if args.sdk_path:
        if os.path.exists(args.sdk_path):
            sdk_path = args.sdk_path
        else:
            print(f"Warning: SDK path {args.sdk_path} does not exist")
    extra_cmake_defines = (
        '{"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"}',
    )
    scratch_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.build_dir"))
    caches_dir = os.path.expandvars("$HOME/work/caches")
    os.makedirs(caches_dir, exist_ok=True)
    # Transition away from building as root:
    if not os.access(caches_dir, os.W_OK):
        print(f"Attempting to fix permissions on {caches_dir}")
        subprocess.run(
            f"sudo chown -R $(id -u):$(id -g) {caches_dir}",
            check=True,
            shell=True,
        )
    docker_build.create_scratch_path(scratch_path)
    docker_build.run_fboss_build(
        scratch_path=scratch_path,
        target=None,
        docker_output=is_interactive,
        use_system_deps=True,
        env_vars=[
            "SCCACHE_DIR:/var/extras/sccache",
            "SCCACHE_CACHE_SIZE:30G",
        ],  # Caching to speed up build within container
        use_local=True,
        num_jobs=None,
        schedule_type=None,
        cache_config=None,
        extras_dir=caches_dir,
        extra_cmake_defines=extra_cmake_defines,
        dot_files=[
            ".bashrc", ".bash_history",
            ".zshrc", ".zsh_history",
            ".config",
            ".emacs", ".emacs.d",
            ".gitconfig",
            ".gnupg",
            ".ssh",
            ".vim", ".vimrc",
            ".vscode-server",
            "bin",
        ],
        build=False,
        sdk_path=sdk_path,
        daemon=not is_interactive,
    )
else:
    # If the container exists, start it if it's not running, and enter it
    if not is_container_available():
        subprocess.run(["docker", "start", docker_build.FBOSS_CONTAINER_NAME])

    if is_interactive:
        shell = os.getenv("SHELL", "/bin/bash")
        subprocess.run(["docker", "exec", "-it", docker_build.FBOSS_CONTAINER_NAME, shell])
    else:
        print(f"Container {docker_build.FBOSS_CONTAINER_NAME} is running and ready for commands")
