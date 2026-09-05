"""Base class for the FBOSS hardware test runners.

Owns the runner lifecycle: DUT connections, artifact deploy (delegated to
deploy.ArtifactDeployer), filter upload, remote test execution, and result
normalization. Concrete runners live in runners/.
"""

import functools
import json
import logging
import os
import tempfile
import time
from abc import ABC, abstractmethod

from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient
from tests.libs.test_runner import junit
from tests.libs.test_runner.deploy import (
    ENV_DEPLOY_ONLY,
    ENV_DEPLOY_ONLY_ON,
    ArtifactDeployer,
)

logger = logging.getLogger("test_runner")

# Floor (seconds) for how long a *failing* test run must occupy before
# run_test returns False.
MIN_FAILURE_DURATION_SECS = 120


def _enforce_min_failure_duration(run_test):
    """Decorator: pad a failing run out to MIN_FAILURE_DURATION_SECS.

    TE batches re-run failing tests back-to-back without re-imaging between
    them. A binary that aborts early (e.g. crashing in SetUp() in seconds)
    produces a tight fail-retry loop that hammers the DUT and floods T-Recs
    with near-instant failures. Padding any failing run to a fixed floor
    keeps the surrounding retry cadence sane. Successful runs are never
    delayed.

    Wraps the single template run_test() entry point; per-runner execution
    lives in _run_test_impl(), which is not decorated, so a run is padded at
    most once regardless of how many subclass layers it passes through.

    Deploy-only runs (FBOSS_DEPLOY_ONLY) are exempt: they stage artifacts and
    return without executing the test, so there is no fail-retry loop to pad.
    """

    @functools.wraps(run_test)
    def wrapper(self, *args, **kwargs):
        start = time.monotonic()
        success = run_test(self, *args, **kwargs)
        # Deploy-only runs stage artifacts and exit without executing the test,
        # so there's no fail-retry loop to protect against — never pad them.
        deploy_only = os.environ.get(ENV_DEPLOY_ONLY) == ENV_DEPLOY_ONLY_ON
        if not success and not deploy_only:
            remaining = MIN_FAILURE_DURATION_SECS - (time.monotonic() - start)
            if remaining > 0:
                logger.info(
                    "Run failed; padding to %ds floor (sleeping %.1fs)",
                    MIN_FAILURE_DURATION_SECS,
                    remaining,
                )
                time.sleep(remaining)
        return success

    return wrapper


def normalize_model(model: str) -> str:
    """Shorten device-DB model name to FBOSS codename form, e.g. NH-4010-F -> nh4010f."""
    return model.lower().replace("-", "")


# Stale-state cleanup paths — must match AgentDirectoryUtil defaults
# (fboss/agent/AgentDirectoryUtil.cpp):
#   getWarmBootDir() = FLAGS_volatile_state_dir + "/warm_boot"
#                      (default /dev/shm/fboss/warm_boot)
#   agentEnsembleConfigDir() = FLAGS_persistent_state_dir + "/agent_ensemble/"
#                      (default /var/facebook/fboss/agent_ensemble/)
_WARM_BOOT_DIR = "/dev/shm/fboss/warm_boot"
_AGENT_ENSEMBLE_DIR = "/var/facebook/fboss/agent_ensemble"


class BaseHwTestRunner(ABC):
    """Base class for hardware test runners."""

    _REMOTE_CONFIG_PATH: str

    # Which FBOSS stack this runner's binaries come from.  Subclasses set this
    # to STACK_FORWARDING or STACK_PLATFORM (deploy.py); it selects the Nexis
    # artifact name and the local CMake build subdir.
    STACK: str = ""

    # Paths inside the extracted tarball that this runner needs on the DUT.
    # Trailing "/" requests a directory; everything else is treated as a single
    # file.  These are resolved against the extracted tarball root on the
    # runner host and SCP'd to the matching location under /opt/fboss/ on
    # the DUT.
    REQUIRED_PATHS: tuple[str, ...] = ()

    def __init__(self):
        self.connected = False
        self.ssh_client = None
        self.scp_client = None
        self.filter_filepath = "/home/netops/tests.conf"
        self.testlog_filepath = "/home/netops/test.log"
        self.testresult_filepath = "/home/netops/tr.xml"
        self.tc = None
        self._use_generated_config = False
        self._fboss_logging = None
        self._test_run_timeout_secs: int | None = None

    def _upload_generated_config(self, config: dict) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".materialized_JSON", delete=False) as f:
            json.dump(config, f, indent=4)
            local_path = f.name
        try:
            exit_status, output = self.scp_client.put_file(local_path, self._REMOTE_CONFIG_PATH)
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            raise RuntimeError(f"Failed to upload generated config: {output}")
        self._use_generated_config = True

    @abstractmethod
    def test_args(self, model: str) -> str:
        """Returns run_test.py command arguments for this test type.

        Args:
            model: Product model (already normalized to lowercase without dashes)

        Returns:
            Command arguments as string.
            Example: "sai --config ./share/hw_test_configs/nh4010.agent.materialized_JSON"
        """

    def getenvvars(self):
        """Load environment variables into test context."""
        self.tc["dut"] = os.getenv("DUT")
        self.tc["username"] = os.getenv("DUTUSERNAME", "root")
        self.tc["password"] = os.getenv("DUTPASSWORD", "root")
        # HWSKU environment variable deprecated in favor of PRODUCT_MODEL
        self.tc["model"] = os.getenv("HWSKU", os.getenv("PRODUCT_MODEL"))
        self.tc["filepath"] = os.getenv("TESTFILE")
        self.tc["gtest_filter"] = os.getenv("TESTFILTER")
        logger.info("dut %s", self.tc["dut"])
        logger.info("filepath %s", self.tc["filepath"])

    def setup(self, test_context):
        """Set up SSH/SCP connections to the DUT and deploy this runner's test artifacts."""
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

        self._deploy_artifacts()

    def _deploy_artifacts(self) -> None:
        """Deploy this runner's test binary slice onto the DUT."""
        ArtifactDeployer(
            runner_name=type(self).__name__,
            stack=self.STACK,
            required_paths=self.REQUIRED_PATHS,
            ssh_client=self.ssh_client,
            scp_client=self.scp_client,
        ).deploy()

    def set_filters(self, src_filepath, dst_filepath):
        """Create and upload test filter file to DUT."""
        logger.debug("Setting filters")
        # tc["filter"] replaces the per-test-file default filter list with
        # a single gtest-style expression
        override_filter = self.tc.get("gtest_filter")
        filters = [override_filter] if override_filter else self.tc["filters"]
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
        junit.normalize_test_results_file(self.tc["filepath"])

    def binary_exit_is_fatal(self, exit_status: int) -> bool:
        return exit_status != 0

    def _merge_junit_results(
        self,
        passes: list[tuple[str, str, str]],
        skipped: list[tuple[str, str]] = (),
    ) -> None:
        """Merge multiple (label, log_local, xml_local) pass results, plus a
        synthetic <skipped> testcase per (pattern, reason) in ``skipped``,
        into /tmp/test.log and /tmp/tr.xml.
        """
        junit.merge_junit_results(passes, skipped)

    def _execute_test_binary(
        self, model: str, log_local: str, xml_local: str, skip_tr_xml: bool
    ) -> bool:
        """Clear local+remote result files, run the test binary once, fetch results.

        Returns True if the fetch succeeded and the binary's exit status
        isn't fatal.
        """
        for local_path in (log_local, xml_local):
            if os.path.exists(local_path):
                os.unlink(local_path)

        if not self.set_filters("/tmp/tests.conf", self.filter_filepath):
            return False

        cmd = f"sudo rm -f {self.testlog_filepath} {self.testresult_filepath}"
        exit_status, output = self.ssh_client.run_cmd(cmd)
        if exit_status != 0:
            logger.error("Failed to run command: %s %s", cmd, output)
            return False

        cmd = self.build_test_cmd(model)
        logger.info("Running remote command: %s", cmd)
        test_exit_status, test_output = self.ssh_client.run_cmd(cmd)

        exit_status, output = self.scp_client.get_file(self.testlog_filepath, log_local)
        if exit_status != 0:
            logger.error("Failed to fetch test logs: %s", output)
            return False

        if not skip_tr_xml:
            exit_status, output = self.scp_client.get_file(
                self.testresult_filepath, xml_local
            )
            if exit_status != 0:
                logger.warning(
                    "Failed to fetch test results (tr.xml may not exist if binary crashed): %s",
                    output,
                )

        if self.binary_exit_is_fatal(test_exit_status):
            logger.error("Failed to run tests: %s", test_output)
            return False
        return True

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

    def build_test_cmd(self, model: str) -> str:
        test_args = self.test_args(model)
        logging_arg = f" --fboss_logging {self._fboss_logging}" if self._fboss_logging else ""
        timeout = self._test_run_timeout_secs
        timeout_arg = f" --test-run-timeout {timeout}" if timeout is not None else ""
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {test_args} --filter_file={self.filter_filepath}{logging_arg}{timeout_arg} "
            f"' > {self.testlog_filepath} 2>&1"
        )

    @_enforce_min_failure_duration
    def run_test(self, test_context, skip_tr_xml=False, fboss_logging=None):
        """Connect to the DUT, deploy this runner's artifacts, then run the test.

        Template method — do NOT override in subclasses. setup() (SSH/SCP
        connect + _deploy_artifacts) and the deploy-only gate live here so every
        runner deploys identically and honors --mode deploy; a subclass that
        reimplemented run_test() could silently skip the gate. Subclasses
        customize execution by overriding _run_test_impl() instead.

        fboss_logging overrides the test binary's --fboss_logging level for this
        run (default: run_test.py's own DBG4).
        """
        self._fboss_logging = fboss_logging
        logger.info("Running tests")
        self.setup(test_context)

        # Deploy-only: setup() has uploaded this runner's artifact slice to the
        # DUT.  Stop here without running the test binary — nhtests-run
        # --mode deploy sets this to stage artifacts without executing tests.
        if os.environ.get(ENV_DEPLOY_ONLY) == ENV_DEPLOY_ONLY_ON:
            logger.info(
                "%s: %s set; artifacts deployed, skipping test execution",
                type(self).__name__, ENV_DEPLOY_ONLY,
            )
            return True

        return self._run_test_impl(test_context, skip_tr_xml=skip_tr_xml)

    def _run_test_impl(self, test_context, skip_tr_xml=False):
        """Run the hardware test on the DUT.

        Called by run_test() after setup()/deploy, so it starts from a
        connected, artifact-staged DUT. Override per runner to customize
        execution (see SmokeTestRunner, BenchmarkTestRunner).
        """
        for local_path in ("/tmp/test.log", "/tmp/tr.xml"):
            if os.path.exists(local_path):
                os.unlink(local_path)

        status = self.set_filters("/tmp/tests.conf", self.filter_filepath)
        if not status:
            return False

        model = normalize_model(self.tc["model"])

        self.pre_test()
        try:
            success = self._execute_test_binary(
                model, "/tmp/test.log", "/tmp/tr.xml", skip_tr_xml
            )
        finally:
            self.post_test()

        if not skip_tr_xml:
            self.normalize_test_results_file()

        return success

    def close(self):
        """Close connections."""
        self.connected = False
