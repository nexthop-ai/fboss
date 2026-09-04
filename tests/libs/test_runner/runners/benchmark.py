"""Benchmark test runners: SAI agent benchmarks and QSFP benchmarks."""

import logging
import re
import time

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_SHARE
from tests.libs.test_runner.junit import generate_tr_xml_from_csv
from tests.libs.test_runner.platform_configs import (
    LINK_QSFP_TEST_CONFIG_NAME,
    QSFP_BENCH_PHY_SDK,
    SAI_AGENT_CONFIG_NAME,
    benchmark_skip_known_bad,
)

logger = logging.getLogger("test_runner")


class BenchmarkTestRunner(BaseHwTestRunner):
    """Runner for benchmark tests. """

    STACK = STACK_FORWARDING
    BINARIES = (
        "bin/sai_all_benchmarks-sai_impl",
        "bin/sai_multi_switch_all_benchmarks-sai_impl",
    )
    # hw_bench_configs is not in STACK_SHARE: this is the only runner that reads
    # it, and a REQUIRED_PATHS entry resolving to nothing is fatal
    # (_slice_members raises), so listing it stack-wide would fail every
    # forwarding runner's deploy against a tarball predating its addition to
    # package.py's FORWARDING_TEST_EXTRA. It must ship alongside hw_test_configs
    # (from STACK_SHARE): platforms with no benchmark-specific config have a
    # symlink into ../hw_test_configs there.
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK], "share/hw_bench_configs/")

    def test_args(self, model: str) -> str:
        config_name = SAI_AGENT_CONFIG_NAME.get(model, model)
        logger.info(
            "model=%s hw_bench_config=%s agent_run_mode=multi_switch",
            model,
            config_name,
        )
        return (
            "benchmark --agent-run-mode multi_switch"
            f" --config ./share/hw_bench_configs/{config_name}"
            f".agent.materialized_JSON{benchmark_skip_known_bad(model)}"
        )

    # Benchmark binaries spin up their own agent (binds thrift port 5909, owns
    # the ASIC), so the production agents must be down first or the bind aborts
    # (Address already in use) and the ASIC contends (SIGBUS/SIGSEGV). run_test.py
    # stops these for the gtest runners but not for the benchmark sub-command.
    #
    # bgpd must go too: it reconnects to whatever holds port 5909, so it treats
    # the benchmark's agent as a restarted production agent and issues a full
    # syncFib. syncFib is replace-all per client, and EcmpSetupHelper programs
    # test routes as ClientID::BGPD, so the sync deletes the route under the
    # traffic the benchmark is mid-measurement on.
    BENCHMARK_DISABLE_SERVICES = ["fboss_sw_agent", "fboss_hw_agent@0", "bgpd"]

    def pre_test(self):
        services = " ".join(self.BENCHMARK_DISABLE_SERVICES)
        logger.info("Stopping production agents for benchmark: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl mask {services}")
        self.ssh_client.run_cmd(f"sudo systemctl stop {services}")
        time.sleep(2)
        # Agents write can_warm_boot on graceful exit; base wipe forces cold boot.
        super().pre_test()

    def post_test(self):
        services = " ".join(self.BENCHMARK_DISABLE_SERVICES)
        logger.info("Restarting production agents: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl unmask {services}")
        self.ssh_client.run_cmd(f"sudo systemctl start {services}")

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        # run_test.py exits non-zero when any individual benchmark fails; that is
        # a test result (captured per-benchmark in the CSV / tr.xml), not an infra
        # error. Only treat the run as infra-fatal if no results CSV was written.
        return self._get_result_csv_name("/tmp/test.log") is None

    def _get_result_csv_name(self, local_log_path: str) -> str | None:
        """Extract CSV filename from benchmark log"""
        with open(local_log_path, encoding="utf-8") as f:
            content = f.read()

        match = re.search(
            r"Benchmark results written to: (benchmark_results_\S+\.csv)", content
        )
        if match:
            return match.group(1)

        logger.warning(
            f"Could not find benchmark results CSV filename in {local_log_path}"
        )
        return None

    def _get_skipped_bm_count(self, local_log_path: str) -> int:
        """Extract num tests skipped from benchmark log"""
        with open(local_log_path, encoding="utf-8") as f:
            for line in f:
                match = re.search(r"Skipped \(known bad, pre-filtered\): (\d+)", line)
                if match:
                    return int(match.group(1))

        logger.warning(f"Could not find skipped count in {local_log_path}")
        return 0

    def _run_test_impl(self, test_context, skip_tr_xml=False) -> bool:
        """
        Run the benchmark test on the DUT.
        This acts as a wrapper around the base class implementation and adds
        additional functionality for generating a tr.xml based on a
        benchmark_result.csv, as benchmarks do not produce a tr.xml
        automatically. (setup()/deploy and the deploy-only gate already ran in
        run_test(); the base run always skips its own tr.xml fetch here.)
        """
        success = super()._run_test_impl(test_context, skip_tr_xml=True)
        if not success:
            return False

        # Benchmarks do not produce tr.xml, only a CSV file
        csv_filename = self._get_result_csv_name("/tmp/test.log")
        if csv_filename is None:
            logger.error("Failed to find benchmark results CSV filename in test log")
            return False

        self.testresult_filepath = f"/opt/fboss/{csv_filename}"
        local_csv_path = "/tmp/benchmark_results.csv"
        exit_status, output = self.scp_client.get_file(
            self.testresult_filepath, local_csv_path
        )
        if exit_status != 0:
            logger.warning("Failed to fetch test results: %s", output)

        # Use CSV file to create tr.xml locally
        # CSV filename looks like:
        # f"benchmark_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"
        csv_timestamp = csv_filename.replace("benchmark_results_", "").replace(
            ".csv", ""
        )
        skipped_count = self._get_skipped_bm_count("/tmp/test.log")

        logger.info("Generating /tmp/tr.xml from %s", local_csv_path)
        success = generate_tr_xml_from_csv(
            local_csv_path, "/tmp/tr.xml", csv_timestamp, skipped_count
        )
        if not success:
            logger.error("Failed to generate /tmp/tr.xml from %s", local_csv_path)
            return False

        self.normalize_test_results_file()

        return True


class QsfpBenchmarkTestRunner(BenchmarkTestRunner):
    """Runner for QSFP benchmarks (run_test.py benchmark --qsfp)."""

    STACK = STACK_FORWARDING
    BINARIES = ("bin/qsfp_hw_test_benchmark",)
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    # Binary must own the xcvr i2c bus, same as qsfp_hw_test (TEST_DISABLE_SERVICES).
    BENCHMARK_DISABLE_SERVICES = ["qsfp_service", "led_service"]

    def test_args(self, model: str) -> str:
        config_name = LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        logger.info("model=%s qsfp_test_config=%s", model, config_name)
        return (
            f"benchmark --qsfp"
            f" --qsfp-config ./share/qsfp_test_configs/{config_name}.materialized_JSON"
            f" --skip-known-bad-tests {config_name}/{QSFP_BENCH_PHY_SDK}"
        )
