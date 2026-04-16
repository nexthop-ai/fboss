"""
Hardware Test Runner for FBOSS

This module provides a base class and specialized test runners for different FBOSS test types.
Each test runner subclass specifies its default configuration directories.
"""

import logging
import os
from abc import ABC, abstractmethod

from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient

logger = logging.getLogger("test_runner")

# Map normalized HWSKU (from device DB model name) to FBOSS config codename
# for hw_test_configs (SAI/agent tests). Only applies to SaiTestRunner and
# SaiAgentTestRunner — QSFP and link configs already use the hwsku name directly.
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

    def run_test(self, test_context):
        """Run the hardware test on the DUT."""
        logger.info("Running tests")
        self.setup(test_context)

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

        # Build the complete test command
        test_args = self.test_args(hwsku)
        cmd = (
            f"sudo su -c 'cd /opt/fboss && ./bin/run_test.py {test_args} "
            f"--filter_file=/home/admin/tests.conf "
            f"' > {self.testlog_filepath} 2>&1"
        )

        logger.info("Running remote command: %s", cmd)
        test_exit_status, test_output = self.ssh_client.run_cmd(cmd)
        logger.debug("exit_status %s output %s", test_exit_status, test_output)

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

        if test_exit_status != 0:
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
        return f"sai --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON"


class SaiAgentTestRunner(BaseHwTestRunner):
    """Runner for SAI agent tests."""

    def test_args(self, hwsku: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(hwsku, hwsku)
        logger.info("hwsku=%s hw_test_config=%s", hwsku, config_name)
        return f"sai_agent --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON"


class QsfpTestRunner(BaseHwTestRunner):
    """Runner for QSFP hardware tests."""

    def test_args(self, hwsku: str) -> str:
        return f"qsfp --qsfp-config ./share/qsfp_test_configs/{hwsku}.materialized_JSON"


class LinkTestRunner(BaseHwTestRunner):
    """Runner for link tests."""

    def test_args(self, hwsku: str) -> str:
        # Link test configs use non-standard naming (no .agent. infix)
        return (
            f"link --agent-run-mode mono "
            f"--config ./share/link_test_configs/{hwsku}.materialized_JSON "
            f"--qsfp-config ./share/qsfp_test_configs/{hwsku}.materialized_JSON"
        )


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
