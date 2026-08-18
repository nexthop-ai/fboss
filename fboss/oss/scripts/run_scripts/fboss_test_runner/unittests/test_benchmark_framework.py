#!/usr/bin/env python3
# Copyright Meta Platforms, Inc. and affiliates.
# @noautodeps

"""Unit tests for the generic BenchmarkFramework (suite-agnostic behavior).

Uses a lightweight FakeSuite so these tests exercise only the framework's
orchestration, parsing, filtering, threshold-checking, and reporting -- the
benchmark-family-specific behavior is covered in test_sai_benchmark_suite.py and
test_qsfp_benchmark_suite.py.
"""

import io
import json
import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from fboss_test_runner.frameworks.benchmark_framework import BenchmarkFramework
from fboss_test_runner.frameworks.benchmark_suite import BenchmarkSuite

_BIN = "/opt/fboss/bin/fake_benchmark"


class FakeSuite(BenchmarkSuite):
    """Minimal suite for exercising the framework in isolation."""

    def __init__(self, config_path="/nonexistent/fake_bench.json"):
        self._config_path = config_path
        self.setup_called = 0
        self.teardown_called = 0

    def binary_path(self, args):
        return _BIN

    def config_path(self):
        return self._config_path

    def known_bad_keys(self, platform_key):
        return [platform_key]

    def build_cmd(self, binary, args, benchmark_name=None):
        cmd = [binary, "--json"]
        if benchmark_name:
            cmd.extend(["--bm_regex", f"^{benchmark_name}$"])
        return cmd

    def find_thresholds(self, benchmark_name, platform_key, all_thresholds, args):
        return all_thresholds.get(benchmark_name, [])

    def setup(self, args):
        self.setup_called += 1

    def teardown(self, args):
        self.teardown_called += 1


@pytest.fixture
def suite():
    return FakeSuite()


@pytest.fixture
def framework(suite):
    return BenchmarkFramework(suite)


@pytest.fixture
def bench_args():
    args = Mock()
    args.filter = None
    args.filter_file = None
    args.profile = None
    args.list_tests = False
    args.fruid_path = None
    args.test_run_timeout = 300
    args.skip_known_bad_tests = None
    return args


@pytest.fixture(autouse=True)
def _binary_present():
    with patch("os.path.isfile", return_value=True):
        yield


# ---- discovery / parsing -------------------------------------------------


def test_list_benchmarks_filters_noise(framework):
    out = (
        "[==========] Running 0 tests\n"
        "HwEcmpGroupShrink\n"
        '{\n  "cpu_time_usec": 911\n}\n'
        "runTxSlowPathBenchmark\n"
    )
    with patch("subprocess.check_output", return_value=out):
        assert framework._list_benchmarks(_BIN) == [
            "HwEcmpGroupShrink",
            "runTxSlowPathBenchmark",
        ]


def test_list_benchmarks_failure_returns_none(framework, capsys):
    with patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "cmd")
    ):
        assert framework._list_benchmarks(_BIN) is None
    assert "Failed to list benchmarks" in capsys.readouterr().out


# ---- filter grammar (_get_benchmarks_to_run) -----------------------------

_ALL = [
    "HwFswScaleRouteAddBenchmark",
    "HwVoqScaleRouteAddBenchmark",
    "HwEcmpGroupShrink",
]


def _filter_file(tmp_path, *lines):
    path = tmp_path / "tests.conf"
    path.write_text("".join(f"{line}\n" for line in lines))
    return str(path)


@pytest.mark.parametrize(
    ("filter_string", "expected"),
    [
        ("*Route*", ["HwFswScaleRouteAddBenchmark", "HwVoqScaleRouteAddBenchmark"]),
        # multiple includes OR together
        ("*Fsw*:*Ecmp*", ["HwFswScaleRouteAddBenchmark", "HwEcmpGroupShrink"]),
        # empty include side means everything
        ("-*Voq*", ["HwFswScaleRouteAddBenchmark", "HwEcmpGroupShrink"]),
        ("*Route*:-*Voq*", ["HwFswScaleRouteAddBenchmark"]),
        # everything after the first '-' excludes
        ("*:-*Voq*:*Ecmp*", ["HwFswScaleRouteAddBenchmark"]),
        ("*Ecmp?roupShrink", ["HwEcmpGroupShrink"]),
        # plain regex back-compat
        (".*Route.*", ["HwFswScaleRouteAddBenchmark", "HwVoqScaleRouteAddBenchmark"]),
    ],
)
def test_get_benchmarks_to_run_grammar(framework, bench_args, filter_string, expected):
    bench_args.filter = filter_string
    assert framework._get_benchmarks_to_run(_ALL, bench_args) == expected


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("*Route*", ".*Route.*"),
        # already-regex constructs survive untouched
        (".*Route.*", ".*Route.*"),
        (r"Hw\*Literal", r"Hw\*Literal"),
        ("Ecmp?Group", "Ecmp.Group"),
        (".*?Route", ".*?Route"),
    ],
)
def test_wildcards_to_regex(framework, pattern, expected):
    assert framework._wildcards_to_regex(pattern) == expected


def test_plain_regex_matches_name_at_position_zero(framework, bench_args):
    # Guards the ".*" -> "..*" bug.
    bench_args.filter = ".*Route.*"
    assert framework._get_benchmarks_to_run(["RouteAdd", "EcmpShrink"], bench_args) == [
        "RouteAdd"
    ]


def test_get_benchmarks_to_run_no_filter_returns_all(framework, bench_args):
    assert framework._get_benchmarks_to_run(_ALL, bench_args) == _ALL


def test_get_benchmarks_to_run_no_match_is_error(framework, bench_args, capsys):
    bench_args.filter = "*NoSuchThing*"
    assert framework._get_benchmarks_to_run(_ALL, bench_args) is None
    assert "No benchmarks matching filter" in capsys.readouterr().out


def test_get_benchmarks_to_run_invalid_pattern(framework, bench_args, capsys):
    bench_args.filter = "Hw(Unclosed"
    assert framework._get_benchmarks_to_run(_ALL, bench_args) is None
    assert "Invalid include pattern" in capsys.readouterr().out


def test_get_benchmarks_to_run_invalid_exclude_pattern(framework, bench_args, capsys):
    bench_args.filter = "*:-Hw(Unclosed"
    assert framework._get_benchmarks_to_run(_ALL, bench_args) is None
    assert "Invalid exclude pattern" in capsys.readouterr().out


def test_filter_file_lines_are_patterns(framework, bench_args, tmp_path):
    # Lines join with ':' as gtest grammar, not exact benchmark names.
    bench_args.filter_file = _filter_file(tmp_path, "*Route*", "-*Voq*")
    assert framework._get_benchmarks_to_run(_ALL, bench_args) == [
        "HwFswScaleRouteAddBenchmark"
    ]


def test_filter_file_wins_over_filter(framework, bench_args, tmp_path):
    bench_args.filter = "*Ecmp*"
    bench_args.filter_file = _filter_file(tmp_path, "*Voq*")
    assert framework._get_benchmarks_to_run(_ALL, bench_args) == [
        "HwVoqScaleRouteAddBenchmark"
    ]


def test_filter_file_missing(framework, bench_args, capsys):
    bench_args.filter_file = "/nonexistent/file.conf"
    assert framework._get_benchmarks_to_run(_ALL, bench_args) is None
    assert "Configuration file not found" in capsys.readouterr().out


def test_filter_file_empty(framework, bench_args, tmp_path, capsys):
    bench_args.filter_file = _filter_file(tmp_path)
    assert framework._get_benchmarks_to_run(_ALL, bench_args) is None
    assert "No benchmark filters found" in capsys.readouterr().out


def test_find_jsons_in_str(framework):
    out = 'noise\n{"a": 1}\nmore\n{"b": 2, "c": 3}\n'
    assert framework._find_jsons_in_str(out) == [{"a": 1}, {"b": 2, "c": 3}]


def test_parse_benchmark_output_with_name(framework):
    stdout = '{"RibBench": 1460000000000}\n{"cpu_time_usec": 5, "max_rss": 9}\n'
    result = framework._parse_benchmark_output(_BIN, stdout, benchmark_name="RibBench")
    assert result["benchmark_test_name"] == "RibBench"
    assert result["benchmark_time_ps"] == "1460000000000"
    assert result["cpu_time_usec"] == "5"
    assert result["max_rss"] == "9"


def test_parse_benchmark_output_empty(framework):
    result = framework._parse_benchmark_output(_BIN, "")
    assert result["benchmark_test_name"] == ""
    assert result["metrics"] == {}


# ---- execution -----------------------------------------------------------


def _mock_popen(stdout_text, returncode=0):
    proc = Mock()
    proc.stdout = io.StringIO(stdout_text)
    proc.stderr = io.StringIO("")
    proc.returncode = returncode
    proc.wait = Mock(return_value=returncode)
    proc.kill = Mock()
    return proc


@patch("subprocess.Popen")
def test_run_benchmark_binary_success(mock_popen, framework, bench_args):
    mock_popen.return_value = _mock_popen('{"B": 2500000000000}\n')
    result = framework._run_benchmark_binary(_BIN, bench_args, benchmark_name="B")
    assert result["test_status"] == "OK"
    assert result["benchmark_test_name"] == "B"
    # build_cmd came from the suite.
    assert "--bm_regex" in mock_popen.call_args[0][0]


@patch("subprocess.Popen")
def test_run_benchmark_binary_timeout(mock_popen, framework, bench_args):
    proc = _mock_popen("")
    proc.wait.side_effect = subprocess.TimeoutExpired("cmd", 300)
    mock_popen.return_value = proc
    result = framework._run_benchmark_binary(_BIN, bench_args, benchmark_name="B")
    assert result["test_status"] == "TIMEOUT"
    assert result["benchmark_test_name"] == "B"
    proc.kill.assert_called_once()


@patch("subprocess.Popen")
def test_run_benchmark_binary_nonzero_is_failed(mock_popen, framework, bench_args):
    mock_popen.return_value = _mock_popen('{"B": 1}\n', returncode=1)
    result = framework._run_benchmark_binary(_BIN, bench_args, benchmark_name="B")
    assert result["test_status"] == "FAILED"


# ---- thresholds ----------------------------------------------------------


def test_check_thresholds_upper_exceeded(framework):
    result = {"metrics": {"B": 30}}
    assert framework._check_thresholds(
        result, [{"metric_key_regex": "B", "upper_bound": 25}]
    ) == ["B=30 > upper_bound=25"]


def test_check_thresholds_missing_metric_no_violation(framework):
    result = {"metrics": {"Other": 30}}
    assert (
        framework._check_thresholds(
            result, [{"metric_key_regex": "B", "upper_bound": 1}]
        )
        == []
    )


def test_apply_threshold_check_pass(framework, bench_args):
    result = {"test_status": "OK", "benchmark_test_name": "B", "metrics": {"B": 10}}
    framework._apply_threshold_check(
        result,
        "plat",
        {"B": [{"metric_key_regex": "B", "upper_bound": 25}]},
        bench_args,
    )
    assert result["threshold_status"] == "PASS"


def test_apply_threshold_check_no_threshold_warns(framework, bench_args, capsys):
    result = {"test_status": "OK", "benchmark_test_name": "B", "metrics": {"B": 10}}
    framework._apply_threshold_check(result, "plat", {"Other": [{}]}, bench_args)
    assert result["threshold_status"] == "NO_THRESHOLD"
    assert "WILL ALWAYS PASS" in capsys.readouterr().out


def test_apply_threshold_check_na_when_not_ok(framework, bench_args):
    result = {"test_status": "FAILED", "benchmark_test_name": "B", "metrics": {}}
    framework._apply_threshold_check(result, "plat", {"B": [{}]}, bench_args)
    assert result["threshold_status"] == "N/A"


# ---- run() orchestration -------------------------------------------------


def _ok_result(name):
    return {
        "benchmark_binary_name": _BIN,
        "benchmark_test_name": name,
        "benchmark_time_ps": "1000",
        "test_status": "OK",
        "cpu_time_usec": "1",
        "max_rss": "2",
        "cpu_rx_pps": "",
        "cpu_tx_pps": "",
        "metrics": {name: 1000},
    }


def test_run_no_binary(framework, bench_args, capsys):
    with patch("os.path.isfile", return_value=False):
        framework.run(bench_args)
    assert "Could not find benchmark binary" in capsys.readouterr().out


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_basic_flow_calls_setup_teardown(
    mock_list, mock_run, mock_write, suite, bench_args
):
    mock_list.return_value = ["A", "B", "C"]
    mock_run.return_value = _ok_result("A")
    framework = BenchmarkFramework(suite)
    framework.run(bench_args)
    assert mock_run.call_count == 3
    assert suite.setup_called == 1
    assert suite.teardown_called == 1
    mock_write.assert_called_once()


@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_list_tests(mock_list, framework, bench_args, capsys):
    mock_list.return_value = ["A", "B"]
    bench_args.list_tests = True
    framework.run(bench_args)
    out = capsys.readouterr().out
    assert "A" in out and "B" in out


@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_discovery_failure(mock_list, framework, bench_args, capsys):
    mock_list.return_value = None
    framework.run(bench_args)
    assert "Could not discover benchmarks" in capsys.readouterr().out


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_filter_regex(mock_list, mock_run, _mock_write, framework, bench_args):
    mock_list.return_value = ["RouteAdd", "RouteDel", "EcmpShrink"]
    mock_run.return_value = _ok_result("RouteAdd")
    bench_args.filter = ".*Route.*"
    framework.run(bench_args)
    assert mock_run.call_count == 2


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_with_filter_file(
    mock_list, mock_run, _mock_write, framework, bench_args, tmp_path
):
    mock_list.return_value = ["RouteAdd", "RouteDel", "EcmpShrink"]
    mock_run.return_value = _ok_result("RouteAdd")
    bench_args.filter_file = _filter_file(tmp_path, "*Route*", "-*Del*")
    framework.run(bench_args)
    assert mock_run.call_count == 1


@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_all_selected_unsupported_reports_skips(
    mock_list, mock_run, suite, bench_args, tmp_path, capsys
):
    # An all-unsupported bucket must still write results; a missing CSV reads as
    # an infra failure.
    cfg = tmp_path / "bench.json"
    cfg.write_text(
        json.dumps({"unsupported_tests": {"plat": [{"test_name_regex": ".*Voq.*"}]}})
    )
    suite._config_path = str(cfg)
    mock_list.return_value = ["HwVoqA", "HwVoqB"]
    bench_args.skip_known_bad_tests = "plat"
    framework = BenchmarkFramework(suite)
    with patch.object(framework, "_write_results_and_summary") as mock_write:
        framework.run(bench_args)
    mock_run.assert_not_called()
    mock_write.assert_called_once_with([], 2)
    assert "No benchmarks to run after filtering" in capsys.readouterr().out


@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_list_tests_does_not_write_results(
    mock_list, mock_run, framework, bench_args
):
    mock_list.return_value = ["A"]
    bench_args.list_tests = True
    with patch.object(framework, "_write_results_and_summary") as mock_write:
        framework.run(bench_args)
    mock_run.assert_not_called()
    mock_write.assert_not_called()


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_prefilters_known_bad(
    mock_list, mock_run, mock_write, suite, bench_args, capsys, tmp_path
):
    # config with a known-bad regex keyed by the platform key
    cfg = tmp_path / "bench.json"
    cfg.write_text(
        json.dumps({"known_bad_tests": {"plat": [{"test_name_regex": ".*Voq.*"}]}})
    )
    suite._config_path = str(cfg)
    mock_list.return_value = ["A", "HwVoqTest", "C"]
    mock_run.return_value = _ok_result("A")
    bench_args.skip_known_bad_tests = "plat"
    BenchmarkFramework(suite).run(bench_args)
    assert mock_run.call_count == 2
    assert "SKIPPING (known bad): HwVoqTest" in capsys.readouterr().out
    assert mock_write.call_args[0][1] == 1


def test_write_results_and_summary_exits_on_failure(framework, tmp_path):
    os.chdir(tmp_path)
    result = _ok_result("A")
    result["test_status"] = "FAILED"
    result["threshold_status"] = "N/A"
    result["threshold_details"] = ""
    with pytest.raises(SystemExit) as exc:
        framework._write_results_and_summary([result])
    assert exc.value.code == 1


# ---- rma-showtech diagnostics on failure ---------------------------------
#
# rma-showtech diagnostics collection on benchmark failure (the run() hook,
# _collect_rma_showtech, and the _capture_subprocess it streams through).


def _failed_result(name, status="FAILED"):
    result = _ok_result(name)
    result["test_status"] = status
    return result


def test_collect_rma_showtech_nondisruptive(framework):
    """rma-showtech runs with '--details all' and without '--disruptive' so
    diagnostics don't further perturb the DUT."""
    with patch.object(
        framework, "_capture_subprocess", return_value=(0, False)
    ) as mock_capture:
        framework._collect_rma_showtech("HwRouteBench")
    mock_capture.assert_called_once()
    cmd = mock_capture.call_args.args[0]
    assert cmd == ["rma-showtech", "--details", "all"]
    assert "--disruptive" not in cmd


def test_collect_rma_showtech_missing_binary_does_not_raise(framework):
    """A missing rma-showtech binary must not mask the underlying benchmark
    failure."""
    with patch.object(framework, "_capture_subprocess", side_effect=FileNotFoundError):
        # Must not raise.
        framework._collect_rma_showtech("HwRouteBench")


@patch("subprocess.Popen")
def test_capture_subprocess_streams_and_reports_timeout(mock_popen, framework, capsys):
    """A hung rma-showtech is killed and reported as timed out, and its output
    still reaches the log."""
    proc = _mock_popen("diag line\n")
    proc.wait.side_effect = [subprocess.TimeoutExpired("cmd", 300), -9]
    mock_popen.return_value = proc
    returncode, timed_out = framework._capture_subprocess(["rma-showtech"], 300)
    assert timed_out
    assert returncode == -9
    proc.kill.assert_called_once()
    assert "diag line" in capsys.readouterr().out


@pytest.mark.parametrize("status", ["FAILED", "TIMEOUT"])
@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_collects_on_failure(
    mock_list, mock_run, _mock_write, framework, bench_args, status
):
    """run() triggers rma-showtech collection on a non-OK outcome."""
    mock_list.return_value = ["A"]
    mock_run.return_value = _failed_result("A", status)
    with patch.object(framework, "_collect_rma_showtech") as mock_collect:
        framework.run(bench_args)
    mock_collect.assert_called_once_with("A")


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_run_benchmark_binary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_no_collection_on_pass(
    mock_list, mock_run, _mock_write, framework, bench_args
):
    """run() does not collect diagnostics when every benchmark passes."""
    mock_list.return_value = ["A", "B"]
    mock_run.return_value = _ok_result("A")
    with patch.object(framework, "_collect_rma_showtech") as mock_collect:
        framework.run(bench_args)
    mock_collect.assert_not_called()


@patch.object(BenchmarkFramework, "_write_results_and_summary")
@patch.object(BenchmarkFramework, "_list_benchmarks")
def test_run_collects_before_next_benchmark_and_teardown(
    mock_list, _mock_write, suite, bench_args
):
    """Diagnostics for a failing benchmark are collected while the DUT is still
    in its failed state: before the next benchmark runs and before teardown."""
    mock_list.return_value = ["A", "B"]
    framework = BenchmarkFramework(suite)
    order = []

    def fake_run(binary, args, benchmark_name=None):  # noqa: ARG001
        order.append(f"run:{benchmark_name}")
        if benchmark_name == "A":
            return _failed_result("A")
        return _ok_result(benchmark_name)

    with (
        patch.object(framework, "_run_benchmark_binary", side_effect=fake_run),
        patch.object(
            framework,
            "_collect_rma_showtech",
            side_effect=lambda name: order.append(f"showtech:{name}"),
        ),
        patch.object(
            suite, "teardown", side_effect=lambda _args: order.append("teardown")
        ),
    ):
        framework.run(bench_args)
    assert order == ["run:A", "showtech:A", "run:B", "teardown"]
