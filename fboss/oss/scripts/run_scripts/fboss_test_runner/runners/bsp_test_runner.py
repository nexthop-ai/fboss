#!/usr/bin/env python3
# @noautodeps
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.


from argparse import ArgumentParser
from typing import ClassVar

from fboss_test_runner.constants import SUB_ARG_BSP_HW_TEST
from fboss_test_runner.runners.platform_services_test_runner import (
    PlatformServicesTestRunner,
)


class BspTestRunner(PlatformServicesTestRunner):
    """
    Runner for the BSP validation suite (bsp_tests).

    bsp_tests is a standalone gtest binary that exercises the BSP / kernel
    layer directly - fbiob, the i2c / gpio / hwmon / led / xcvr / watchdog
    kmods, cdev, and kmod load/unload - rather than the FBOSS platform-service
    daemons that `run_test.py platform` covers. It needs no agent, SAI, or
    config file, so it reuses the cold-boot-only PlatformServicesTestRunner
    flow with a single fixed binary and test type.
    """

    # Single binary - no family of test types like the platform services runner.
    TEST_TYPE_CHOICES: ClassVar[list] = [SUB_ARG_BSP_HW_TEST]

    def add_subcommand_arguments(self, sub_parser: ArgumentParser) -> None:
        # Register the common + platform-services args (including --type) via
        # super(), then pin args.type: bsp_tests has no test-type choice, so the
        # inherited PlatformServicesTestRunner flow (disable_services(),
        # result-classname subscripting) resolves to "bsp_tests".
        super().add_subcommand_arguments(sub_parser)
        sub_parser.set_defaults(type=SUB_ARG_BSP_HW_TEST)

    def _get_test_binary_name(self) -> str:
        return "bsp_tests"

    def _get_test_run_args(self, conf_file: str) -> list[str]:  # noqa: ARG002
        return ["--enable_stress_tests"]
