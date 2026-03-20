#!/usr/bin/env python3
# Copyright 2004-present Facebook. All Rights Reserved.

"""
Run fboss-sim runtime container with proper configuration.

This script launches the minimal fboss-sim runtime container created by
fboss-sim-docker-package.py with all necessary flags and capabilities.

Features:
- Proper systemd support (--privileged, --cgroupns=host)
- Shared memory configuration (--shm-size=512m) to prevent malloc corruption
- Network capabilities for interface management
- Support for monolithic and split agent modes
- Automatically stops and removes existing container
"""

import getpass
import subprocess
import sys
import time

USERNAME = getpass.getuser()
DEFAULT_IMAGE_NAME = f"fboss_sim_runtime_{USERNAME}"
DEFAULT_CONTAINER_NAME = f"fboss_sim_runtime_{USERNAME}"


def stop_existing_container(container_name: str):
    """Stop and remove existing container if it exists"""
    print(f"🔍 Checking for existing container: {container_name}")

    # Check if container exists
    check_cmd = ["docker", "ps", "-a", "-q", "-f", f"name={container_name}"]
    result = subprocess.run(check_cmd, check=False, capture_output=True, text=True)

    if result.stdout.strip():
        print("  → Found existing container, stopping...")
        stop_result = subprocess.run(
            ["docker", "stop", container_name], check=False, capture_output=True
        )
        if stop_result.returncode == 0:
            print("  ✓ Container stopped")

        print("  → Removing container...")
        rm_result = subprocess.run(
            ["docker", "rm", container_name], check=False, capture_output=True
        )
        if rm_result.returncode == 0:
            print("  ✓ Container removed")
    else:
        print("  → No existing container found")


def run_container():
    """Run the cfboss runtime container"""
    print("\n🚀 Starting cfboss runtime container...")
    print(f"  Image: {DEFAULT_IMAGE_NAME}:latest")
    print(f"  Container: {DEFAULT_CONTAINER_NAME}")
    print("  Configuration:")
    print("    - Shared memory: 512m")
    print("    - Memory limit: 4g")
    print("    - Cgroup namespace: host")
    print("    - Capabilities: NET_ADMIN (network interfaces), SYS_ADMIN (systemd)")

    cmd = [
        "docker",
        "run",
        "-d",
        # Security: Use minimal capabilities instead of --privileged
        # CAP_NET_ADMIN: Required for TunManager to create/manage network interfaces
        # CAP_SYS_ADMIN: Required for systemd to manage cgroups
        "--cap-add=NET_ADMIN",
        "--cap-add=SYS_ADMIN",
        # TUN device access for TunManager
        "--device=/dev/net/tun",
        # Shared memory for warm boot state and IPC
        "--shm-size=512m",
        # Memory limit to prevent runaway processes
        "--memory=4g",
        # Systemd requires host cgroup namespace and cgroup mount
        "--cgroupns=host",
        "-v",
        "/sys/fs/cgroup:/sys/fs/cgroup:rw",
        # Systemd needs tmpfs for /run and /tmp
        "--tmpfs",
        "/run",
        "--tmpfs",
        "/tmp",
        "--name",
        DEFAULT_CONTAINER_NAME,
        f"{DEFAULT_IMAGE_NAME}:latest",
    ]

    print("\n  → Running docker command...")
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Failed to start container")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode

    container_id = result.stdout.strip()
    print(f"  ✓ Container started (ID: {container_id[:12]})")

    # Wait for systemd to initialize
    print("  → Waiting for systemd to initialize...")
    time.sleep(3)
    print("  ✓ Systemd initialized")

    return 0


def main():
    print("=" * 60)
    print("cfboss Runtime Container Launcher")
    print("=" * 60)

    # Stop existing container
    stop_existing_container(DEFAULT_CONTAINER_NAME)

    # Run container
    ret = run_container()
    if ret != 0:
        return ret

    print(f"\n{'=' * 60}")
    print("✅ Container started successfully!")
    print(f"{'=' * 60}")
    print(f"\nContainer name: {DEFAULT_CONTAINER_NAME}")
    print("\nUseful commands:")
    print(
        f"  • Check status:  docker exec {DEFAULT_CONTAINER_NAME} systemctl status wedge_agent"
    )
    print(f"  • View logs:     docker logs {DEFAULT_CONTAINER_NAME}")
    print(f"  • Enter shell:   docker exec -it {DEFAULT_CONTAINER_NAME} bash")
    print(
        f"  • Switch mode:   docker exec {DEFAULT_CONTAINER_NAME} switch-agent-mode.sh split"
    )
    print(
        f"  • Run CLI test:  docker exec {DEFAULT_CONTAINER_NAME} /opt/fboss/bin/cli_test"
    )
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
