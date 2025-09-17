#!/usr/bin/env python3

# Enter the FBOSS build container with everything mounted

import os.path
import importlib
import subprocess
import argparse

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

proc = subprocess.run(["docker", "ps", "-a"], capture_output=True)
if (
    proc.returncode == 0
    and docker_build.FBOSS_CONTAINER_NAME not in proc.stdout.decode()
):
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
        scratch_path=os.path.expandvars("$HOME/work/fboss_build-" + branch_name),
        target=None,
        docker_output=True,
        use_system_deps=True,
        env_vars=["SCCACHE_DIR:/var/extras/sccache", "SCCACHE_CACHE_SIZE:30G"],
        use_local=True,
        num_jobs=None,
        schedule_type=None,
        cache_config=None,
        extras_dir=os.path.expandvars("$HOME/work/caches"),
        extra_cmake_defines=extra_cmake_defines,
        build=False,
        sdk_path=sdk_path,
    )
else:
    proc = subprocess.run(["docker", "ps"], capture_output=True)
    if (
        proc.returncode == 0
        and docker_build.FBOSS_CONTAINER_NAME not in proc.stdout.decode()
    ):
        subprocess.run(["docker", "start", docker_build.FBOSS_CONTAINER_NAME])

    subprocess.run(["docker", "exec", "-it", docker_build.FBOSS_CONTAINER_NAME, "bash"])
