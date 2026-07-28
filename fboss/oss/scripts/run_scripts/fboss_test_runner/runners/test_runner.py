#!/usr/bin/env python3
# @noautodeps
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import abc
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from datetime import datetime, timezone

from nh_test_xml_utils import (
    emit_test_boundary,
    exit_info,
    find_recent_core_dump,
    inject_streams_into_xml,
    pipe_to_tee,
    StreamTee,
    write_synthetic_failure_xml,
)

from fboss_test_runner.constants import (
    ALL_SIMUALTOR_ASICS_STR,
    DEFAULT_TEST_RUN_TIMEOUT_IN_SECOND,
    DNX_SIMULATOR_ASICS,
    DNX_SIMULATOR_ENV,
    OPT_ARG_COLDBOOT,
    OPT_ARG_CONFIG_FILE,
    OPT_ARG_DISABLE_FSDB,
    OPT_ARG_FBOSS_LOGGING,
    OPT_ARG_FILTER,
    OPT_ARG_FILTER_FILE,
    OPT_ARG_FRUID_PATH,
    OPT_ARG_FSDB_CONFIG_FILE,
    OPT_ARG_LIST_TESTS,
    OPT_ARG_MGT_IF,
    OPT_ARG_NUM_WARMBOOT_ITERATIONS,
    OPT_ARG_PROFILE,
    OPT_ARG_QSFP_CONFIG_FILE,
    OPT_ARG_SAI_LOGGING,
    OPT_ARG_SAI_REPLAYER_LOGGING,
    OPT_ARG_SETUP_CB,
    OPT_ARG_SETUP_WB,
    OPT_ARG_SIMULATOR,
    OPT_ARG_SKIP_KNOWN_BAD_TESTS,
    OPT_ARG_TEST_RUN_TIMEOUT,
    OPT_KNOWN_BAD_TESTS_FILE,
    OPT_UNSUPPORTED_TESTS_FILE,
    SUB_ARG_BSP_HW_TEST,
    TEST_DISABLE_SERVICES,
    XGS_SIMULATOR_ASICS,
    XGS_SIMULATOR_ENV,
)
from fboss_test_runner.reporters.console_reporter import ConsoleReporter
from fboss_test_runner.reporters.csv_reporter import CsvReporter
from fboss_test_runner.result_types import GtestResult, GtestStatus, RunOutcome
from fboss_test_runner.runners.utils import (
    get_test_regexes_from_file,
    load_from_file,
    test_matches_any_regex,
)
from fboss_test_runner.services.fboss_agent_utils import FBOSS_AGENT_VOLATILE_STATE_DIR

_YELLOW = "\033[1;33m"
_RED = "\033[1;31m"
_RESET = "\033[0m"

# Strip [cold_boot]/[warm_boot*] so phases of one logical test share a name.
_BOOT_SUBSCRIPT_RE = re.compile(r"\[(?:cold|warm)_boot[^\]]*\]$")
_STATUS_RANK = {"skipped": 0, "passed": 1, "error": 2, "failure": 3}


def _print_deprecation_banner(lines: list[str]) -> None:
    """Print a highly visible warning banner with color and box formatting."""
    width = max(len(line) for line in lines) + 4
    border = "*" * width
    print(f"\n{_RED}{border}")
    for line in lines:
        print(f"* {_YELLOW}{line.ljust(width - 4)}{_RED} *")
    print(f"{border}{_RESET}\n", flush=True)


def disable_services(test_name: str):
    if test_name in TEST_DISABLE_SERVICES:
        services = TEST_DISABLE_SERVICES[test_name]
        print(f"Stopping services: {', '.join(services)}", flush=True)
        subprocess.run(["systemctl", "mask", *services], check=False)
        subprocess.run(["systemctl", "stop", *services], check=False)
        time.sleep(2)
        # fboss_*_agent gracefulExit() writes can_warm_boot; wipe so the next
        # test binary cold-boots instead of crashing on missing agent.conf.
        if any(
            s.startswith("fboss_sw_agent") or s.startswith("fboss_hw_agent")
            for s in services
        ):
            subprocess.run(
                ["rm", "-rf", f"{FBOSS_AGENT_VOLATILE_STATE_DIR}/warm_boot"],
                check=False,
            )
        print("Services stopped", flush=True)


def _wait_for_devmap(timeout_s: int = 30) -> None:
    # platform_manager rebuilds /run/devmap/ asynchronously after restart.
    # Poll until sensors and xcvrs dirs are non-empty so dependent services
    # (qsfp_service, sensor_service) don't start against missing symlinks.
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if all(
            os.path.isdir(d) and os.listdir(d)
            for d in ("/run/devmap/sensors", "/run/devmap/xcvrs")
        ):
            return
        time.sleep(1)
    print(
        "Warning: /run/devmap not fully repopulated after platform_manager restart",
        flush=True,
    )


def enable_services(test_name: str):
    if test_name not in TEST_DISABLE_SERVICES:
        return
    services = TEST_DISABLE_SERVICES[test_name]
    print(f"Restarting services: {', '.join(services)}", flush=True)
    subprocess.run(
        ["systemctl", "unmask", *services], check=False, stderr=subprocess.DEVNULL
    )

    if test_name == SUB_ARG_BSP_HW_TEST:
        print("Restarting platform_manager to rebuild /run/devmap/", flush=True)
        subprocess.run(["systemctl", "restart", "platform_manager"], check=False)
        _wait_for_devmap()

    for service in services:
        subprocess.Popen(
            ["systemctl", "restart", service],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    print("Services restart initiated", flush=True)


class TestRunner(abc.ABC):
    WARMBOOT_SETUP_OPTION = "--setup-for-warmboot"
    COLDBOOT_PREFIX = "cold_boot."
    WARMBOOT_PREFIX = "warm_boot."
    # SwSwitch agent thrift ports (SwAgentInitializer FLAGS_port / migrated_port).
    AGENT_THRIFT_PORTS = (5909, 5959)
    AGENT_PORT_FREE_TIMEOUT_S = 60
    # Category labels passed to _resolve_tests_file (used in log messages).
    KNOWN_BAD_TESTS_LABEL = "known_bad"
    UNSUPPORTED_TESTS_LABEL = "unsupported"

    TESTRESULT_FILE = "/home/netops/tr.xml"
    TESTRESULT_CURRENT_RUN_FILE = "/home/netops/tr_current_run.xml"

    def __init__(self) -> None:
        self._known_bad_test_regexes: list[str] = []
        self._unsupported_test_regexes: list[str] = []
        # Known-bad/unsupported tests dropped pre-run; recorded as <skipped>.
        self._skipped_known_bad_tests: list[str] = []
        self.env_var: dict[str, str] = dict(os.environ)
        # Populated by run_test() before any per-run method runs. Defaults to an
        # empty Namespace so attribute access is typed (Namespace.__getattr__ ->
        # Any) rather than Optional; a method reached before run_test() fails
        # loudly on the missing attribute, same as the old None default.
        self.args: Namespace = Namespace()

    def _get_common_gflags(self) -> list[str]:
        """
        Return pass-through gflags appended to every test binary invocation.
        No parsing or validation - just forward whatever the user provides.
        """
        args = self.args
        if hasattr(args, "extra_gflags") and args.extra_gflags:
            return args.extra_gflags.split()
        return []

    def _get_config_path(self) -> str:
        return ""

    def _resolve_tests_file(
        self, user_file: str | None, default_file: str, label: str
    ) -> str:
        """Resolve a known-bad / unsupported tests file, shared by all runners:
        prefer a caller-supplied override when it exists, else fall back to the
        default file when it exists, else return "" (no filtering)."""
        if user_file:
            if os.path.exists(user_file):
                print(f"Using user-specified {label} tests file: {user_file}")
                return user_file
            print(f"Warning: User-specified {label} tests file not found: {user_file}")
        if default_file and os.path.exists(default_file):
            print(f"Using default {label} tests file: {default_file}")
            return default_file
        print(f"No {label} tests file found, skipping {label} test filtering")
        return ""

    def _get_known_bad_tests_file(self) -> str:
        return ""

    def _get_unsupported_tests_file(self) -> str:
        return ""

    @abc.abstractmethod
    def _get_test_binary_name(self) -> str:
        pass

    def _get_sai_replayer_logging_flags(
        self, sai_replayer_log_path: str | None
    ) -> list[str]:
        return []

    def _get_sai_logging_flags(self) -> list[str]:
        return []

    @abc.abstractmethod
    def _get_warmboot_check_file(self) -> str:
        pass

    @abc.abstractmethod
    def _get_test_run_args(self, conf_file: str) -> list[str]:
        pass

    def _setup_run(self, conf_file: str) -> None:  # noqa: B027
        pass

    def _setup_coldboot_test(self, sai_replayer_log_path: str | None = None) -> None:  # noqa: B027
        pass

    def _setup_warmboot_test(self, sai_replayer_log_path: str | None = None) -> None:  # noqa: B027
        pass

    def _end_run(self) -> None:  # noqa: B027
        pass

    def add_subcommand_arguments(self, sub_parser: ArgumentParser) -> None:
        sub_parser.add_argument(
            OPT_ARG_COLDBOOT,
            action="store_true",
            default=False,
            help="Run tests without warmboot",
        )
        sub_parser.add_argument(
            OPT_ARG_FILTER,
            type=str,
            help="only run tests that match the filter e.g. --filter=*Route*V6*",
        )
        sub_parser.add_argument(
            OPT_ARG_FILTER_FILE,
            type=str,
            help="only run tests that match the filters in filter file",
        )
        sub_parser.add_argument(
            OPT_ARG_PROFILE,
            type=str,
            help="only include patterns tagged with this profile (requires --filter_file)",
        )
        sub_parser.add_argument(
            OPT_ARG_LIST_TESTS,
            action="store_true",
            default=False,
            help="Only lists the tests, do not run any test",
        )
        sub_parser.add_argument(
            OPT_ARG_CONFIG_FILE, type=str, help="run with the specified config file"
        )
        sub_parser.add_argument(
            OPT_ARG_SKIP_KNOWN_BAD_TESTS,
            type=str,
            help="test config key for known bad tests. Format: vendor/coldboot-sai/warmboot-sai/asic",
        )
        sub_parser.add_argument(
            OPT_KNOWN_BAD_TESTS_FILE,
            type=str,
            default=None,
            help="Specify file for storing the known bad tests",
        )
        sub_parser.add_argument(
            OPT_UNSUPPORTED_TESTS_FILE,
            type=str,
            default=None,
            help="Specify file for storing the unsupported tests",
        )
        sub_parser.add_argument(
            OPT_ARG_MGT_IF,
            type=str,
            default="eth0",
            help="Management interface (default = eth0)",
        )
        sub_parser.add_argument(
            OPT_ARG_FRUID_PATH,
            type=str,
            default="/var/facebook/fboss/fruid.json",
            help="Specify file for storing the fruid data",
        )
        sub_parser.add_argument(
            OPT_ARG_FBOSS_LOGGING,
            type=str,
            default="DBG4",
            help="Enable FBOSS logging (Options: INFO|ERR|DBG0-9)",
        )
        sub_parser.add_argument(
            OPT_ARG_TEST_RUN_TIMEOUT,
            type=int,
            default=DEFAULT_TEST_RUN_TIMEOUT_IN_SECOND,
            help="Specify test run timeout in seconds",
        )
        sub_parser.add_argument(
            OPT_ARG_NUM_WARMBOOT_ITERATIONS,
            type=int,
            default=1,
            help=(
                "Number of consecutive warmboot iterations to run after coldboot "
                "(default 1). Use with --filter to soak a single test across many "
                "warmboots, e.g. --filter AgentEmptyTest.CheckInit "
                "--num-warmboot-iterations 64. Ignored when --coldboot_only is set."
            ),
        )
        # --- Pass-through gflags for test binaries ---
        sub_parser.add_argument(
            "--extra-gflags",
            type=str,
            default=None,
            help=(
                "Pass-through flags appended to every test binary invocation. "
                "Use = to attach value (required when value starts with --). "
                "Example: --extra-gflags='--asic_feature_support_overrides=73=false --v=2'"
            ),
        )

    @staticmethod
    def _add_sai_arguments(sub_parser: ArgumentParser) -> None:
        sub_parser.add_argument(
            OPT_ARG_SAI_LOGGING,
            type=str,
            default="WARN",
            help="Enable SAI logging (Options: DEBUG|INFO|NOTICE|WARN|ERROR|CRITICAL)",
        )
        sub_parser.add_argument(
            OPT_ARG_SAI_REPLAYER_LOGGING,
            type=str,
            help="Enable SAI Replayer logging and store logs in the supplied directory",
        )
        sub_parser.add_argument(
            OPT_ARG_SIMULATOR,
            type=str,
            help="Specify ASIC simulator. Options: " + ALL_SIMUALTOR_ASICS_STR,
        )
        sub_parser.add_argument(
            "--run-on-reference-board",
            action="store_true",
            help="Modify SAI settings to run on reference board instead of real product",
            default=False,
        )
        sub_parser.add_argument(
            OPT_ARG_SETUP_CB,
            type=str,
            default=None,
            help="run script before cold boot run",
        )
        sub_parser.add_argument(
            OPT_ARG_SETUP_WB,
            type=str,
            default=None,
            help="run script before warm boot run",
        )

    @staticmethod
    def _add_service_arguments(sub_parser: ArgumentParser) -> None:
        sub_parser.add_argument(
            OPT_ARG_QSFP_CONFIG_FILE,
            type=str,
            help="run tests with specified qsfp config (absolute path)",
        )
        sub_parser.add_argument(
            OPT_ARG_DISABLE_FSDB,
            action="store_true",
            help="Disable FSDB service for link tests",
            default=False,
        )
        sub_parser.add_argument(
            OPT_ARG_FSDB_CONFIG_FILE,
            type=str,
            help="run tests with specified fsdb config (absolute path)",
            default=None,
        )

    def _filter_tests(self, tests: list[str]) -> list[str]:
        return tests

    def _get_sai_replayer_log_path(
        self,
        test_prefix: str,
        test_name: str,
        sai_replayer_logging_dir: str | None = None,
    ) -> str | None:
        if sai_replayer_logging_dir is None:
            return None
        return os.path.join(
            sai_replayer_logging_dir,
            "replayer-log-" + test_prefix + test_name.replace("/", "-"),
        )

    def _get_test_run_cmd(
        self, conf_file: str, test_to_run: str, flags: list[str]
    ) -> list[str]:
        args = self.args
        test_binary_name = self._get_test_binary_name()
        run_cmd = [
            test_binary_name,
            "--gtest_filter=" + test_to_run,
            f"--gtest_output=xml:{self.TESTRESULT_CURRENT_RUN_FILE}",
        ]
        if args.fruid_path is not None:
            run_cmd.append("--fruid_filepath=" + args.fruid_path)
        run_cmd += self._get_test_run_args(conf_file)
        run_cmd += self._get_common_gflags()

        return run_cmd + flags if flags else run_cmd

    def _get_test_regexes_from_file(
        self, file_path: str, test_dict_key: str, keys_to_try: list[str]
    ) -> list[str]:
        return get_test_regexes_from_file(file_path, test_dict_key, keys_to_try)

    def _initialize_test_lists(self, args: Namespace) -> None:
        """
        Initialize known bad and unsupported test lists.
        This should be called once at the start of run_test() when args are available.
        """
        if not args.skip_known_bad_tests:
            print(
                "The --skip-known-bad-tests option is not set, therefore unsupported tests will be run."
            )
            self._known_bad_test_regexes = []
            self._unsupported_test_regexes = []
            return

        # Build list of keys to try - always try exactly two keys:
        # 1. The key as provided
        # 2. Either the key with run mode suffix stripped (if it ends with one)
        #    or the key with run mode suffix appended (if it doesn't)
        base_key = args.skip_known_bad_tests
        keys_to_try = [base_key]

        # Only try run mode suffix if the subcommand has agent_run_mode
        if hasattr(args, "agent_run_mode"):
            run_mode_suffix = f"/{args.agent_run_mode}"
            if base_key.endswith(run_mode_suffix):
                # Key already has the run mode suffix, try the stripped version
                stripped_key = base_key[: -len(run_mode_suffix)]
                keys_to_try.append(stripped_key)
            else:
                # Key doesn't have the run mode suffix, try adding it
                keys_to_try.append(f"{base_key}{run_mode_suffix}")

        # Load known bad tests
        known_bad_tests_file = self._get_known_bad_tests_file()
        self._known_bad_test_regexes = self._get_test_regexes_from_file(
            file_path=known_bad_tests_file,
            test_dict_key="known_bad_tests",
            keys_to_try=keys_to_try,
        )

        # Load unsupported tests
        unsupported_tests_file = self._get_unsupported_tests_file()
        self._unsupported_test_regexes = self._get_test_regexes_from_file(
            file_path=unsupported_tests_file,
            test_dict_key="unsupported_tests",
            keys_to_try=keys_to_try,
        )

    def _parse_list_test_output(self, output: bytes) -> list[str]:
        ret = []
        class_name = None
        for line in output.decode("utf-8").split("\n"):
            if not line:
                continue
            # for tests that are templdated, gtest will print a comment of the
            # template. Example output:
            #
            # BcmMirrorTest/0.  # TypeParam = folly::IPAddressV4
            #   ResolvedSpanMirror
            #
            # In this case, we just need to ignore the comment (starts with '#')
            sanitized_line = line.split("#")[0].strip()
            if sanitized_line.endswith("."):
                class_name = sanitized_line[:-1]
            else:
                if not class_name:
                    raise RuntimeError("error")
                func_name = sanitized_line.strip()
                ret.append(f"{class_name}.{func_name}")

        return ret

    def _parse_gtest_run_output(self, test_output: bytes) -> list[GtestResult]:
        return GtestResult.parse_output(test_output)

    def _list_tests_to_run(self, test_filter: str) -> list[str]:
        output = subprocess.check_output(
            [
                self._get_test_binary_name(),
                "--gtest_list_tests",
                f"--gtest_filter={test_filter}",
            ]
        )
        return self._parse_list_test_output(output)

    def _test_matches_any_regex(self, test: str, regex_list: list[str]) -> bool:
        return test_matches_any_regex(test, regex_list)

    def _is_known_bad_test(self, test: str) -> bool:
        """Check if a test is in the known bad tests list."""
        return self._test_matches_any_regex(test, self._known_bad_test_regexes)

    def _is_unsupported_test(self, test: str) -> bool:
        """Check if a test is in the unsupported tests list."""
        return self._test_matches_any_regex(test, self._unsupported_test_regexes)

    def _get_tests_to_run(self) -> list[str]:
        # Filter syntax is -
        #   --filter=<include_regexes>-<exclude_regexes>
        #   in case of multiple regexes, each one should be separated by ':'
        #
        # For example, to run all tests matching "Vlan" and "Port" but
        # excluding "Mac" tests in the list is -
        #   --filter=*Vlan*:*Port*:-*Mac*
        #
        # Also, multiple '-' is allowed but all regexes following the first '-'
        # are part of exclude list.
        #
        # There are 4 variations of test filtering:
        # 1. Tests by filter without known bad
        # 2. Tests by filter with known bad
        # 3. All tests with known bad
        # 4. All tests without known bad
        args = self.args
        test_names = []
        if args.filter or args.filter_file:
            if args.filter_file:
                gtest_regexes = load_from_file(args.filter_file, args.profile)
                test_names = self._list_tests_to_run(":".join(gtest_regexes))
            elif args.filter:
                test_names = self._list_tests_to_run(args.filter)
        else:
            test_names = self._list_tests_to_run("*")
        test_filter = ""
        self._skipped_known_bad_tests = []
        for test_name in test_names:
            if self._is_known_bad_test(test_name):
                print(f"  >> SKIPPING (known bad)  : {test_name}")
                self._skipped_known_bad_tests.append(test_name)
                continue
            if self._is_unsupported_test(test_name):
                print(f"  >> SKIPPING (unsupported): {test_name}")
                self._skipped_known_bad_tests.append(test_name)
                continue
            test_filter += f"{test_name}:"
        if not test_filter:
            return []
        return self._list_tests_to_run(test_filter)

    def _restart_bcmsim(self, asic: str) -> None:
        try:
            subprocess.Popen(
                # avoid warmboot, so as to run test with coldboot init, warmboot shut down
                # as a workaround for intermittent unclean exit issue in OSS environment
                ["rm", "-f", "/dev/shm/fboss/warm_boot/can_warm_boot_0"]
            )
            subprocess.Popen(
                # command to start bcmsim service
                ["./runner.sh", "restart", "python3", "brcmsim.py", "-a", asic, "-s"]
            )
            time.sleep(60)
            print("Restarted bcmsim service", flush=True)
        except subprocess.CalledProcessError:
            print("Failed to restart bcmsim service", flush=True)

    def _capture_subprocess(self, cmd, timeout):
        """Run cmd, tee its stdout/stderr to the parent in real time, and
        return (returncode, timed_out, stdout_tail, stderr_tail).

        Memory is bounded by `StreamTee` (head + tail window per stream).
        On timeout the child is killed and reaped so the tee threads can
        drain the closed pipes and exit cleanly.
        """
        stdout_tee = StreamTee(sys.stdout.buffer.write)
        stderr_tee = StreamTee(sys.stderr.buffer.write)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env_var,
            bufsize=65536,
        )
        # daemon=True so a tee thread stuck in a slow `sys.stdout.buffer.write`
        # (e.g. blocked parent pipe) cannot wedge interpreter shutdown.
        t_out = threading.Thread(
            target=pipe_to_tee, args=(proc.stdout, stdout_tee), daemon=True
        )
        t_err = threading.Thread(
            target=pipe_to_tee, args=(proc.stderr, stderr_tee), daemon=True
        )
        t_out.start()
        t_err.start()

        timed_out = False
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            returncode = proc.wait()
            timed_out = True
        # Closed pipes unblock the tee threads; bound the join so a stuck
        # thread cannot wedge the runner.
        t_out.join(timeout=10)
        t_err.join(timeout=10)
        if t_out.is_alive() or t_err.is_alive():
            print(
                f"Warning: tee thread did not exit within 10s "
                f"(stdout_alive={t_out.is_alive()}, stderr_alive={t_err.is_alive()}); "
                f"continuing with captured snapshot.",
                flush=True,
            )
        sys.stdout.flush()
        sys.stderr.flush()
        return returncode, timed_out, stdout_tee.snapshot(), stderr_tee.snapshot()

    def _collect_rma_showtech(self, test_to_run: str) -> None:
        """Stream rma-showtech output to the test log on test failure."""
        # Collect broad platform diagnostics. Only the non-disruptive details
        # are gathered (i.e. no --disruptive) so collecting diagnostics does not
        # further perturb the DUT under test.
        cmd = ["rma-showtech", "--details", "all"]
        timeout_s = 300
        begin_marker = "########## BEGIN rma-showtech (test failed) ##########"
        end_marker = "########## END rma-showtech ##########"

        print(f"{begin_marker} for {test_to_run}", flush=True)
        try:
            returncode, timed_out, _, _ = self._capture_subprocess(cmd, timeout_s)
            if timed_out:
                print(f"rma-showtech timed out after {timeout_s}s", flush=True)
            elif returncode != 0:
                print(f"rma-showtech exited with code {returncode}", flush=True)
        except FileNotFoundError:
            print("rma-showtech binary not found; skipping diagnostics", flush=True)
        except Exception as e:  # must not mask the test failure
            print(f"Failed to run rma-showtech: {e}", flush=True)
        finally:
            print(end_marker, flush=True)

    @staticmethod
    def _port_in_use(port: int) -> bool:
        # SO_REUSEADDR so a TIME_WAIT socket doesn't read as busy; only an
        # actively bound agent does.
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("::", port))
                return False
            except OSError:
                return True

    def _wait_for_agent_thrift_ports_free(self) -> None:
        deadline = time.monotonic() + self.AGENT_PORT_FREE_TIMEOUT_S
        while True:
            busy = [p for p in self.AGENT_THRIFT_PORTS if self._port_in_use(p)]
            if not busy:
                return
            if time.monotonic() >= deadline:
                print(
                    "Warning: agent thrift port(s) "
                    f"{busy} still in use after {self.AGENT_PORT_FREE_TIMEOUT_S}s; "
                    "starting the test anyway",
                    flush=True,
                )
                return
            time.sleep(1)

    def _run_test(
        self,
        conf_file: str,
        test_prefix: str,
        test_to_run: str,
        setup_warmboot: bool,
        sai_replayer_logging_path: str | None = None,
    ) -> RunOutcome:
        args = self.args
        # Setup flags for the test binary before running the tests
        flags = [self.WARMBOOT_SETUP_OPTION] if setup_warmboot else []
        flags += self._get_sai_replayer_logging_flags(sai_replayer_logging_path)
        flags += self._get_sai_logging_flags()
        flags += ["--logging", args.fboss_logging]

        # Guard against a leftover XML from a prior run being mis-attributed:
        # callers already unlink before each call, but unlinking here too means
        # a future caller that forgets won't silently stamp this run's streams
        # onto the previous test's XML.
        with suppress(FileNotFoundError):
            os.unlink(self.TESTRESULT_CURRENT_RUN_FILE)

        # Wait for the previous test's agent to release the thrift ports before
        # launching, else the bind races and the agent aborts.
        self._wait_for_agent_thrift_ports_free()

        # monotonic for durations (immune to NTP step), wall-clock for the
        # core-dump-finder which compares against filesystem mtime.
        wall_start = time.time()
        mono_start = time.monotonic()
        test_run_cmd = self._get_test_run_cmd(conf_file, test_to_run, flags)
        print(f"Running command {test_run_cmd}", flush=True)
        emit_test_boundary(kind="START", test_name=test_to_run, prefix=test_prefix)

        returncode, timed_out, stdout_tail, stderr_tail = self._capture_subprocess(
            test_run_cmd, args.test_run_timeout
        )
        elapsed_sec = time.monotonic() - mono_start
        elapsed_ms = int(elapsed_sec * 1000)
        info = exit_info(returncode=returncode, timed_out=timed_out)

        xml_exists = os.path.exists(self.TESTRESULT_CURRENT_RUN_FILE)
        if info["kind"] == "FAIL" and xml_exists:
            inject_streams_into_xml(
                self.TESTRESULT_CURRENT_RUN_FILE, stdout_tail, stderr_tail
            )

        if info["kind"] in ("OK", "FAIL") and xml_exists:
            # Parse the real gtest output and tag each result with the
            # boot-phase prefix (cold_boot./warm_boot.).
            results = self._parse_gtest_run_output(stdout_tail)
            for result in results:
                result.test_name = test_prefix + result.test_name
            if results:
                outcome = RunOutcome(stdout_tail.decode("utf-8"), results)
            else:
                # No gtest result line found (e.g. --setup-for-warmboot causes
                # an early exit); synthesize a result so the test still appears
                # in the summary.
                status = GtestStatus.OK if info["kind"] == "OK" else GtestStatus.FAILED
                synthesized = GtestResult(test_prefix + test_to_run, status, elapsed_ms)
                outcome = RunOutcome(synthesized.as_log_line(), [synthesized])
        elif info["kind"] == "OK" and not xml_exists:
            synthesized = GtestResult(
                test_prefix + test_to_run, GtestStatus.OK, elapsed_ms
            )
            outcome = RunOutcome(synthesized.as_log_line(), [synthesized])
        else:
            # TIMEOUT, CRASH, or FAIL without a usable XML: write a synthetic
            # failure XML (with core-dump details on crash) so the failure is
            # still recorded in TESTRESULT_CURRENT_RUN_FILE, and synthesize the
            # matching result for the run summary.
            core_dump_path = (
                find_recent_core_dump(wall_start) if info["kind"] == "CRASH" else None
            )
            write_synthetic_failure_xml(
                xml_path=self.TESTRESULT_CURRENT_RUN_FILE,
                test_to_run=test_to_run,
                info=info,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                core_dump_path=core_dump_path,
                duration_sec=elapsed_sec,
            )
            if info["kind"] == "TIMEOUT":
                synthesized = GtestResult(
                    test_prefix + test_to_run,
                    GtestStatus.TIMEOUT,
                    args.test_run_timeout * 1000,
                )
            else:
                synthesized = GtestResult(
                    test_prefix + test_to_run, GtestStatus.FAILED, elapsed_ms
                )
            outcome = RunOutcome(synthesized.as_log_line(), [synthesized])

        # On any non-OK outcome, collect platform diagnostics from the DUT and
        # record them in the test log, inside this test's START/END boundary.
        if info["kind"] != "OK":
            self._collect_rma_showtech(test_to_run)

        emit_test_boundary(
            kind="END",
            test_name=test_to_run,
            prefix=test_prefix,
            info=info,
            duration_sec=elapsed_sec,
        )
        return outcome

    def _string_in_file(self, file_path: str, string: str) -> bool | None:
        try:
            with open(file_path) as file:
                file_contents = file.read()
            return string in file_contents
        except FileNotFoundError:
            print(f"File not found when replacing string: {file_path}")

    def _replace_string_in_file(
        self, file_path: str, old_str: str, new_str: str
    ) -> None:
        try:
            with open(file_path) as file:
                file_contents = file.read()

            new_file_contents = file_contents.replace(old_str, new_str)

            if new_file_contents != file_contents:
                with open(file_path, "w") as file:
                    file.write(new_file_contents)
                print(f"Replaced {old_str} by {new_str} in file {file_path}")
        except FileNotFoundError:
            print(f"File not found when replacing string: {file_path}")
        except Exception as e:
            print(f"Error when replacing string in {file_path}: {e!s}")

    def _backup_and_modify_config(self, conf_file: str) -> str:
        """Create a copy of the config and modify settings"""
        args = self.args
        if getattr(args, "run_on_reference_board", False):
            # Create a copy of the config file for modification
            try:
                # Create a modified copy in /tmp with standard name
                config_filename = os.path.basename(conf_file)
                _config_file_modified = f"/tmp/modified-{config_filename}"
                shutil.copy2(conf_file, _config_file_modified)

                print(
                    f"Using a modified config file {_config_file_modified} for test runs"
                )
                # Some platforms, like TH5 SVK, need to set
                # AUTOLOAD_BOARD_SETTINGS=1 to autodetect reference board
                self._replace_string_in_file(
                    _config_file_modified,
                    "AUTOLOAD_BOARD_SETTINGS: 0",
                    "AUTOLOAD_BOARD_SETTINGS: 1",
                )
                return _config_file_modified
            except Exception as e:
                print(f"Error creating config copy {conf_file}: {e!s}")
                return conf_file
        return conf_file

    def _apply_simulator_env(self, simulator: str | None) -> None:
        """Overlay simulator-specific env vars onto this run's environment."""
        if simulator in XGS_SIMULATOR_ASICS:
            self.env_var.update(XGS_SIMULATOR_ENV)
        elif simulator in DNX_SIMULATOR_ASICS:
            self.env_var.update(DNX_SIMULATOR_ENV)

    def _run_tests(
        self, tests_to_run: list[str], conf_file: str, args: Namespace
    ) -> tuple[list, list]:
        sai_replayer_logging = getattr(args, "sai_replayer_logging", None)
        simulator = getattr(args, "simulator", None)

        if sai_replayer_logging:
            if os.path.isdir(sai_replayer_logging) or os.path.isfile(
                sai_replayer_logging
            ):
                raise ValueError(
                    f"File or directory {sai_replayer_logging} already exists."
                    "Remove or specify another directory and retry. Exitting"
                )

            os.makedirs(sai_replayer_logging)
        self._apply_simulator_env(simulator)

        # Determine if tests need to be run with warmboot mode too
        warmboot = False
        if args.coldboot_only is False:
            warmboot = True

        if conf_file and not os.path.exists(conf_file):
            print(f"########## Required configuration file not found: {conf_file}")
            return [], []

        all_results: list[GtestResult] = []
        test_results = []
        try:
            test_binary_name = self._get_test_binary_name()
            file_name = os.path.basename(test_binary_name)
            disable_services(file_name)
            # Once-per-run setup hook (e.g. Fboss2IntegrationTestRunner detects/starts
            # prod agents and populates _switch_indexes). Other runners default to a
            # no-op _setup_run, so this is safe for every suite.
            self._setup_run(conf_file)
            num_tests = len(tests_to_run)
            for idx, test_to_run in enumerate(tests_to_run):
                test_prefix = self.COLDBOOT_PREFIX
                sai_replayer_log_path = self._get_sai_replayer_log_path(
                    test_prefix, test_to_run, sai_replayer_logging
                )
                # Run the test for coldboot verification
                self._setup_coldboot_test(sai_replayer_log_path)
                with suppress(FileNotFoundError):
                    os.unlink(self.TESTRESULT_CURRENT_RUN_FILE)
                print("########## Running test: " + test_to_run, flush=True)
                if simulator:
                    self._restart_bcmsim(simulator)
                run_outcome = self._run_test(
                    conf_file,
                    test_prefix,
                    test_to_run,
                    warmboot,  # setup_warmboot
                    sai_replayer_log_path,
                )
                print(
                    f"########## Coldboot test results ({idx + 1}/{num_tests}): {run_outcome.console_output}",
                    flush=True,
                )
                all_results.extend(run_outcome.results)
                test_results.append(
                    self.get_updated_test_result_with_classname_subscript("cold_boot")
                )

                # Run the test again for warmboot verification if the test supports it.
                # With --num-warmboot-iterations N, soak the test across N consecutive
                # warmboots; each iteration re-arms --setup-for-warmboot so the next boot
                # can warmboot, and we stop early on the first failure.
                _raw_wb_iters = getattr(args, "num_warmboot_iterations", 1)
                try:
                    # getattr on a Mock returns a Mock which isn't comparable to int.
                    # Coerce to int defensively; fall back to 1.
                    num_wb_iterations = (
                        _raw_wb_iters
                        if isinstance(_raw_wb_iters, int)
                        else int(_raw_wb_iters)
                    )
                except Exception:
                    num_wb_iterations = 1
                num_wb_iterations = max(1, num_wb_iterations)
                for wb_iter in range(num_wb_iterations):
                    if not (
                        warmboot and os.path.isfile(self._get_warmboot_check_file())
                    ):
                        break
                    # Re-arm warmboot for every iteration except the last so the next
                    # boot warmboots; the final iteration need not set up again.
                    setup_next_warmboot = wb_iter < num_wb_iterations - 1
                    test_prefix = (
                        self.WARMBOOT_PREFIX
                        if num_wb_iterations == 1
                        else f"{self.WARMBOOT_PREFIX}{wb_iter}."
                    )
                    sai_replayer_log_path = self._get_sai_replayer_log_path(
                        test_prefix, test_to_run, sai_replayer_logging
                    )
                    self._setup_warmboot_test(sai_replayer_log_path)
                    print(
                        "########## Verifying test with warmboot "
                        f"({wb_iter + 1}/{num_wb_iterations}): {test_to_run}",
                        flush=True,
                    )
                    run_outcome = self._run_test(
                        conf_file,
                        test_prefix,
                        test_to_run,
                        setup_next_warmboot,  # setup_warmboot
                        sai_replayer_log_path,
                    )
                    print(
                        f"########## Warmboot test results ({idx + 1}/{num_tests}, "
                        f"iter {wb_iter + 1}/{num_wb_iterations}): {run_outcome.console_output}",
                        flush=True,
                    )
                    all_results.extend(run_outcome.results)
                    test_results.append(
                        self.get_updated_test_result_with_classname_subscript(
                            "warm_boot"
                        )
                    )
                    # Stop the warmboot soak on first non-passing iteration.
                    # GtestStatus.OK is the passing status (displayed as "PASSED").
                    if any(r.status != GtestStatus.OK for r in run_outcome.results):
                        break
        finally:
            self._end_run()
            enable_services(file_name)
        return all_results, test_results

    def _print_output_summary(self, results: list[GtestResult]) -> None:
        ConsoleReporter().print_gtest_summary(results)
        CsvReporter().write_gtest_results(results)

    def _parse_test_result_xml(self, test_result_xml: str | None) -> ET.Element | None:
        """Safely parse a test result XML string"""
        if not test_result_xml:
            return None
        try:
            return ET.fromstring(test_result_xml)
        except ET.ParseError as e:
            print(f"Warning: Failed to parse test result XML: {e}")
            return None

    def _extract_timestamp_from_results(self, test_results: list[str | None]) -> str:
        """Extract the first valid timestamp from test results"""
        for result in test_results:
            root = self._parse_test_result_xml(result)
            if root is None:
                continue

            # Try to find timestamp in testsuites or testsuite element
            timestamp = root.get("timestamp")
            if timestamp:
                return timestamp

            # Check nested testsuite elements
            for testsuite in root.iter("testsuite"):
                timestamp = testsuite.get("timestamp")
                if timestamp:
                    return timestamp

        # Fallback to current time if no timestamp found
        print(
            "Warning: No timestamp found in test results, using current UTC time as fallback"
        )
        return datetime.now(timezone.utc).isoformat()

    def _aggregate_testsuite_info(self, test_results: list[str | None]) -> dict:
        """Aggregate test information from all test results using XML parsing"""
        info = {
            "tests": 0,
            "failures": 0,
            "skipped": 0,
            "disabled": 0,
            "errors": 0,
            "time": 0.0,
            "timestamp": self._extract_timestamp_from_results(test_results),
            "name": "AllTests",
        }

        for result in test_results:
            root = self._parse_test_result_xml(result)
            if root is None:
                continue

            # Find all testsuite elements and aggregate their attributes
            for testsuite in root.iter("testsuite"):
                info["tests"] += int(testsuite.get("tests", 0))
                info["failures"] += int(testsuite.get("failures", 0))
                info["skipped"] += int(testsuite.get("skipped", 0))
                info["disabled"] += int(testsuite.get("disabled", 0))
                info["errors"] += int(testsuite.get("errors", 0))
                info["time"] += float(testsuite.get("time", 0.0))

        return info

    @staticmethod
    def _testcase_status(testcase: ET.Element) -> str:
        for child in testcase:
            if child.tag in ("failure", "error", "skipped"):
                return child.tag
        return "passed"

    def _collapse_boot_phases(self, testcases: list[ET.Element]) -> list[ET.Element]:
        # One entry per logical (classname, name); worst status wins.
        # gtest's XML output sets `name` to the bare method and `classname` to
        # the suite, so different suites can share a method name (e.g.
        # VerifyWRR). Key on both so unrelated tests are not merged.
        best: dict[tuple[str, str], tuple[int, ET.Element]] = {}
        order: list[tuple[str, str]] = []
        for testcase in testcases:
            base = _BOOT_SUBSCRIPT_RE.sub("", testcase.get("name", ""))
            key = (testcase.get("classname", ""), base)
            rank = _STATUS_RANK.get(self._testcase_status(testcase), 1)
            if key not in best:
                order.append(key)
                best[key] = (rank, testcase)
            elif rank > best[key][0]:
                best[key] = (rank, testcase)
        collapsed = []
        for key in order:
            _, base = key
            testcase = best[key][1]
            testcase.set("name", base)
            collapsed.append(testcase)
        return collapsed

    def _build_skipped_known_bad_testcases(self) -> list[ET.Element]:
        testcases = []
        for full_name in self._skipped_known_bad_tests:
            suite_name, _, case_name = full_name.partition(".")
            if not case_name:
                suite_name = "Unknown"
            testcase = ET.Element(
                "testcase",
                name=full_name,
                classname=suite_name,
                time="0.0",
                status="notrun",
            )
            ET.SubElement(
                testcase,
                "skipped",
                message="known bad or unsupported test, filtered out before running",
            )
            testcases.append(testcase)
        return testcases

    def _write_results_to_xml(self, test_results: list[str | None]) -> None:
        output_xml = self.TESTRESULT_FILE
        info = self._aggregate_testsuite_info(test_results)

        raw_testcases: list[ET.Element] = []
        for result in test_results:
            root = self._parse_test_result_xml(result)
            if root is None:
                continue
            raw_testcases.extend(root.iter("testcase"))
        raw_testcases.extend(self._build_skipped_known_bad_testcases())
        collapsed = self._collapse_boot_phases(raw_testcases)

        counts = dict.fromkeys(("failure", "error", "skipped"), 0)
        for tc in collapsed:
            status = self._testcase_status(tc)
            if status in counts:
                counts[status] += 1

        testsuites = ET.Element("testsuites")
        testsuite = ET.SubElement(
            testsuites,
            "testsuite",
            tests=str(len(collapsed)),
            failures=str(counts["failure"]),
            disabled="0",
            errors=str(counts["error"]),
            skipped=str(counts["skipped"]),
            time=str(info["time"]),
            timestamp=info["timestamp"],
            name=info["name"],
        )
        for testcase in collapsed:
            testsuite.append(testcase)

        ET.indent(testsuites)
        with open(output_xml, "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(ET.tostring(testsuites, encoding="unicode"))

        print(f"\nTest result xml stored at: {output_xml}")

    def get_updated_test_result_with_classname_subscript(self, subscript):
        test_result = None
        try:
            with open(self.TESTRESULT_CURRENT_RUN_FILE, encoding="utf-8") as file:
                test_result = file.read()
                pattern = r'testcase name="([^"]*)"'
                match = re.search(pattern, test_result)
                if match:
                    test_result = re.sub(
                        pattern,
                        f'testcase name="{match.group(1)}[{subscript}]"',
                        test_result,
                    )
        except Exception as e:
            print(f"An error occurred while reading the file: {e}")
        return test_result

    def run_test(self, args: Namespace) -> None:
        self.args = args
        test_binary = self._get_test_binary_name()
        # Some runners return an absolute path (e.g. /opt/fboss/bin/sai_test-sai_impl);
        # others return a bare binary name resolved via $PATH (e.g. platform_hw_test).
        if os.path.isabs(test_binary):
            binary_found = os.path.isfile(test_binary)
        else:
            binary_found = shutil.which(test_binary) is not None
        if not binary_found:
            print(
                f"Error: test binary not found: {test_binary}\n"
                f"\tMake sure the binary is installed at the expected path."
            )
            return

        # Initialize test lists once at the start
        self._initialize_test_lists(args)

        if hasattr(args, "agent_run_mode"):
            _print_deprecation_banner(
                [
                    "NOTE: Default run mode is now multi_switch.",
                    "Mono mode is DEPRECATED and will be removed in a future.",
                ]
            )
        tests_to_run = self._get_tests_to_run()
        tests_to_run = self._filter_tests(tests_to_run)

        # Check if tests need to be run or only listed
        if (
            args.list_tests is False
            and getattr(args, "list_tests_for_features", None) is None
        ):
            start_time = datetime.now()
            original_conf_file = (
                args.config if (args.config is not None) else self._get_config_path()
            )
            conf_file = self._backup_and_modify_config(original_conf_file)
            output, test_results = self._run_tests(tests_to_run, conf_file, args)
            end_time = datetime.now()
            delta_time = end_time - start_time
            print(
                f"Running all tests took {delta_time} between {start_time} and {end_time}",
                flush=True,
            )
            # output is the list[GtestResult] for the console/CSV summary;
            # test_results is the list of per-test XML strings for the
            # aggregated XML report.
            self._print_output_summary(output)
            self._write_results_to_xml(test_results)
        else:
            # Print the filtered tests
            for test in tests_to_run:
                print(test)
