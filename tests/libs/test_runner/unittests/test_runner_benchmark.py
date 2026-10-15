"""BenchmarkTestRunner and QsfpBenchmarkTestRunner: argument assembly and the
benchmark log parsing that decides whether a run is infra-fatal."""

from unittest.mock import patch

import pytest

from tests.libs.test_runner import BenchmarkTestRunner, QsfpBenchmarkTestRunner


class TestTestArgs:
    @pytest.mark.parametrize(
        ("model", "config_name"),
        [
            ("nhbw800f", "wedge800bact"),  # real benchmark config
            ("minipack3", "montblanc"),  # symlink into hw_test_configs
        ],
    )
    def test_bench_config_always_from_hw_bench_configs(self, model, config_name):
        args = BenchmarkTestRunner().test_args(model)
        assert f"./share/hw_bench_configs/{config_name}.agent.materialized_JSON" in args
        assert "hw_test_configs" not in args

    def test_pins_multi_switch(self, monkeypatch):
        monkeypatch.setenv("FBOSS_AGENT_RUN_MODE", "mono")

        args = BenchmarkTestRunner().test_args("nhbw800f")

        assert "benchmark --agent-run-mode multi_switch" in args
        assert "benchmark --agent-run-mode mono" not in args

    def test_qsfp_benchmark_reads_qsfp_test_configs(self):
        args = QsfpBenchmarkTestRunner().test_args("nhbw800f")
        assert "qsfp_test_configs/wedge800bact.materialized_JSON" in args
        assert "hw_bench_configs" not in args


class TestLogParsing:
    def test_result_csv_name_from_log(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text(
            "Running 3 benchmarks\n"
            "Benchmark results written to: benchmark_results_20261014_103000.csv\n"
        )
        assert BenchmarkTestRunner()._get_result_csv_name(str(log)) == "benchmark_results_20261014_103000.csv"

    def test_result_csv_name_absent(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("binary crashed before writing anything\n")
        assert BenchmarkTestRunner()._get_result_csv_name(str(log)) is None

    def test_skipped_count_from_log(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("Skipped (known bad, pre-filtered): 4\nRunning 10 benchmarks\n")
        assert BenchmarkTestRunner()._get_skipped_bm_count(str(log)) == 4

    def test_skipped_count_defaults_to_zero(self, tmp_path):
        log = tmp_path / "test.log"
        log.write_text("Running 10 benchmarks\n")
        assert BenchmarkTestRunner()._get_skipped_bm_count(str(log)) == 0


class TestBinaryExitIsFatal:
    """run_test.py exits non-zero when any benchmark fails; only a missing
    results CSV means the run itself broke."""

    @pytest.mark.parametrize("exit_status", [0, 1])
    def test_fatal_only_without_a_results_csv(self, exit_status):
        runner = BenchmarkTestRunner()
        with patch.object(runner, "_get_result_csv_name", return_value=None):
            assert runner.binary_exit_is_fatal(exit_status) is True
        with patch.object(runner, "_get_result_csv_name", return_value="benchmark_results_x.csv"):
            assert runner.binary_exit_is_fatal(exit_status) is False
