# Copyright (c) 2004-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

"""Build command implementation."""

from pathlib import Path

from distro_cli.builder.image_builder import ImageBuilder
from distro_cli.lib.cli import validate_path
from distro_cli.lib.manifest import ImageManifest


def build_command(args):
    """Build FBOSS image or components"""
    manifest_path = Path(args.manifest)
    manifest_obj = ImageManifest(manifest_path)
<<<<<<< HEAD
    builder = ImageBuilder(manifest_obj, args.kiwi_ng_debug)
||||||| fa2cbb1024
    builder = ImageBuilder(manifest_obj)
=======
    output_dir = getattr(args, "output_dir", None)
    builder = ImageBuilder(manifest_obj, output_dir=output_dir)
>>>>>>> e6332d29c3484deac8007be2a2b3d6ecd1dc3936

    if args.components:
        builder.build_components(list(args.components))
    else:
        builder.build_all()


def setup_build_command(cli):
    """Setup the build command"""
    cli.add_command(
        "build",
        build_command,
        help_text="Build FBOSS image or components",
        arguments=[
            (
                "manifest",
                {
                    "type": lambda p: validate_path(p, must_exist=True),
                    "help": "Path to manifest JSON file",
                },
            ),
            (
                "components",
                {"nargs": "*", "help": "Specific components to build (default: all)"},
            ),
            (
<<<<<<< HEAD
                "--kiwi-ng-debug",
                {
                    "action": "store_true",
                    "help": "Enable debug flag to see kiwi-ng build output (default: no)",
||||||| fa2cbb1024
=======
                "--output-dir",
                {
                    "type": str,
                    "default": None,
                    "help": "Output directory on a real filesystem (not FUSE/EdenFS). "
                    "Required on devservers where the source tree is on EdenFS.",
>>>>>>> e6332d29c3484deac8007be2a2b3d6ecd1dc3936
                },
            ),
        ],
    )
