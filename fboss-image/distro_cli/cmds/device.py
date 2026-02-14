# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Device command implementation."""

import json
import logging
import sys

from distro_cli.lib.cli import validate_path
from distro_cli.lib.distro_infra import (
    DISTRO_INFRA_CONTAINER,
    GETIP_SCRIPT_CONTAINER_PATH,
    deploy_image_to_device,
)
from distro_cli.lib.docker import container
from distro_cli.lib.exceptions import DistroInfraError

logger = logging.getLogger("fboss-image")


def print_to_console(message: str) -> None:
    """Print message to console"""
    print(message)  # noqa: T201


def image_upstream_command(args):
    """Download full image from upstream repository and set it to be loaded onto device"""
    logger.info(f"Setting upstream image for device {args.mac}")
    logger.info("Device image-upstream command (stub)")


def image_command(args):
    """Set device image from file and configure PXE boot"""
    logger.info(f"Setting image for device {args.mac}: {args.image_path}")

    try:
        deploy_image_to_device(args.mac, args.image_path)
        logger.info(
            f"Successfully configured device {args.mac} with image {args.image_path}"
        )
        logger.info("Device is ready for PXE boot")

    except DistroInfraError as e:
        logger.error(f"Failed to configure device: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


def reprovision_command(args):
    """Reprovision device"""
    logger.info(f"Reprovisioning device {args.mac}")
    logger.info("Device reprovision command (stub)")


def update_command(args):
    """Update specific components on device"""
    logger.info(f"Updating device {args.mac}")
    logger.info(f"Manifest: {args.manifest}")
    logger.info(f"Components: {' '.join(args.components)}")
    logger.info("Device update command (stub)")


def getip_command(args):
    """Get device IP address"""
    logger.info(f"Getting IP for device {args.mac}")

    # Check if container is running
    if not container.container_is_running(DISTRO_INFRA_CONTAINER):
        logger.error(f"Container '{DISTRO_INFRA_CONTAINER}' is not running")
        logger.error("Please start the distro-infra container first")
        return

    # Build command
    cmd = [GETIP_SCRIPT_CONTAINER_PATH, args.mac]
    if args.interface:
        cmd.append(args.interface)

    # Execute in container
    exit_code, stdout, stderr = container.exec_in_container(DISTRO_INFRA_CONTAINER, cmd)

    if exit_code != 0:
        logger.error(f"getip.sh failed with exit code {exit_code}")
        if stderr:
            logger.error(f"stderr: {stderr}")
        if stdout:
            logger.error(f"stdout: {stdout}")
        return

    # Parse JSON output
    try:
        result = json.loads(stdout)

        # Check for error in JSON
        if "error_code" in result:
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            logger.error(f"Error code: {result['error_code']}")
            return

        # Extract IP addresses
        ipv4 = result.get("ipv4")
        ipv6 = result.get("ipv6")

        if ipv4:
            print_to_console(ipv4)
        elif ipv6:
            print_to_console(ipv6)
        else:
            logger.error("No IP address found in response")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON output: {e}")
        logger.error(f"Output was: {stdout}")


def ssh_command(args):
    """SSH to device"""
    logger.info(f"SSH to device {args.mac}")
    logger.info("Device ssh command (stub)")


def setup_device_commands(cli):
    """Setup the device commands"""
    device = cli.add_command_group(
        "device",
        help_text="Manage FBOSS devices",
        arguments=[("mac", {"help": "Device MAC address"})],
    )

    device.add_command(
        "image-upstream",
        image_upstream_command,
        help_text="Download and set upstream Distro Image to be loaded onto device",
        arguments=[],
    )

    device.add_command(
        "image",
        image_command,
        help_text="Set Distro Image file to be loaded onto device",
        arguments=[
            (
                "image_path",
                {
                    "type": lambda p: validate_path(p, must_exist=True),
                    "help": "Path to image file",
                },
            )
        ],
    )

    device.add_command(
        "reprovision", reprovision_command, help_text="Reprovision device", arguments=[]
    )

    device.add_command(
        "update",
        update_command,
        help_text="Update specific components on device",
        arguments=[
            (
                "manifest",
                {
                    "type": lambda p: validate_path(p, must_exist=True),
                    "help": "Path to manifest JSON file",
                },
            ),
            ("components", {"nargs": "+", "help": "Component names to update"}),
        ],
    )

    device.add_command(
        "getip",
        getip_command,
        help_text="Get device IP address",
        arguments=[
            ("interface", {"help": "Network interface to use", "nargs": "?"}),
        ],
    )

    device.add_command("ssh", ssh_command, help_text="SSH to device", arguments=[])
