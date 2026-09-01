#!/usr/bin/env python3
# @noautodeps
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import os
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from typing import ClassVar

<<<<<<< HEAD
from fboss_test_runner.constants import SUB_ARG_PLATFORM_MANAGER_HW_TEST
from fboss_test_runner.result_types import GtestResult
from fboss_test_runner.runners.test_runner import (
    disable_services,
    enable_services,
    TestRunner,
)
||||||| 4c0febe655
from fboss_test_runner.result_types import GtestResult
from fboss_test_runner.runners.test_runner import TestRunner
=======
from fboss_test_runner.reporters.json_reporter import JsonReporter
from fboss_test_runner.result_types import GtestResult, TestExecutionResult
from fboss_test_runner.runners.test_runner import TestRunner
>>>>>>> be11fad19cf8da3f8dbcc1318a6109b7c9b96dbe

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

    def _wait_for_agent_thrift_ports_free(self) -> None:
        # The base-class wait exists for suites where each test binary starts
        # its own agent and must bind the agent thrift ports. Platform services
        # tests never touch those ports (they talk to sysfs directly), while the
        # DUT's production fboss_sw_agent/fboss_hw_agent hold 5909/5959 for the
        # whole run by design, so the wait can never succeed and would burn its
        # full timeout before every single test. Same rationale as the fboss2
        # integration runner's override.
        return

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
        args = self.args
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

    @staticmethod
    def _args_for_test_type(args: Namespace, test_type: str) -> Namespace:
        return Namespace(
            **{
                **vars(args),
                "fruid_path": None,
                "type": test_type,
            }
        )

    def list_tests(self, args: Namespace) -> int:
        test_types = [args.type] if args.type else self.TEST_TYPE_CHOICES
        exit_code = 0
        for test_type in test_types:
            exit_code = max(
                exit_code,
                super().list_tests(self._args_for_test_type(args, test_type)),
            )
        return exit_code

    def _run_test_type(self, args: Namespace, test_type: str) -> TestExecutionResult:
        return self._execute_test(self._args_for_test_type(args, test_type))

    def run_test(self, args: Namespace) -> int:
        test_types = [args.type] if args.type else self.TEST_TYPE_CHOICES
        results: list[GtestResult] = []
        setup_failures: list[str] = []
        exit_code = 0

        try:
            for test_type in test_types:
                execution = self._run_test_type(args, test_type)
                if execution.error is not None and args.results_json is None:
                    raise execution.error
                if execution.results is not None:
                    results.extend(execution.results)
                if execution.setup_failure is not None:
                    setup_failures.append(execution.setup_failure)
                    exit_code = os.EX_TEMPFAIL
                elif exit_code != os.EX_TEMPFAIL:
                    exit_code = max(exit_code, execution.exit_code)
        finally:
            if results:
                self._print_output_summary(results)
            if args.results_json is not None:
                JsonReporter().write_run_results(
                    results, setup_failures, args.results_json
                )
        return exit_code
