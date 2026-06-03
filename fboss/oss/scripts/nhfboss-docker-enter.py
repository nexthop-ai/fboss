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
#
# Worktree mode (--worktree <path>):
# - Mounts the given worktree directory instead of the main repo
# - Creates .build_dir inside the worktree for build output
# - Mounts the main .git dir so git works inside the container
# - Uses a container name derived from the worktree directory name

import argparse
import hashlib
import importlib
import os.path
import re
import subprocess
import sys

docker_build = importlib.import_module("docker-build")

DOT_FILES = [
    ".bashrc",
    ".bash_history",
    ".zshrc",
    ".zsh_history",
    ".config",
    ".emacs",
    ".emacs.d",
    ".gitconfig",
    ".gnupg",
    ".ssh",
    ".vim",
    ".vimrc",
    ".vscode-server",
    "bin",
]

EXTRA_CMAKE_DEFINES = (
    '{"CMAKE_C_COMPILER_LAUNCHER":"sccache","CMAKE_CXX_COMPILER_LAUNCHER":"sccache"}'
)

parser = argparse.ArgumentParser(description="Enter FBOSS build container")
parser.add_argument(
    "--sdk-path", help="Path to SDK directory to mount into container", type=str
)
parser.add_argument(
    "--reset-mount", action="store_true", help="Reset the mount points in the container"
)
parser.add_argument(
    "--worktree",
    help="Path to a git worktree to use instead of the main repo. "
    "Creates a dedicated container with the worktree mounted at /var/FBOSS/fboss "
    "and .build_dir inside the worktree for build output.",
    type=str,
)
parser.add_argument(
    "--env",
    metavar="KEY=VALUE",
    action="append",
    default=[],
    help="Extra environment variables to set in the container (e.g. --env SAI_IMPL=fake). "
    "May be specified multiple times.",
)
args = parser.parse_args()

# Resolve worktree path and derive container name if --worktree given
worktree_abs_path = None
if args.worktree:
    worktree_abs_path = os.path.abspath(args.worktree)
    if not os.path.isdir(worktree_abs_path):
        print(
            f"Error: worktree path {worktree_abs_path} does not exist", file=sys.stderr
        )
        sys.exit(1)
    # Sanitize the basename to docker-safe chars and append a short hash of the
    # absolute path so two worktrees sharing a basename get distinct containers.
    worktree_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", os.path.basename(worktree_abs_path))
    worktree_hash = hashlib.sha1(worktree_abs_path.encode()).hexdigest()[:8]
    container_name = f"FBOSS_build_worktree-{worktree_name}-{worktree_hash}"
    docker_build.FBOSS_CONTAINER_NAME = container_name

if args.reset_mount:
    # Stop and remove the container if it's running
    stop_proc = subprocess.run(
        ["docker", "stop", docker_build.FBOSS_CONTAINER_NAME],
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["docker", "rm", docker_build.FBOSS_CONTAINER_NAME],
        check=False,
        capture_output=True,
    )


def _ensure_caches_dir() -> str:
    caches_dir = os.path.expandvars("$HOME/work/caches")
    os.makedirs(caches_dir, exist_ok=True)
    if not os.access(caches_dir, os.W_OK):
        print(f"Attempting to fix permissions on {caches_dir}")
        subprocess.run(
            f"sudo chown -R $(id -u):$(id -g) {caches_dir}",
            check=True,
            shell=True,
        )
    return caches_dir


def is_container_available(check_all: bool = False) -> bool:
    """Check if the FBOSS build container is available.
    Args:
        check_all: If True, check if the container exists but might not be running.
    Returns:
        True if the container is available, False otherwise.
    """
    cmd = [
        "docker",
        "ps",
        "--filter",
        f"name=^{docker_build.FBOSS_CONTAINER_NAME}$",
        "--format",
        "{{.Names}}",
    ]
    if check_all:
        cmd.insert(2, "-a")
    proc = subprocess.run(cmd, check=False, capture_output=True)
    return (
        proc.returncode == 0
        and docker_build.FBOSS_CONTAINER_NAME in proc.stdout.decode().split()
    )


def create_container(
    scratch_path: str,
    source_path: str | None,
    extra_mounts: list[str],
    sdk_path: str | None,
    is_interactive: bool,
    extra_env_vars: list[str] | None = None,
):
    docker_build.create_scratch_path(scratch_path)
    caches_dir = _ensure_caches_dir()

    if sdk_path:
        extra_mounts = [*extra_mounts, f"{sdk_path}:/opt/sdk:z"]

    # Convert user-supplied KEY=VALUE to the KEY:VALUE format expected internally
    converted_extra = [ev.replace("=", ":", 1) for ev in (extra_env_vars or [])]

    docker_build.run_fboss_build(
        scratch_path=scratch_path,
        target=None,
        docker_output=is_interactive,
        use_system_deps=True,
        env_vars=[
            "SCCACHE_DIR:/var/extras/sccache",
            "SCCACHE_CACHE_SIZE:30G",
            f"HISTFILE:/home/{docker_build.USERNAME}/.bash_history",
            "HISTSIZE:10000",
            "HISTFILESIZE:10000",
            *converted_extra,
        ],
        use_local=True,
        use_clang=True,
        num_jobs=None,
        schedule_type=None,
        cache_config=None,
        extras_dir=caches_dir,
        extra_cmake_defines=EXTRA_CMAKE_DEFINES,
        dot_files=DOT_FILES,
        build=False,
        daemon=not is_interactive,
        source_path=source_path,
        extra_mounts=extra_mounts,
    )


# Check if we're in an interactive environment (has a TTY)
is_interactive = sys.stdout.isatty()
if not is_container_available(check_all=True):
    sdk_path = None
    if args.sdk_path:
        if os.path.exists(args.sdk_path):
            sdk_path = args.sdk_path
        else:
            print(f"Warning: SDK path {args.sdk_path} does not exist")

    if worktree_abs_path:
        # A worktree's .git is a file pointing at the main repo's common git dir
        # via an absolute host path. Resolve that dir from the worktree itself
        # (not the script location) and bind-mount it read-only at the same path
        # inside the container so git resolves the pointer.
        common_git_dir = subprocess.run(
            ["git", "-C", worktree_abs_path, "rev-parse", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        common_git_dir = os.path.abspath(
            os.path.join(worktree_abs_path, common_git_dir)
        )
        scratch_path = os.path.join(worktree_abs_path, ".build_dir")
        extra_mounts = [
            f"{common_git_dir}:{common_git_dir}:ro",
        ]
        create_container(
            scratch_path,
            worktree_abs_path,
            extra_mounts,
            sdk_path,
            is_interactive,
            args.env,
        )
    else:
        scratch_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../.build_dir")
        )
        create_container(scratch_path, None, [], sdk_path, is_interactive, args.env)
else:
    # If the container exists, start it if it's not running, and enter it
    if not is_container_available():
        subprocess.run(
            ["docker", "start", docker_build.FBOSS_CONTAINER_NAME], check=False
        )

    if is_interactive:
        shell = os.getenv("SHELL", "/bin/bash")
        env_flags = [flag for ev in args.env for flag in ("-e", ev)]
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                *env_flags,
                docker_build.FBOSS_CONTAINER_NAME,
                shell,
            ],
            check=False,
        )
    else:
        print(
            f"Container {docker_build.FBOSS_CONTAINER_NAME} is running and ready for commands"
        )
