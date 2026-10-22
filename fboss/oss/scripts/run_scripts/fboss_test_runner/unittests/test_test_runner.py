# Copyright Meta Platforms, Inc. and affiliates.
# @noautodeps
"""Tests for TestRunner orchestration: _run_test, _run_tests, and related
end-to-end execution paths (gtest output post-processing, synthesize-OK
fallback for early-exit binaries, warmboot loop, timeout handling, config
backup, filter merging), plus the load_from_file helper consumed
by _get_tests_to_run via args.filter_file."""

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from argparse import Namespace
from unittest.mock import ANY, MagicMock, patch

import pytest

from fboss_test_runner.errors import TestRunnerUsageError
from fboss_test_runner.result_types import GtestResult, GtestStatus, RunOutcome
from fboss_test_runner.runners.utils import load_from_file
from fboss_test_runner.tier_selection import TestCapability, TestTier


class TestLoadFromFile:
    """load_from_file is a module-level helper used by _get_tests_to_run
    (args.filter_file path) and BenchmarkTestRunner. Tests live here next to
    the consumer."""

    def test_basic(self):
        """Test loading entries from a file with comments and blank lines"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("# Comment line\n")
            f.write("entry1\n")
            f.write("\n")
            f.write("entry2\n")
            f.write("# Another comment\n")
            f.write("entry3\n")
            temp_file = f.name
        try:
            result = load_from_file(temp_file)
            assert result == ["entry1", "entry2", "entry3"]
        finally:
            os.unlink(temp_file)

    def test_nonexistent(self):
        """Test loading from a nonexistent file returns empty list"""
        result = load_from_file("/nonexistent/path.conf")
        assert result == []

    def test_empty(self):
        """Test loading from an empty file returns empty list"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            temp_file = f.name
        try:
            result = load_from_file(temp_file)
            assert result == []
        finally:
            os.unlink(temp_file)

    def test_with_profile(self):
        """Test loading with profile filters to matching tagged lines"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("entry_untagged\n")
            f.write("entry_tagged_p1 p1\n")
            f.write("entry_tagged_p2 p2\n")
            f.write("entry_tagged_t t\n")
            temp_file = f.name
        try:
            result = load_from_file(temp_file, profile="p1")
            assert result == ["entry_tagged_p1"]
        finally:
            os.unlink(temp_file)

    def test_no_profile_includes_untagged_and_t(self):
        """Test that without profile, untagged and t-tagged lines are included"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("entry_untagged\n")
            f.write("entry_tagged_p1 p1\n")
            f.write("entry_tagged_t t\n")
            temp_file = f.name
        try:
            result = load_from_file(temp_file)
            assert result == ["entry_untagged", "entry_tagged_t"]
        finally:
            os.unlink(temp_file)

    def test_comments_and_whitespace(self):
        """Test that comments and whitespace-only lines are skipped"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".conf") as f:
            f.write("# full comment\n")
            f.write("   \n")
            f.write("\n")
            f.write("  # indented comment\n")
            f.write("entry1\n")
            temp_file = f.name
        try:
            result = load_from_file(temp_file)
            assert result == ["entry1"]
        finally:
            os.unlink(temp_file)


def _make_capture_writing(stdout_bytes: bytes, runner, xml_to_write: bytes | None):
    """Build a fake `_capture_subprocess` that optionally writes a gtest XML
    to runner.TESTRESULT_CURRENT_RUN_FILE and returns
    (returncode=0, timed_out=False, stdout_bytes, b"").
    """

    def fake_capture(cmd, timeout):  # noqa: ARG001 - signature mirrors _capture_subprocess
        if xml_to_write is not None:
            with open(runner.TESTRESULT_CURRENT_RUN_FILE, "wb") as f:
                f.write(xml_to_write)
        return 0, False, stdout_bytes, b""

    return fake_capture


_STUB_GTEST_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="1" failures="0" errors="0" time="0.1">
  <testsuite name="HwFooTest" tests="1" failures="0">
    <testcase name="Bar" classname="HwFooTest" time="0.1" status="run"/>
  </testsuite>
</testsuites>
"""


class TestTierFilterComposition:
    def test_prepare_tests_applies_tier_filter_after_runner_filter(self, runner):
        args = Namespace(tier="0")
        with (
            patch("shutil.which", return_value="/opt/fboss/bin/test_binary"),
            patch.object(runner, "_initialize_test_lists"),
            patch.object(
                runner, "_get_tests_to_run", return_value=["Suite.B", "Suite.A"]
            ),
            patch.object(
                runner, "_filter_tests", return_value=["Suite.A"]
            ) as runner_filter,
            patch.object(
                runner, "_filter_tests_for_tier", return_value=["Suite.A"]
            ) as tier_filter,
        ):
            assert runner._prepare_tests(args) == ["Suite.A"]

        runner_filter.assert_called_once_with(["Suite.B", "Suite.A"])
        tier_filter.assert_called_once_with(["Suite.A"], TestTier.T0)

    def test_base_runner_rejects_tier_selection(self, runner):
        runner.args = Namespace(command="unsupported")
        with pytest.raises(TestRunnerUsageError, match="not supported for unsupported"):
            runner._filter_tests_for_tier([], TestTier.T0)

    @pytest.mark.parametrize(
        "requested_tier,expected",
        [(TestTier.T0, ["Suite.B", "Suite.A"]), (TestTier.T1, [])],
    )
    def test_uniform_tier_filters_without_metadata(
        self, runner, requested_tier, expected
    ):
        tests = ["Suite.B", "Suite.A"]
        with (
            patch.object(runner, "_get_uniform_test_tier", return_value=TestTier.T0),
            patch.object(runner, "_get_tier_metadata_file") as metadata_file,
        ):
            assert runner._filter_tests_for_tier(tests, requested_tier) == expected

        metadata_file.assert_not_called()

    def test_metadata_filter_expands_patterns_and_intersects_candidates(
        self, runner, tmp_path
    ):
        metadata = tmp_path / "test_metadata.json"
        metadata.write_text(
            json.dumps(
                {
                    "rules": [
                        {
                            "testNamePattern": "EmptyTest.*",
                            "tier": "T0",
                            "requiredCapabilities": [],
                            "profiles": [],
                        },
                        {
                            "testNamePattern": "CapableTest.*",
                            "tier": "T0",
                            "requiredCapabilities": [TestCapability.TRANSCEIVER.value],
                            "profiles": [],
                        },
                        {
                            "testNamePattern": "OtherTier.*",
                            "tier": "T1",
                            "requiredCapabilities": [],
                            "profiles": [],
                        },
                    ]
                }
            )
        )
        candidates = ["Unrelated.Test", "CapableTest.Case", "EmptyTest.CheckInit"]
        with (
            patch.object(runner, "_get_tier_metadata_file", return_value=str(metadata)),
            patch.object(
                runner,
                "_get_available_test_capabilities",
                return_value=(TestCapability.TRANSCEIVER,),
            ),
            patch.object(
                runner,
                "_list_tests_to_run",
                return_value=["EmptyTest.CheckInit", "CapableTest.Case"],
            ) as expand_patterns,
        ):
            selected = runner._filter_tests_for_tier(candidates, TestTier.T0)

        expand_patterns.assert_called_once_with("EmptyTest.*:CapableTest.*")
        assert selected == ["CapableTest.Case", "EmptyTest.CheckInit"]

    def test_metadata_filter_reports_missing_file(self, runner, tmp_path):
        missing = str(tmp_path / "missing.json")
        with (
            patch.object(runner, "_get_tier_metadata_file", return_value=missing),
            pytest.raises(TestRunnerUsageError, match="Unable to load test metadata"),
        ):
            runner._filter_tests_for_tier([], TestTier.T0)

    def test_metadata_filter_skips_gtest_when_no_patterns_match(self, runner, tmp_path):
        metadata = tmp_path / "test_metadata.json"
        metadata.write_text(
            json.dumps(
                {
                    "rules": [
                        {
                            "testNamePattern": "OtherTier.*",
                            "tier": "T1",
                            "requiredCapabilities": [],
                            "profiles": [],
                        }
                    ]
                }
            )
        )
        with (
            patch.object(runner, "_get_tier_metadata_file", return_value=str(metadata)),
            patch.object(runner, "_list_tests_to_run") as expand_patterns,
        ):
            assert runner._filter_tests_for_tier(["Suite.Test"], TestTier.T0) == []

        expand_patterns.assert_not_called()


class TestRunTestGtestFallback:
    """Tests for _run_test gtest output post-processing (prefix injection,
    synthesize-OK fallback for empty output)."""

    def test_preserves_skipped_does_not_synthesize_ok(
        self, runner, mock_args, tmp_path
    ):
        """End-to-end: a SKIPPED gtest result must not be rewritten as OK."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        # _get_test_run_cmd reads args off the runner instance (self.args);
        # patch it on the runner for the duration of the call.
        with (
            patch.object(runner, "args", new=mock_args),
            patch.object(
                runner,
                "_capture_subprocess",
                new=_make_capture_writing(
                    b"[  SKIPPED ] HwFooTest.Bar (5 ms)\n", runner, _STUB_GTEST_XML
                ),
            ),
        ):
            outcome = runner._run_test(
                conf_file="dummy.conf",
                test_prefix="cold_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=False,
            )
        assert len(outcome.results) == 1
        result = outcome.results[0]
        assert result.status == GtestStatus.SKIPPED
        assert result.test_name == "cold_boot.HwFooTest.Bar"
        assert result.filter_name == "HwFooTest.Bar"
        # Critical: the fallback must NOT have rewritten this to OK.
        assert result.status != GtestStatus.OK

    def test_synthesize_ok_when_no_gtest_line(self, runner, mock_args, tmp_path):
        """Fallback path still works: empty output (e.g. --setup-for-warmboot early
        exit) should still synthesize an OK result so the test isn't lost from
        the summary."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        with (
            patch.object(runner, "args", new=mock_args, create=True),
            patch.object(
                runner,
                "_capture_subprocess",
                new=_make_capture_writing(b"", runner, _STUB_GTEST_XML),
            ),
        ):
            outcome = runner._run_test(
                conf_file="dummy.conf",
                test_prefix="warm_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=True,
            )
        assert len(outcome.results) == 1
        result = outcome.results[0]
        assert result.status == GtestStatus.OK
        assert result.test_name == "warm_boot.HwFooTest.Bar"
        assert result.filter_name == "HwFooTest.Bar"


class TestRunTestTimeout:
    """Test that a timed-out capture is converted to a TIMEOUT result so the
    test surfaces in the summary."""

    def test_timeout_synthesizes_timeout_line(self, runner, mock_args, tmp_path):
        # The TIMEOUT branch writes a synthetic-failure XML, so point the
        # result file at a writable tmp location.
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        mock_args.test_run_timeout = 300

        def fake_capture(cmd, timeout):  # noqa: ARG001 - mirrors _capture_subprocess
            # returncode is ignored once timed_out is True (see exit_info).
            return -9, True, b"", b""

        with (
            patch.object(runner, "args", new=mock_args, create=True),
            patch.object(runner, "_capture_subprocess", new=fake_capture),
        ):
            outcome = runner._run_test(
                conf_file="dummy.conf",
                test_prefix="cold_boot.",
                test_to_run="HwSlowTest.Slow",
                setup_warmboot=False,
            )
        assert len(outcome.results) == 1
        result = outcome.results[0]
        # Critical: timeout must produce a TIMEOUT result, NOT be silently
        # dropped or rewritten as OK.
        assert result.status == GtestStatus.TIMEOUT
        assert result.test_name == "cold_boot.HwSlowTest.Slow"
        assert result.filter_name == "HwSlowTest.Slow"
        # Duration reported is timeout_in_second * 1000.
        assert result.duration_ms == 300000


class TestRunTestsWarmboot:
    """Tests for _run_tests cold→warm orchestration."""

    def _make_args(self, mock_args, coldboot_only):
        mock_args.coldboot_only = coldboot_only
        mock_args.sai_replayer_logging = None
        mock_args.simulator = None
        mock_args.sai_logging = "WARN"
        mock_args.fboss_logging = "WARN"
        mock_args.test_run_timeout = 300
        mock_args.num_warmboot_iterations = 1
        return mock_args

    def _make_conf(self, tmp_path):
        # _run_tests early-returns when conf_file does not exist on disk.
        conf = tmp_path / "test.conf"
        conf.write_text("")
        return str(conf)

    def test_warmboot_runs_both_phases_when_check_file_present(
        self, runner, mock_args, tmp_path
    ):
        check_file = tmp_path / "can_warm_boot"
        check_file.write_text("")
        runner._get_warmboot_check_file = lambda: str(check_file)
        args = self._make_args(mock_args, coldboot_only=False)
        conf = self._make_conf(tmp_path)

        with (
            patch.object(
                runner,
                "_run_test",
                return_value=RunOutcome(
                    "[ OK ] x.HwT.t (1 ms)", [GtestResult("x.HwT.t", GtestStatus.OK, 1)]
                ),
            ) as mock_run,
            patch.object(runner, "_setup_coldboot_test"),
            patch.object(runner, "_setup_warmboot_test"),
            patch.object(runner, "_end_run"),
        ):
            all_results, _ = runner._run_tests(["HwT.t"], conf, args)

        # 1 cold + 1 warm = 2 invocations, 2 results.
        assert mock_run.call_count == 2
        assert len(all_results) == 2
        prefixes = [call.args[1] for call in mock_run.call_args_list]
        assert prefixes == [runner.COLDBOOT_PREFIX, runner.WARMBOOT_PREFIX]

    def test_coldboot_only_skips_warmboot(self, runner, mock_args, tmp_path):
        # Even when the check file exists, --coldboot_only must skip warmboot.
        check_file = tmp_path / "can_warm_boot"
        check_file.write_text("")
        runner._get_warmboot_check_file = lambda: str(check_file)
        args = self._make_args(mock_args, coldboot_only=True)
        conf = self._make_conf(tmp_path)

        with (
            patch.object(
                runner,
                "_run_test",
                return_value=RunOutcome(
                    "[ OK ] x.HwT.t (1 ms)", [GtestResult("x.HwT.t", GtestStatus.OK, 1)]
                ),
            ) as mock_run,
            patch.object(runner, "_setup_coldboot_test"),
            patch.object(runner, "_setup_warmboot_test") as mock_warm_setup,
            patch.object(runner, "_end_run"),
        ):
            all_results, _ = runner._run_tests(["HwT.t"], conf, args)

        assert mock_run.call_count == 1
        assert len(all_results) == 1
        mock_warm_setup.assert_not_called()

    def test_warmboot_skipped_when_check_file_missing(
        self, runner, mock_args, tmp_path
    ):
        # Regression for the "warmboot file path mismatch" failure mode:
        # if _get_warmboot_check_file points at a path that doesn't exist
        # (e.g. wrong switch_index for the run mode), the warmboot pass is
        # silently skipped — no warmboot result will appear in the summary.
        missing = tmp_path / "does_not_exist"
        runner._get_warmboot_check_file = lambda: str(missing)
        args = self._make_args(mock_args, coldboot_only=False)
        conf = self._make_conf(tmp_path)

        with (
            patch.object(
                runner,
                "_run_test",
                return_value=RunOutcome(
                    "[ OK ] x.HwT.t (1 ms)", [GtestResult("x.HwT.t", GtestStatus.OK, 1)]
                ),
            ) as mock_run,
            patch.object(runner, "_setup_coldboot_test"),
            patch.object(runner, "_setup_warmboot_test") as mock_warm_setup,
            patch.object(runner, "_end_run"),
        ):
            all_results, _ = runner._run_tests(["HwT.t"], conf, args)

        # Warmboot was requested (coldboot_only=False) but check file is
        # missing → only the coldboot pass runs.
        assert mock_run.call_count == 1
        assert len(all_results) == 1
        mock_warm_setup.assert_not_called()


class TestSimulatorEnv:
    """_apply_simulator_env overlays simulator vars onto a per-instance env
    copy, so simulator runs never leak env across runner instances (the env
    used to live on a shared ClassVar)."""

    def test_xgs_overlay(self, runner):
        runner._apply_simulator_env("th4")
        assert runner.env_var["BCM_SIM_PATH"] == "1"
        assert runner.env_var["SOC_TARGET_SERVER"] == "127.0.0.1"
        assert runner.env_var["SOC_TARGET_PORT"] == "22222"

    def test_dnx_overlay(self, runner):
        runner._apply_simulator_env("j3")
        assert runner.env_var["ADAPTER_DEVID_0"] == "8860"
        assert runner.env_var["SOC_TARGET_SERVER"] == "localhost"
        assert runner.env_var["SAI_BOOT_FLAGS"] == "0x1020000"

    def test_no_simulator_leaves_env_unchanged(self, runner):
        before = dict(runner.env_var)
        runner._apply_simulator_env(None)
        assert runner.env_var == before

    def test_env_is_per_instance_no_leak(self, runner):
        # Applying simulator env to one runner must not leak onto a
        # separate instance.
        other = type(runner)()
        assert "SOC_TARGET_PORT" not in other.env_var
        runner._apply_simulator_env("th4")
        assert "SOC_TARGET_PORT" in runner.env_var
        assert "SOC_TARGET_PORT" not in other.env_var


class TestPrepareConfigForRun:
    """Test that _prepare_config_for_run creates a retained config and
    rewrites AUTOLOAD_BOARD_SETTINGS when --run-on-reference-board is set.
    Exercises _string_in_file + _replace_string_in_file transitively."""

    def test_reference_board_creates_modified_copy(self, runner, tmp_path):
        conf = tmp_path / "platform.materialized_JSON"
        conf.write_text("AUTOLOAD_BOARD_SETTINGS: 0\nother: value\n")

        generated_root = tmp_path / "generated_configs"
        modified_path = generated_root / "sai" / conf.name
        args = MagicMock()
        args.command = "sai"
        args.config = str(conf)
        args.run_on_reference_board = True
        with (
            patch.object(runner, "args", new=args, create=True),
            patch(
                "fboss_test_runner.runners.test_runner.GENERATED_CONFIG_ROOT",
                str(generated_root),
            ),
        ):
            returned = runner._prepare_config_for_run()

        assert returned == str(modified_path)
        assert modified_path.is_file()
        new_contents = modified_path.read_text()
        assert "AUTOLOAD_BOARD_SETTINGS: 1" in new_contents
        assert "AUTOLOAD_BOARD_SETTINGS: 0" not in new_contents
        # Original must be untouched.
        assert "AUTOLOAD_BOARD_SETTINGS: 0" in conf.read_text()

    def test_no_reference_board_returns_original_unmodified(self, runner, tmp_path):
        conf = tmp_path / "platform.materialized_JSON"
        conf.write_text("AUTOLOAD_BOARD_SETTINGS: 0\n")
        args = MagicMock()
        args.config = str(conf)
        args.run_on_reference_board = False
        with patch.object(runner, "args", new=args, create=True):
            returned = runner._prepare_config_for_run()
        assert returned == str(conf)
        # The original contents remain unchanged.
        assert "AUTOLOAD_BOARD_SETTINGS: 0" in conf.read_text()


class TestGetTestsToRunFilter:
    def _make_args(self, **overrides):
        args = MagicMock()
        args.filter = None
        args.filter_file = None
        args.profile = None
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def test_filter_file_overrides_filter_and_joins_with_colon(self, runner):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write("HwVlan* default\n")
            f.write("HwAcl* default\n")
            filter_file_path = f.name

        try:
            args = self._make_args(
                filter="ignored_when_filter_file_set",
                filter_file=filter_file_path,
                profile="default",
            )
            with (
                patch.object(runner, "args", new=args, create=True),
                patch.object(
                    runner, "_list_tests_to_run", return_value=["HwVlanTest.A"]
                ) as mock_list,
                patch.object(runner, "_is_known_bad_test", return_value=False),
                patch.object(runner, "_is_unsupported_test", return_value=False),
            ):
                runner._get_tests_to_run()

            first_filter = mock_list.call_args_list[0].args[0]
            assert ":" in first_filter
            assert "HwVlan*" in first_filter
            assert "HwAcl*" in first_filter
            assert "ignored_when_filter_file_set" not in first_filter
        finally:
            os.unlink(filter_file_path)

    def test_known_bad_tests_excluded_from_final_filter(self, runner):
        listed = ["HwVlanTest.Delete", "HwRouteTest.Add"]

        def fake_is_known_bad(test):
            return test == "HwVlanTest.Delete"

        args = self._make_args()
        with (
            patch.object(runner, "args", new=args, create=True),
            patch.object(
                runner, "_list_tests_to_run", side_effect=[listed, ["HwRouteTest.Add"]]
            ) as mock_list,
            patch.object(runner, "_is_known_bad_test", side_effect=fake_is_known_bad),
            patch.object(runner, "_is_unsupported_test", return_value=False),
        ):
            result = runner._get_tests_to_run()

        assert mock_list.call_args_list[0].args[0] == "*"
        second_filter = mock_list.call_args_list[1].args[0]
        assert "HwRouteTest.Add" in second_filter
        assert "HwVlanTest.Delete" not in second_filter
        assert result == ["HwRouteTest.Add"]

    def test_skipped_known_bad_names_are_recorded(self, runner):
        # All dropped -> empty run list, but names still captured.
        listed = ["HwVlanTest.Delete", "HwMirrorTest.Span"]

        def fake_is_known_bad(test):
            return test == "HwVlanTest.Delete"

        def fake_is_unsupported(test):
            return test == "HwMirrorTest.Span"

        args = self._make_args()
        with (
            patch.object(runner, "args", new=args, create=True),
            patch.object(runner, "_list_tests_to_run", return_value=listed),
            patch.object(runner, "_is_known_bad_test", side_effect=fake_is_known_bad),
            patch.object(
                runner, "_is_unsupported_test", side_effect=fake_is_unsupported
            ),
        ):
            result = runner._get_tests_to_run()

        assert result == []
        assert runner._skipped_known_bad_tests == [
            "HwVlanTest.Delete",
            "HwMirrorTest.Span",
        ]


class TestWriteResultsRecordsSkipped:
    """Filtered-out known-bad/unsupported tests are recorded as <skipped>."""

    def test_all_filtered_records_skipped_count_and_cases(self, runner, tmp_path):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = ["HwVlanTest.Delete", "HwMirrorTest.Span"]

        runner._write_results_to_xml([])  # nothing ran

        root = ET.parse(runner.TESTRESULT_FILE).getroot()
        suite = root.find("testsuite")
        assert suite.get("tests") == "2"
        assert suite.get("skipped") == "2"
        assert suite.get("failures") == "0"
        assert suite.get("errors") == "0"

        skipped_cases = [
            tc for tc in suite.iter("testcase") if tc.find("skipped") is not None
        ]
        assert len(skipped_cases) == 2
        recorded = {(tc.get("classname"), tc.get("name")) for tc in skipped_cases}
        assert recorded == {
            ("HwVlanTest", "HwVlanTest.Delete"),
            ("HwMirrorTest", "HwMirrorTest.Span"),
        }

    def test_skipped_added_on_top_of_real_results(self, runner, tmp_path):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = ["HwVlanTest.Delete"]
        ran = (
            '<testsuites tests="1" failures="0" errors="0" time="0.1">'
            '<testsuite name="HwFooTest" tests="1" failures="0" skipped="0" errors="0" time="0.1">'
            '<testcase name="Bar" classname="HwFooTest" time="0.1" status="run"/>'
            "</testsuite></testsuites>"
        )
        runner._write_results_to_xml([ran])
        suite = ET.parse(runner.TESTRESULT_FILE).getroot().find("testsuite")
        assert suite.get("tests") == "2"
        assert suite.get("skipped") == "1"


def _phase_result(suite: str, method: str, phase: str, outcome: str = "pass") -> str:
    inner = {"pass": "", "fail": '<failure message="boom"/>', "skip": "<skipped/>"}[
        outcome
    ]
    fails = "1" if outcome == "fail" else "0"
    return (
        f'<testsuites tests="1" failures="{fails}" errors="0" time="0.1">'
        f'<testsuite name="{suite}" tests="1" failures="{fails}" skipped="0" '
        f'errors="0" time="0.1">'
        f'<testcase name="{suite}.{method}[{phase}]" classname="{suite}" '
        f'time="0.1" status="run">{inner}</testcase>'
        "</testsuite></testsuites>"
    )


class TestWriteResultsCollapsesBootPhases:
    def _suite(self, runner, tmp_path, results):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = []
        runner._write_results_to_xml(results)
        return ET.parse(runner.TESTRESULT_FILE).getroot().find("testsuite")

    def test_cold_and_warm_collapse_to_one(self, runner, tmp_path):
        suite = self._suite(
            runner,
            tmp_path,
            [
                _phase_result("AgentT", "M", "cold_boot", "fail"),
                _phase_result("AgentT", "M", "warm_boot", "fail"),
            ],
        )
        assert suite.get("tests") == "1"
        assert suite.get("failures") == "1"
        cases = list(suite.iter("testcase"))
        assert len(cases) == 1
        assert cases[0].get("name") == "AgentT.M"

    def test_pass_and_fail_same_total(self, runner, tmp_path):
        green = self._suite(
            runner, tmp_path, [_phase_result("AgentT", "M", "warm_boot", "pass")]
        )
        red = self._suite(
            runner,
            tmp_path,
            [
                _phase_result("AgentT", "M", "cold_boot", "fail"),
                _phase_result("AgentT", "M", "warm_boot", "fail"),
            ],
        )
        assert green.get("tests") == red.get("tests") == "1"
        assert green.get("failures") == "0"
        assert red.get("failures") == "1"

    def test_worst_status_wins(self, runner, tmp_path):
        suite = self._suite(
            runner,
            tmp_path,
            [
                _phase_result("AgentT", "M", "cold_boot", "pass"),
                _phase_result("AgentT", "M", "warm_boot", "fail"),
            ],
        )
        assert suite.get("tests") == "1"
        assert suite.get("failures") == "1"

    def test_cold_only_counted_once(self, runner, tmp_path):
        suite = self._suite(
            runner, tmp_path, [_phase_result("AgentScale", "Max", "cold_boot", "pass")]
        )
        assert suite.get("tests") == "1"
        assert suite.get("failures") == "0"

    def test_duplicate_known_bad_deduped(self, runner, tmp_path):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = [
            "AgentHwMirrorTest.HwMirrorStat",
            "AgentHwMirrorTest.HwMirrorStat",
        ]
        runner._write_results_to_xml([])
        suite = ET.parse(runner.TESTRESULT_FILE).getroot().find("testsuite")
        assert suite.get("tests") == "1"
        assert suite.get("skipped") == "1"

    def test_run_skip_and_phases_combined(self, runner, tmp_path):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = ["AgentHw.Bad", "AgentHw.Bad"]
        runner._write_results_to_xml(
            [
                _phase_result("AgentA", "P", "warm_boot", "pass"),
                _phase_result("AgentB", "F", "cold_boot", "fail"),
                _phase_result("AgentB", "F", "warm_boot", "fail"),
            ]
        )
        suite = ET.parse(runner.TESTRESULT_FILE).getroot().find("testsuite")
        assert suite.get("tests") == "3"
        assert suite.get("failures") == "1"
        assert suite.get("skipped") == "1"


def _gtest_phase_result(
    suite: str, method: str, phase: str, outcome: str = "pass"
) -> str:
    # Mirrors real gtest --gtest_output=xml: `name` is the bare method and
    # `classname` is the suite (get_updated_test_result_with_classname_subscript
    # then appends the boot-phase subscript to `name`).
    inner = {"pass": "", "fail": '<failure message="boom"/>', "skip": "<skipped/>"}[
        outcome
    ]
    fails = "1" if outcome == "fail" else "0"
    return (
        f'<testsuites tests="1" failures="{fails}" errors="0" time="0.1">'
        f'<testsuite name="{suite}" tests="1" failures="{fails}" skipped="0" '
        f'errors="0" time="0.1">'
        f'<testcase name="{method}[{phase}]" classname="{suite}" '
        f'time="0.1" status="run">{inner}</testcase>'
        "</testsuite></testsuites>"
    )


class TestCollapseKeysOnSuiteAndMethod:
    def _suite(self, runner, tmp_path, results):
        runner.TESTRESULT_FILE = str(tmp_path / "tr.xml")
        runner._skipped_known_bad_tests = []
        runner._write_results_to_xml(results)
        return ET.parse(runner.TESTRESULT_FILE).getroot().find("testsuite")

    def test_same_method_different_suites_not_merged(self, runner, tmp_path):
        # Two distinct tests sharing a method name must stay separate; the
        # failing one must not be masked by the passing one.
        suite = self._suite(
            runner,
            tmp_path,
            [
                _gtest_phase_result(
                    "AgentNetworkAIQosSchedulerTest", "VerifyWRR", "cold_boot", "pass"
                ),
                _gtest_phase_result(
                    "AgentNetworkAIQosSchedulerTest", "VerifyWRR", "warm_boot", "pass"
                ),
                _gtest_phase_result(
                    "AgentOlympicQosSchedulerTest", "VerifyWRR", "cold_boot", "pass"
                ),
                _gtest_phase_result(
                    "AgentOlympicQosSchedulerTest", "VerifyWRR", "warm_boot", "fail"
                ),
            ],
        )
        assert suite.get("tests") == "2"
        assert suite.get("failures") == "1"
        cases = list(suite.iter("testcase"))
        assert {c.get("classname") for c in cases} == {
            "AgentNetworkAIQosSchedulerTest",
            "AgentOlympicQosSchedulerTest",
        }

    def test_two_failing_same_method_counted_separately(self, runner, tmp_path):
        suite = self._suite(
            runner,
            tmp_path,
            [
                _gtest_phase_result(
                    "SuiteA", "VerifyDscpQueueMapping", "cold_boot", "fail"
                ),
                _gtest_phase_result(
                    "SuiteB", "VerifyDscpQueueMapping", "cold_boot", "fail"
                ),
            ],
        )
        assert suite.get("tests") == "2"
        assert suite.get("failures") == "2"

    def test_phases_still_collapse_per_suite(self, runner, tmp_path):
        suite = self._suite(
            runner,
            tmp_path,
            [
                _gtest_phase_result("SuiteA", "M", "cold_boot", "pass"),
                _gtest_phase_result("SuiteA", "M", "warm_boot", "fail"),
            ],
        )
        assert suite.get("tests") == "1"
        assert suite.get("failures") == "1"
        cases = list(suite.iter("testcase"))
        assert len(cases) == 1
        assert cases[0].get("name") == "M"


class TestCollectRmaShowtechOnFail:
    """rma-showtech diagnostics collection on test failure (_run_test hook and
    _collect_rma_showtech behavior)."""

    def test_runs_rma_showtech_nondisruptive(self, runner):
        """rma-showtech runs with '--details all' and without '--disruptive' so
        diagnostics don't further perturb the DUT."""
        with patch.object(
            runner, "_capture_subprocess", return_value=(0, False, b"", b"")
        ) as mock_capture:
            runner._collect_rma_showtech("HwFooTest.Bar", 1791348080.7)
        mock_capture.assert_called_once()
        cmd = mock_capture.call_args.args[0]
        assert cmd == ["rma-showtech", "--details", "all", "--since", "1791348020"]
        assert "--disruptive" not in cmd

    def test_windows_history_to_test_start_minus_margin(self, runner):
        """A failure collects history only from shortly before its test began."""
        with patch.object(
            runner, "_capture_subprocess", return_value=(0, False, b"", b"")
        ) as mock_capture:
            runner._collect_rma_showtech("HwFooTest.Bar", 1791348080.7)
        assert mock_capture.call_args.args[0] == [
            "rma-showtech",
            "--details",
            "all",
            "--since",
            "1791348020",
        ]

    def test_missing_binary_does_not_raise(self, runner):
        """A missing rma-showtech binary must not mask the underlying test
        failure."""
        with patch.object(runner, "_capture_subprocess", side_effect=FileNotFoundError):
            # Must not raise.
            runner._collect_rma_showtech("HwFooTest.Bar", 1791348080.7)

    def test_run_test_collects_on_failure(self, runner, mock_args, tmp_path):
        """_run_test triggers rma-showtech collection on a non-OK outcome."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")

        def fake_capture(cmd, timeout):  # noqa: ARG001 - mirrors _capture_subprocess
            # Non-zero return code with no XML => FAIL outcome.
            return 1, False, b"", b""

        with (
            patch.object(runner, "args", new=mock_args),
            patch.object(runner, "_capture_subprocess", new=fake_capture),
            patch.object(runner, "_collect_rma_showtech") as mock_collect,
        ):
            runner._run_test(
                conf_file="dummy.conf",
                test_prefix="cold_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=False,
            )
        mock_collect.assert_called_once_with("HwFooTest.Bar", ANY)

    def test_run_test_no_collection_on_pass(self, runner, mock_args, tmp_path):
        """_run_test does not collect diagnostics when the test passes."""
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        with (
            patch.object(runner, "args", new=mock_args),
            patch.object(
                runner,
                "_capture_subprocess",
                new=_make_capture_writing(
                    b"[  PASSED  ] HwFooTest.Bar (5 ms)\n", runner, _STUB_GTEST_XML
                ),
            ),
            patch.object(runner, "_collect_rma_showtech") as mock_collect,
        ):
            runner._run_test(
                conf_file="dummy.conf",
                test_prefix="cold_boot.",
                test_to_run="HwFooTest.Bar",
                setup_warmboot=False,
            )
        mock_collect.assert_not_called()


class TestResolveTestsFile:
    """Tests for the shared TestRunner._resolve_tests_file helper used by every
    runner: prefer a caller-supplied override when it exists, else fall back to
    the default file when it exists, else return "" (no filtering). Per-runner
    tests only assert their default file wires through; the resolution logic is
    exercised here once."""

    _EXISTS = "fboss_test_runner.runners.test_runner.os.path.exists"
    _DEFAULT = "./share/known_bad_tests/default.materialized_JSON"

    def test_override_used_when_present(self, runner):
        with patch(self._EXISTS, return_value=True):
            assert (
                runner._resolve_tests_file(
                    "/tmp/override.json", self._DEFAULT, "known_bad"
                )
                == "/tmp/override.json"
            )

    def test_override_missing_falls_back_to_default(self, runner):
        # Override set but absent -> use the (present) default file.
        with patch(self._EXISTS, side_effect=lambda p: p == self._DEFAULT):
            assert (
                runner._resolve_tests_file(
                    "/tmp/missing.json", self._DEFAULT, "known_bad"
                )
                == self._DEFAULT
            )

    def test_override_and_default_missing_returns_empty(self, runner):
        with patch(self._EXISTS, return_value=False):
            assert (
                runner._resolve_tests_file(
                    "/tmp/missing.json", self._DEFAULT, "known_bad"
                )
                == ""
            )

    def test_default_used_when_present(self, runner):
        with patch(self._EXISTS, return_value=True):
            assert (
                runner._resolve_tests_file(None, self._DEFAULT, "unsupported")
                == self._DEFAULT
            )

    def test_default_missing_returns_empty(self, runner):
        with patch(self._EXISTS, return_value=False):
            assert runner._resolve_tests_file(None, self._DEFAULT, "unsupported") == ""

    def test_no_default_returns_empty(self, runner):
        # A runner with no default file (default_file="") and no override.
        assert runner._resolve_tests_file(None, "", "unsupported") == ""


class TestGetTestRunCmdSwitchId:
    def test_switch_id_for_testing_is_included(self, runner, mock_args):
        mock_args.switch_id_for_testing = 1
        with patch.object(runner, "args", new=mock_args):
            cmd = runner._get_test_run_cmd("dummy.conf", "HwFooTest.Bar", [])
            assert "--switch_id_for_testing=1" in cmd

    def test_switch_id_for_testing_none_is_excluded(self, runner, mock_args):
        mock_args.switch_id_for_testing = None
        with patch.object(runner, "args", new=mock_args):
            cmd = runner._get_test_run_cmd("dummy.conf", "HwFooTest.Bar", [])
            assert not any("switch_id_for_testing" in item for item in cmd)


class TestAgentCrashDowngrade:
    """A unit crash detected after a test must fail that test even though the
    gtest binary itself reported OK (systemd Restart= resurrects a crashed
    production agent inside the test's own readiness wait, so gtest never
    sees it)."""

    _MOD = "fboss_test_runner.runners.test_runner"

    _PASSING_XML = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<testsuites tests="1" failures="0" disabled="0" errors="0" time="1" name="All">\n'
        b'  <testsuite name="HwT" tests="1" failures="0" disabled="0" errors="0" time="1">\n'
        b'    <testcase name="t" status="run" result="completed" time="1" classname="HwT"/>\n'
        b"  </testsuite>\n</testsuites>\n"
    )

    def _make_args(self, mock_args, **overrides):
        # _run_tests probes these with os.path / getattr; a bare Mock breaks them.
        mock_args.sai_replayer_logging = None
        mock_args.simulator = None
        for k, v in overrides.items():
            setattr(mock_args, k, v)
        return mock_args

    def _make_conf(self, tmp_path):
        conf = tmp_path / "test.conf"
        conf.write_text("")
        return str(conf)

    def _ok_outcome(self):
        return RunOutcome(
            "[ OK ] cold_boot.HwT.t (1 ms)",
            [GtestResult("cold_boot.HwT.t", GtestStatus.OK, 1)],
        )

    def _run(self, runner, mock_args, tmp_path, exits):
        runner.TESTRESULT_CURRENT_RUN_FILE = str(tmp_path / "tr_current_run.xml")
        args = self._make_args(mock_args, coldboot_only=True)
        conf = self._make_conf(tmp_path)

        def fake_run_test(*_a, **_k):
            # the binary "ran" and wrote a passing XML
            with open(runner.TESTRESULT_CURRENT_RUN_FILE, "wb") as f:
                f.write(self._PASSING_XML)
            return self._ok_outcome()

        with (
            patch.object(runner, "_run_test", side_effect=fake_run_test),
            patch.object(runner, "_setup_coldboot_test"),
            patch.object(runner, "_end_run"),
            patch.object(runner, "_collect_rma_showtech") as mock_showtech,
            patch(f"{self._MOD}.find_unclean_unit_exits", return_value=exits) as e,
            patch(f"{self._MOD}.list_core_dumps", return_value=set()) as c,
            patch(f"{self._MOD}.describe_core_dump"),
        ):
            all_results, test_results = runner._run_tests(["HwT.t"], conf, args)
        # the journal is read once per test; cores are listed before and after
        e.assert_called_once()
        assert c.call_count == 2
        return all_results, test_results, mock_showtech

    def test_crash_reason_downgrades_ok_to_failed(self, runner, mock_args, tmp_path):
        all_results, test_results, mock_showtech = self._run(
            runner,
            mock_args,
            tmp_path,
            exits=["fboss_hw_agent@0.service main process dumped core (status=6/ABRT)"],
        )
        assert [r.status for r in all_results] == [GtestStatus.FAILED]
        # the per-test XML captured for the aggregate now carries a <failure>
        assert len(test_results) == 1
        root = ET.fromstring(test_results[0])
        failure = next(root.iter("testcase")).find("failure")
        assert failure is not None
        assert "fboss_hw_agent@0.service main process dumped core" in failure.get(
            "message"
        )
        mock_showtech.assert_called_once_with("HwT.t", ANY)

    def test_no_crash_leaves_result_untouched(self, runner, mock_args, tmp_path):
        all_results, test_results, mock_showtech = self._run(
            runner, mock_args, tmp_path, exits=[]
        )
        assert [r.status for r in all_results] == [GtestStatus.OK]
        root = ET.fromstring(test_results[0])
        assert next(root.iter("testcase")).find("failure") is None
        mock_showtech.assert_not_called()


class TestCrashDetection:
    """What `_run_test_guarded` treats as a crash: any unit the test left
    running (production agents for the CLI suite, qsfp_service and the
    platform services for the SAI suites, ...) dying uncleanly inside the
    test window, or any core dump from a process other than the test binary."""

    _MOD = "fboss_test_runner.runners.test_runner"

    _OLD_CORE = "/var/lib/systemd/coredump/core.fboss_sw_agent.0.x.9.9.zst"

    def _reason(self, runner, exits, cores, summaries=None, stacks=None):
        """Run one guarded test and return the crash reason handed to
        _apply_agent_crash, or None if it was not called. `summaries` maps a
        core path to what `describe_core_dump` says about it. `stacks` maps a
        core path to its formatted stack trace."""
        outcome = RunOutcome("", [GtestResult("cold_boot.HwT.t", GtestStatus.OK, 1)])
        listings = iter([{self._OLD_CORE}, {self._OLD_CORE, *cores}])
        summaries = summaries or {}
        stacks = stacks or {}
        with (
            patch(f"{self._MOD}.time.time", return_value=1.0),
            patch.object(runner, "_run_test", return_value=outcome),
            patch.object(runner, "_apply_agent_crash") as apply,
            patch(f"{self._MOD}.find_unclean_unit_exits", return_value=exits) as e,
            patch(
                f"{self._MOD}.list_core_dumps", side_effect=lambda: next(listings)
            ) as c,
            patch(
                f"{self._MOD}.get_core_dump_info",
                side_effect=lambda core: f"info for {core}",
            ),
            patch(
                f"{self._MOD}.describe_core_dump",
                side_effect=lambda core, *_, **__: summaries.get(core, f"core {core}"),
            ),
            patch(
                f"{self._MOD}.format_core_dump_stack",
                side_effect=lambda core, *_, **__: stacks.get(core),
            ),
        ):
            assert (
                runner._run_test_guarded("c", "cold_boot.", "HwT.t", False) is outcome
            )
        # both probes look at the window that opened when the binary started
        e.assert_called_once_with(1.0)
        assert c.call_count == 2
        if not apply.called:
            return None
        apply.assert_called_once()
        assert apply.call_args[0][:3] == (outcome, "cold_boot.", "HwT.t")
        # the core paths ride along for the banner, never in the reason
        expected_cores = sorted(core for core in cores if "sai_test-sai_im" not in core)
        assert apply.call_args[0][4] == expected_cores
        expected_stacks = [stacks[c] for c in expected_cores if c in stacks]
        assert apply.call_args[0][5] == expected_stacks
        return apply.call_args[0][3]

    def test_unit_crash_is_reported(self, runner):
        reason = self._reason(
            runner,
            ["qsfp_service.service main process dumped core (status=6/ABRT)"],
            [],
        )
        assert reason == "qsfp_service.service main process dumped core (status=6/ABRT)"

    def test_foreign_cores_are_described_not_listed(self, runner):
        """The reason is what result databases index and classify failures
        on, and they cap it at a few hundred characters: a core path would
        crowd out the crash. Each core contributes its stack summary; the
        paths go to the banner."""
        hw = "/var/lib/systemd/coredump/core.fboss_hw_agent-.0.x.1.2.zst"
        qsfp = "/var/lib/systemd/coredump/core.qsfp_service.0.x.3.4.zst"
        reason = self._reason(
            runner,
            [],
            [hw, qsfp],
            {
                hw: "fboss_hw_agent@0.service SIGABRT in SaiStore::check < SaiSwitch::init",
                qsfp: "qsfp_service.service SIGSEGV in TransceiverManager::refresh",
            },
        )
        assert reason == (
            "fboss_hw_agent@0.service SIGABRT in SaiStore::check < SaiSwitch::init; "
            "qsfp_service.service SIGSEGV in TransceiverManager::refresh"
        )

    def test_own_core_is_ignored(self, runner):
        """The test binary dumping core already failed the test on its own;
        naming its core as a unit crash would be noise."""
        with patch.object(
            runner,
            "_get_test_binary_name",
            return_value="/opt/fboss/bin/sai_test-sai_impl",
        ):
            assert (
                self._reason(
                    runner,
                    [],
                    ["/var/lib/systemd/coredump/core.sai_test-sai_im.0.x.5.6.zst"],
                )
                is None
            )

    def test_core_summary_replaces_the_units_exit_line(self, runner):
        """PID 1's "main process dumped core" line and the core summary
        describe the same death; only the summary says why. A unit that
        died without leaving a core keeps its journal line."""
        hw = "/var/lib/systemd/coredump/core.fboss_hw_agent-.0.x.1.2.zst"
        reason = self._reason(
            runner,
            [
                "fboss_hw_agent@0.service main process dumped core (status=11/SEGV)",
                "fboss_sw_agent.service main process exited (status=1/FAILURE)",
            ],
            [hw],
            {hw: "fboss_hw_agent@0.service SIGSEGV in SaiPortManager::addPort"},
        )
        assert reason == (
            "fboss_sw_agent.service main process exited (status=1/FAILURE); "
            "fboss_hw_agent@0.service SIGSEGV in SaiPortManager::addPort"
        )

    def test_healthy_window_is_not_a_crash(self, runner):
        assert self._reason(runner, [], []) is None

    def test_apply_downgrades_ok_and_skipped_only(self, runner):
        outcome = RunOutcome(
            "gtest transcript line 1\ngtest transcript line 2\n",
            [
                GtestResult("cold_boot.HwT.ok", GtestStatus.OK, 1),
                GtestResult("cold_boot.HwT.skipped", GtestStatus.SKIPPED, 1),
                GtestResult("cold_boot.HwT.timeout", GtestStatus.TIMEOUT, 1),
            ],
        )
        runner._apply_agent_crash(
            outcome, "cold_boot.", "HwT.*", "x.service dumped core"
        )
        assert [r.status for r in outcome.results] == [
            GtestStatus.FAILED,
            GtestStatus.FAILED,
            GtestStatus.TIMEOUT,
        ]
        # the binary's transcript is kept (it is the only copy), the verdict
        # is appended after it
        assert outcome.console_output.startswith(
            "gtest transcript line 1\ngtest transcript line 2\n########## CRASH"
        )
        assert "x.service dumped core" in outcome.console_output
        assert outcome.console_output.endswith(
            "\n".join(r.as_log_line() for r in outcome.results)
        )

    def test_apply_injects_core_stack_trace_into_xml_and_console(
        self, runner, tmp_path
    ):
        xml_file = tmp_path / "tr_current_run.xml"
        xml_file.write_bytes(
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<testsuites tests="1" failures="0" disabled="0" errors="0" time="1">\n'
            b'  <testsuite name="HwT" tests="1" failures="0" disabled="0" errors="0" time="1">\n'
            b'    <testcase name="t" status="run" result="completed" time="1" classname="HwT"/>\n'
            b"  </testsuite>\n</testsuites>\n"
        )
        runner.TESTRESULT_CURRENT_RUN_FILE = str(xml_file)
        outcome = RunOutcome(
            "gtest line 1\n", [GtestResult("cold_boot.HwT.t", GtestStatus.OK, 1)]
        )
        stack = (
            "Core dump: /var/core/core.1 [fboss_hw_agent@0.service (SIGABRT)]\n"
            "Stack trace of thread 100:\n"
            "  #0 0x123 abort (libc.so.6)\n"
            "  #1 0x456 facebook::fboss::SaiStore::check (fboss_hw_agent)\n"
        )
        runner._apply_agent_crash(
            outcome,
            "cold_boot.",
            "HwT.t",
            "fboss_hw_agent@0.service SIGABRT in SaiStore::check",
            cores=["/var/core/core.1"],
            core_stacks=[stack],
        )
        assert outcome.results[0].status == GtestStatus.FAILED
        assert stack in outcome.console_output

        # Verify failure in XML contains the stack trace
        root = ET.fromstring(xml_file.read_bytes())
        failure = next(root.iter("testcase")).find("failure")
        assert failure is not None
        assert "Agent crashed during test:" in failure.get("message")
        assert stack in failure.text

    def test_foreign_cores_include_stack_traces(self, runner):
        hw = "/var/lib/systemd/coredump/core.fboss_hw_agent-.0.x.1.2.zst"
        hw_stack = (
            f"Core dump: {hw} [fboss_hw_agent@0.service (SIGABRT)]\nStack trace..."
        )
        reason = self._reason(
            runner,
            [],
            [hw],
            summaries={hw: "fboss_hw_agent@0.service SIGABRT in SaiStore::check"},
            stacks={hw: hw_stack},
        )
        assert reason == "fboss_hw_agent@0.service SIGABRT in SaiStore::check"
