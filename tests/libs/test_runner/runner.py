"""
Hardware Test Runner for FBOSS

This module provides a base class and specialized test runners for different FBOSS test types.
Each test runner subclass specifies its default configuration directories.
"""

import logging
import os
import time
import shlex
from abc import ABC, abstractmethod

from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient

logger = logging.getLogger("test_runner")

# Map normalized HWSKU (from device DB model name) to FBOSS config codename
# for hw_test_configs (SAI/agent tests). Only applies to SaiTestRunner and
# SaiAgentTestRunner.
#
# Wedge800 naming: B/C = Broadcom/Cisco ASIC, ACT/NHP = Accton/Nexthop vendor.
# ACT DUTs use NHP configs (same ASIC, different manufacturer).
#
# Sources of truth:
#   - fboss/fboss/lib/platforms/PlatformProductInfo.cpp (model -> PlatformType)
#   - fboss/fboss/oss/hw_test_configs/ (available config files)
_HW_TEST_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "wedge800bact": "wedge800bnhp",
    # "wedge800cact": "wedge800cnhp",  # TODO: add when cnhp config is checked in
}

# vendor/coldboot-sai/warmboot-sai/asic — key for run_test.py
# --skip-known-bad-tests against ./share/hw_known_bad_tests/sai*_known_bad_tests.
# Without this, ~128 known-broken tests for tomahawk5 (and the unsupported list)
# run and fail, gutting the pass rate. run_test.py auto-tries the /mono or
# /multi_switch suffix for the sai_agent file, so the same 4-tuple covers both
# SaiTestRunner and SaiAgentTestRunner.
_SAI_KNOWN_BAD_KEY: dict[str, str] = {
    "minipack3": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800bact": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "wedge800bnhp": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
}


def _sai_skip_known_bad(hwsku: str) -> str:
    key = _SAI_KNOWN_BAD_KEY.get(hwsku)
    return f" --skip-known-bad-tests {key}" if key else ""


# Stale-state cleanup paths — must match AgentDirectoryUtil defaults
# (fboss/agent/AgentDirectoryUtil.cpp):
#   getWarmBootDir() = FLAGS_volatile_state_dir + "/warm_boot"
#                      (default /dev/shm/fboss/warm_boot)
#   agentEnsembleConfigDir() = FLAGS_persistent_state_dir + "/agent_ensemble/"
#                      (default /var/facebook/fboss/agent_ensemble/)
_WARM_BOOT_DIR = "/dev/shm/fboss/warm_boot"
_AGENT_ENSEMBLE_DIR = "/var/facebook/fboss/agent_ensemble"

# Link test configs use non-standard naming (no .agent. infix), so kept
# separate from _HW_TEST_CONFIG_NAME.
_LINK_TEST_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
}


class BaseHwTestRunner(ABC):
    """Base class for hardware test runners."""

    def __init__(self):
        self.connected = False
        self.ssh_client = None
        self.scp_client = None
        self.filter_filepath = "/home/admin/tests.conf"
        self.testlog_filepath = "/home/admin/test.log"
        self.testresult_filepath = "/home/admin/tr.xml"
        self.tc = None

    @abstractmethod
    def test_args(self, hwsku: str) -> str:
        """Returns run_test.py command arguments for this test type.

        Args:
            hwsku: Hardware SKU (already normalized to lowercase without dashes)

        Returns:
            Command arguments as string.
            Example: "sai --config ./share/hw_test_configs/nh4010.agent.materialized_JSON"
        """

    def getenvvars(self):
        """Load environment variables into test context."""
        self.tc["dut"] = os.getenv("DUT")
        self.tc["username"] = os.getenv("DUTUSERNAME", "root")
        self.tc["password"] = os.getenv("DUTPASSWORD", "root")
        self.tc["hwsku"] = os.getenv("HWSKU")
        self.tc["filepath"] = os.getenv("TESTFILE")
        logger.info("dut %s", self.tc['dut'])
        logger.info("filepath %s", self.tc['filepath'])

    def setup(self, test_context):
        """Set up SSH/SCP connections to the DUT."""
        logger.debug("Setting up test")
        self.tc = test_context.copy()
        self.getenvvars()

        self.ssh_client = DeviceSSHClient(
            self.tc["dut"],
            device_username=self.tc["username"],
            device_password=self.tc["password"],
            debug=True,
        )
        self.scp_client = DeviceSCPClient(
            self.tc["dut"],
            device_username=self.tc["username"],
            device_password=self.tc["password"],
            debug=True,
        )
        self.connected = True

    def set_filters(self, src_filepath, dst_filepath):
        """Create and upload test filter file to DUT."""
        logger.debug("Setting filters")
        filters = self.tc["filters"]
        # create filters file
        with open(src_filepath, "w", encoding="utf-8") as f:
            for test_filter in filters:
                f.write(f"{test_filter}\n")
        exit_status, output = self.scp_client.put_file(src_filepath, dst_filepath)
        if exit_status != 0:
            logger.error("Failed to copy filter file: %s", output)
            return False
        return True

    def normalize_test_results_file(self):
        """Normalize test results XML file."""
        logger.info("Normalizing test results file")
        if not os.path.exists("/tmp/tr.xml"):
            logger.warning("tr.xml not found, skipping normalization")
            return
        with open("/tmp/tr.xml", encoding="utf-8") as f:
            lines = f.readlines()

        with open("/tmp/tr.xml", "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip().startswith("<testsuite"):
                    line = line.replace(
                        'name="AllTests"', f"name=\"{self.tc['filepath']}\""
                    )
                elif line.strip().startswith("<testcase"):
                    classname = line.split('classname="')[1].split('"')[0]
                    classname = classname.split("/")[0]
                    name = line.split('name="')[1].split('"')[0]
                    line = line.replace(f'name="{name}"', f'name="{classname}.{name}"')
                f.write(line)

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        return exit_status != 0

    def pre_test(self):
        """Wipe stale agent-ensemble state before each test.

        AgentEnsemble::setBootType picks WARM_BOOT iff
        <warm_boot_dir>/can_warm_boot exists, but only the COLD_BOOT path
        in AgentEnsemble::setupEnsemble writes agent.conf. A stale marker
        without a paired agent.conf wedges every test in SetUp() with
        'unable to read .../agent.conf'. This is the dominant TE failure
        mode (~43% of FAIL runs in T-Recs over the last month) because
        TE batches run back-to-back without re-imaging between them,
        unlike devs who install fresh images per run.

        Force a known cold-boot state on every invocation by removing the
        can_warm_boot marker (so setBootType returns COLD_BOOT) and the
        agent_ensemble dir (so the cold-boot path writes a fresh
        agent.conf from --config). AgentEnsemble re-creates the dir via
        utilCreateDir(), so removal is safe.
        """
        cmd = (
            f"sudo rm -f {_WARM_BOOT_DIR}/can_warm_boot* "
            f"&& sudo rm -rf {_AGENT_ENSEMBLE_DIR}"
        )
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.warning("pre_test state cleanup failed: %s", output)

    def post_test(self):
        pass

    def build_test_cmd(self, hwsku: str) -> str:
        test_args = self.test_args(hwsku)
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {test_args} --filter_file=/home/admin/tests.conf "
            f"' > {self.testlog_filepath} 2>&1"
        )

    def run_test(self, test_context):
        """Run the hardware test on the DUT."""
        logger.info("Running tests")
        self.setup(test_context)

        for local_path in ("/tmp/test.log", "/tmp/tr.xml"):
            if os.path.exists(local_path):
                os.unlink(local_path)

        # Ensure /home/admin exists on the DUT — prepare creates it during
        # _post_image_actions, but it may be missing if the DUT was reimaged
        # without a full prepare cycle or if the directory was cleaned up.
        exit_status, output = self.ssh_client.run_cmd(
            "sudo mkdir -p /home/admin && sudo chmod 755 /home/admin"
        )
        if exit_status != 0:
            logger.warning("Failed to ensure /home/admin exists: %s", output)

        status = self.set_filters("/tmp/tests.conf", self.filter_filepath)
        if not status:
            return False

        hwsku = self.tc["hwsku"]
        # shorten hwsku from NH-4010-F to nh4010f
        hwsku = hwsku.lower().replace("-", "")

        logger.info(
            "Clearing remote files: /home/admin/test.log and /home/admin/tr.xml"
        )
        cmd = f"rm -f {self.testlog_filepath} {self.testresult_filepath}"
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error("Failed to run command: %s %s", cmd, output)
            return False

        self.pre_test()
        try:
            cmd = self.build_test_cmd(hwsku)
            logger.info("Running remote command: %s", cmd)
            test_exit_status, test_output = self.ssh_client.run_cmd(cmd)
            logger.debug("exit_status %s output %s", test_exit_status, test_output)
        finally:
            self.post_test()

        logger.info("Fetching test logs and results files")
        exit_status, output = self.scp_client.get_file(
            self.testlog_filepath, "/tmp/test.log"
        )
        if exit_status != 0:
            logger.error("Failed to fetch test logs: %s", output)
            return False

        exit_status, output = self.scp_client.get_file(
            self.testresult_filepath, "/tmp/tr.xml"
        )
        if exit_status != 0:
            logger.warning("Failed to fetch test results (tr.xml may not exist if binary crashed): %s", output)

        self.normalize_test_results_file()

        if self.binary_exit_is_fatal(test_exit_status):
            logger.error("Failed to run tests: %s", test_output)
            return False

        return True

    def close(self):
        """Close connections."""
        self.connected = False


# Concrete test runner implementations

class SaiTestRunner(BaseHwTestRunner):
    """Runner for SAI hardware tests."""

    def test_args(self, hwsku: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(hwsku, hwsku)
        logger.info("hwsku=%s hw_test_config=%s", hwsku, config_name)
        return f"sai --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{_sai_skip_known_bad(hwsku)}"


class SaiAgentTestRunner(BaseHwTestRunner):
    """Runner for SAI agent tests."""

    def test_args(self, hwsku: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(hwsku, hwsku)
        logger.info("hwsku=%s hw_test_config=%s", hwsku, config_name)
        return f"sai_agent --agent-run-mode mono --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{_sai_skip_known_bad(hwsku)}"


class QsfpTestRunner(BaseHwTestRunner):
    """Runner for QSFP hardware tests."""

    def test_args(self, hwsku: str) -> str:
        return f"qsfp --qsfp-config /etc/coop/qsfp.conf"


class LinkTestRunner(BaseHwTestRunner):
    """Runner for link tests."""

    def test_args(self, hwsku: str) -> str:
        config_name = _LINK_TEST_CONFIG_NAME.get(hwsku, hwsku)
        args = (
            "link --agent-run-mode mono "
            f"--config ./share/link_test_configs/{config_name}.materialized_JSON "
            "--qsfp-config /etc/coop/qsfp.conf"
        )
        if hwsku == "wedge800cact":
            # warmboot acting strange, will readd once fixed
            args += " --coldboot_only"
        return args


class PlatformTestRunner(BaseHwTestRunner):
    """Runner for platform services hardware tests.

    Supports all platform test types via the --type flag:
    platform_hw_test, fan_service_hw_test, sensor_service_hw_test,
    fw_util_hw_test, weutil_hw_test, data_corral_service_hw_test,
    platform_manager_hw_test.
    """

    def __init__(self, test_type="platform_hw_test"):
        super().__init__()
        self.test_type = test_type

    def test_args(self, hwsku: str) -> str:
        return f"platform --type {self.test_type}"

class BspTestRunner(BaseHwTestRunner):
    """Runner for BSP hardware tests. Invokes bsp_tests binary directly."""

    BSP_DISABLE_SERVICES = [
        "fan_service",
        "qsfp_service",
    ]

    def test_args(self, hwsku: str) -> str:
        return ""

    def build_test_cmd(self, hwsku: str) -> str:
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f"./bin/bsp_tests --enable_stress_tests "
            f"--gtest_output=xml:{self.testresult_filepath}' "
            f"> {self.testlog_filepath} 2>&1"
        )

    def pre_test(self):
        """Disable FBOSS services that conflict with BSP tests."""
        services = " ".join(self.BSP_DISABLE_SERVICES)
        logger.info("Stopping services for BSP tests: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl mask {services}")
        self.ssh_client.run_cmd(f"sudo systemctl stop {services}")
        time.sleep(2)
        logger.info("Services stopped")

    def set_filters(self, src_filepath, dst_filepath):
        """BSP tests run all cases via the bsp_tests binary — no filter file needed."""
        return True

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        return not os.path.exists("/tmp/tr.xml")

    def normalize_test_results_file(self):
        super().normalize_test_results_file()

        if not os.path.exists("/tmp/tr.xml"):
            return

        with open("/tmp/tr.xml", encoding="utf-8") as f:
            lines = f.readlines()

        if not any(line.lstrip().startswith("<testsuites") for line in lines):
            return

        logger.info("Collapsing BSP testsuites into a single suite")

        out = []
        for line in lines:
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            if stripped.startswith("<testsuites"):
                out.append(line)
                inner = stripped.replace("<testsuites", "<testsuite", 1)
                if 'skipped="' not in inner:
                    inner = inner.replace("<testsuite", '<testsuite skipped="0"', 1)
                out.append(indent + "  " + inner)
            elif stripped.startswith("</testsuites>"):
                out.append(indent + "  </testsuite>\n")
                out.append(line)
            elif stripped.startswith("<testsuite") or stripped.startswith("</testsuite>"):
                continue
            else:
                out.append(line)

        with open("/tmp/tr.xml", "w", encoding="utf-8") as f:
            f.writelines(out)

    def post_test(self):
        """Re-enable FBOSS services after BSP tests.

        platform_manager must restart first so it re-explores and rebuilds
        /run/devmap/ — BSP stress tests reload kmods which invalidate the
        symlinks qsfp_service opens (/run/devmap/xcvrs/xcvr_io_N).
        """
        services = " ".join(self.BSP_DISABLE_SERVICES)
        logger.info("Re-enabling services: %s", services)
        self.ssh_client.run_cmd(f"sudo systemctl unmask {services}")

        self.ssh_client.run_cmd("sudo systemctl restart platform_manager")
        self.ssh_client.run_cmd(
            "sudo bash -c 'for i in $(seq 1 30); do "
            '[ -n "$(ls /run/devmap/xcvrs/ 2>/dev/null)" ] && exit 0; '
            "sleep 1; done; exit 0'"
        )

        self.ssh_client.run_cmd(f"sudo systemctl restart {services}")
        logger.info("Services restart initiated")

class SmokeTestRunner(BaseHwTestRunner):
    """Runner for the FBOSS agent smoke test.

    Unlike the gtest-based runners above, this one invokes
    ``agent_smoke.py`` directly on the DUT — no filter file, no
    ``run_test.py`` indirection — and consumes the JUnit XML it produces
    at ``self.testresult_filepath``.
    """

    AGENT_SMOKE_PATH = "/opt/fboss/bin/python_tests/agent_smoke.py"

    def test_args(self, hwsku: str) -> str:
        # Unused; SmokeTestRunner overrides run_test entirely.
        return ""

    def _build_remote_cmd(self) -> str:
        parts = [
            "python3",
            self.AGENT_SMOKE_PATH,
            "--results-xml",
            self.testresult_filepath,
        ]
        for key, flag in (
            ("stability_window", "--stability-window"),
            ("startup_timeout", "--startup-timeout"),
            ("expected_hw_agents", "--expected-hw-agents"),
            ("services", "--services"),
        ):
            value = self.tc.get(key)
            if value is not None and value != "":
                parts += [flag, str(value)]
        return shlex.join(parts)

    def run_test(self, test_context):
        logger.info("Running agent smoke test")
        self.setup(test_context)

        # Ensure /home/admin exists; the redirect below runs as the SSH user
        # (sudo applies only to the script body), so a missing dir would
        # break test.log / tr.xml capture.
        exit_status, output = self.ssh_client.run_cmd(
            "sudo mkdir -p /home/admin && sudo chmod 755 /home/admin"
        )
        if exit_status != 0:
            logger.warning("Failed to ensure /home/admin exists: %s", output)

        cmd = (
            f"sudo rm -f {self.testlog_filepath} {self.testresult_filepath}"
        )
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error("Failed to clear remote files: %s %s", cmd, output)
            return False

        remote = self._build_remote_cmd()
        cmd = f"sudo {remote} > {self.testlog_filepath} 2>&1"
        logger.info("Running remote command: %s", cmd)
        smoke_status, output = self.ssh_client.run_cmd(cmd)
        logger.debug("smoke exit_status %s output %s", smoke_status, output)

        for remote_path, local_path in (
            (self.testlog_filepath, "/tmp/test.log"),
            (self.testresult_filepath, "/tmp/tr.xml"),
        ):
            exit_status, output = self.scp_client.get_file(
                remote_path, local_path
            )
            if exit_status != 0:
                logger.error(
                    "Failed to fetch %s: %s", remote_path, output
                )
                return False

        if smoke_status != 0:
            logger.error("agent_smoke.py exited %s; see /tmp/tr.xml",
                         smoke_status)
            return False
        return True
