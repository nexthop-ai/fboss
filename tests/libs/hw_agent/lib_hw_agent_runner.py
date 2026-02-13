# hw_agent_runner.py

import os
import pytest
import logging
from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient

# Configure logging to ensure it works with pytest
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hw_agent_runner")


class HwAgentTestRunner:
    """Test runner for hardware agent operations."""

    def __init__(
        self,
    ):
        self.connected = False
        self.ssh_client = None
        self.scp_client = None
        self.filter_filepath = "/home/admin/tests.conf"
        self.testlog_filepath = "/home/admin/test.log"
        self.testresult_filepath = "/home/admin/tr.xml"
        self.tc = None

    def getenvvars(self):
        self.tc["dut"] = os.getenv("DUT")
        self.tc["username"] = os.getenv("DUTUSERNAME", "root")
        self.tc["password"] = os.getenv("DUTPASSWORD", "root")
        self.tc["hwsku"] = os.getenv("HWSKU")
        self.tc["filepath"] = os.getenv("TESTFILE")
        logger.info(f"dut {self.tc['dut']}")
        logger.info(f"filepath {self.tc['filepath']}")

    def setup(self, test_context):
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
        logger.debug("Setting filters")
        filters = self.tc["filters"]
        # create filters file
        with open(src_filepath, "w") as f:
            for filter in filters:
                f.write(f"{filter}\n")
        exit_status, output = self.scp_client.put_file(src_filepath, dst_filepath)
        if exit_status != 0:
            logger.error(f"Failed to copy filter file: {output}")
            return False
        return True

    def normalize_test_results_file(self):
        logger.info("Normalizing test results file")
        with open("/tmp/tr.xml", "r") as f:
            lines = f.readlines()

        with open("/tmp/tr.xml", "w") as f:
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
        logger.info("Running tests")
        self.setup(test_context)

        status = self.set_filters("/tmp/tests.conf", self.filter_filepath)
        if not status:
            return False

        hwsku = self.tc["hwsku"]
        # shorten hwsku from NH-4010 to nh4010
        hwsku = hwsku.lower().replace("-", "")

        logger.info(
            "Clearing remote files: /home/admin/test.log and /home/admin/tr.xml"
        )
        cmd = f"rm -f {self.testlog_filepath} {self.testresult_filepath}"
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error(f"Failed to run command: {cmd} {output}")
            return False

        cmd = "sudo su -c 'cd /opt/fboss && ./bin/run_test.py sai --filter_file=/home/admin/tests.conf "
        cmd += f"--config ./share/hw_test_configs/{hwsku}.agent.materialized_JSON --sai-bin bin/sai_test-sai_impl' > {self.testlog_filepath} 2>&1"
        logger.info(f"Running remote command: {cmd}")
        exit_status, output = self.ssh_client.run_cmd(cmd)
        logger.debug(f"exit_status {exit_status} output {output}")

        if exit_status != 0:
            logger.error(f"Failed to run tests: {output}")
            return False
        else:
            logger.info("Fetching test logs and results files")
            exit_status, output = self.scp_client.get_file(
                self.testlog_filepath, "/tmp/test.log"
            )
            if exit_status != 0:
                logger.error(f"Failed to fetch test logs: {output}")
                return False

            exit_status, output = self.scp_client.get_file(
                self.testresult_filepath, "/tmp/tr.xml"
            )
            if exit_status != 0:
                logger.error(f"Failed to fetch test results: {output}")
                return False

            self.normalize_test_results_file()
        return True

    def close(self):
        self.connected = False


@pytest.fixture
def hw_agent_test_runner():
    """Fixture that provides a HwAgentTestRunner instance with automatic cleanup."""
    runner = HwAgentTestRunner()
    yield runner
    runner.close()
