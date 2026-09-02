"""FBOSS agent smoke test runner."""

import logging
import shlex

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import STACK_FORWARDING

logger = logging.getLogger("test_runner")


class SmokeTestRunner(BaseHwTestRunner):
    """Runner for the FBOSS agent smoke test.

    Unlike the gtest-based runners, this one invokes ``agent_smoke.py``
    directly on the DUT — no filter file, no ``run_test.py`` indirection —
    and consumes the JUnit XML it produces at ``self.testresult_filepath``.
    """

    # agent_smoke.py and junit.py live in the forwarding test tarball under
    # bin/python_tests/ — see FORWARDING_TEST_EXTRA in
    # fboss/oss/scripts/package.py.
    STACK = STACK_FORWARDING
    # Smoke drives agent_smoke.py directly (no run_test.py, no share configs),
    # so it ships only its scripts — not the forwarding share tree.
    BINARIES = (
        "bin/python_tests/agent_smoke.py",
        "bin/python_tests/junit.py",
    )
    REQUIRED_PATHS = BINARIES

    AGENT_SMOKE_PATH = "/opt/fboss/bin/python_tests/agent_smoke.py"

    def test_args(self, model: str) -> str:
        # Unused; SmokeTestRunner overrides _run_test_impl (drives agent_smoke.py
        # directly, not run_test.py), so no test_args are built.
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

    def _run_test_impl(self, test_context, skip_tr_xml=False):
        logger.info("Running agent smoke test")

        cmd = f"sudo rm -f {self.testlog_filepath} {self.testresult_filepath}"
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
            exit_status, output = self.scp_client.get_file(remote_path, local_path)
            if exit_status != 0:
                logger.error("Failed to fetch %s: %s", remote_path, output)
                return False

        if smoke_status != 0:
            logger.error("agent_smoke.py exited %s; see /tmp/tr.xml", smoke_status)
            return False
        return True
