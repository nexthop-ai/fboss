#!/usr/bin/env python3
# @noautodeps
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from typing import ClassVar

import run_test

from fboss_test_runner.constants import SUB_ARG_PLATFORM_MANAGER_HW_TEST
from fboss_test_runner.result_types import GtestResult
from fboss_test_runner.runners.test_runner import (
    disable_services,
    enable_services,
    TestRunner,
)

SUB_ARG_TEST_TYPE = "--type"
SUB_ARG_PLATFORM_HW_TEST = "platform_hw_test"
SUB_ARG_DATA_CORRAL_HW_TEST = "data_corral_service_hw_test"
SUB_ARG_FAN_HW_TEST = "fan_service_hw_test"
SUB_ARG_FW_UTIL_HW_TEST = "fw_util_hw_test"
SUB_ARG_SENSOR_HW_TEST = "sensor_service_hw_test"
SUB_ARG_WEUTIL_HW_TEST = "weutil_hw_test"


class PlatformServicesTestRunner(TestRunner):
    TEST_TYPE_CHOICES: ClassVar[list] = [
        SUB_ARG_PLATFORM_HW_TEST,
        SUB_ARG_DATA_CORRAL_HW_TEST,
        SUB_ARG_FAN_HW_TEST,
        SUB_ARG_FW_UTIL_HW_TEST,
        SUB_ARG_SENSOR_HW_TEST,
        SUB_ARG_WEUTIL_HW_TEST,
        SUB_ARG_PLATFORM_MANAGER_HW_TEST,
    ]

    def add_subcommand_arguments(self, sub_parser: ArgumentParser) -> None:
        super().add_subcommand_arguments(sub_parser)
        sub_parser.add_argument(
            SUB_ARG_TEST_TYPE,
            choices=self.TEST_TYPE_CHOICES,
            nargs="?",
            default=None,
            help="Specify test type for platform services test.",
        )

    def _get_test_binary_name(self) -> str:
        args = run_test.args
        binary_map = {
            SUB_ARG_PLATFORM_HW_TEST: "platform_hw_test",
            SUB_ARG_DATA_CORRAL_HW_TEST: "data_corral_service_hw_test",
            SUB_ARG_FAN_HW_TEST: "fan_service_hw_test",
            SUB_ARG_FW_UTIL_HW_TEST: "fw_util_hw_test",
            SUB_ARG_SENSOR_HW_TEST: "sensor_service_hw_test",
            SUB_ARG_WEUTIL_HW_TEST: "weutil_hw_test",
            SUB_ARG_PLATFORM_MANAGER_HW_TEST: "platform_manager_hw_test",
        }

        return binary_map.get(args.type, "platform_hw_test")

    def _get_warmboot_check_file(self) -> str:
        return ""

    def _get_test_run_args(self, conf_file: str) -> list[str]:  # noqa: ARG002
        return []

    def _run_tests(
        self, tests_to_run: list[str], conf_file: str, args: Namespace
    ) -> tuple[list, list]:
        test_binary_name = self._get_test_binary_name()
        all_results: list[GtestResult] = []
        test_results = []
        num_tests = len(tests_to_run)
        disable_services(args.type)
        try:
            for idx, test_to_run in enumerate(tests_to_run):
                test_prefix = test_binary_name + "."
                with suppress(FileNotFoundError):
                    os.unlink(self.TESTRESULT_CURRENT_RUN_FILE)
                print("########## Running test: " + test_to_run, flush=True)
                run_outcome = self._run_test(
                    conf_file,
                    test_prefix,
                    test_to_run,
                    False,  # setup_warmboot
                )
                print(
                    f"test results ({idx + 1}/{num_tests}): {run_outcome.console_output}",
                    flush=True,
                )
                all_results.extend(run_outcome.results)
                # Reads each test result file (updated by _run_test above) and appends it with
                # args.type as a subscript (e.g., TestName[fan_service_hw_test])
                test_results.append(
                    self.get_updated_test_result_with_classname_subscript(args.type)
                )
        finally:
            enable_services(args.type)

        self._end_run()
        return all_results, test_results

    def run_test(self, args: Namespace) -> None:
        args.fruid_path = None
        types = [args.type] if args.type else self.TEST_TYPE_CHOICES
        for test_type in types:
            args.type = test_type
            super().run_test(args)
