"""fboss2 CLI integration test runner."""

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_SHARE


class Fboss2IntegrationTestRunner(BaseHwTestRunner):
    """Runner for fboss2 CLI integration tests.

    fboss2_integration_test is a gtest binary that drives fboss2-dev CLI
    commands against a running FBOSS instance and verifies their output. It
    is SAI/platform-independent — it talks to the agent over Thrift — so
    unlike the SAI/agent runners it needs no --config or per-model
    known-bad-test key. run_test.py's fboss2_integration subcommand resolves
    both internally (/etc/coop/agent.conf and the bundled
    fboss2_integration_known_bad_tests file).
    """

    # fboss2_integration_test ships in the forwarding test tarball
    # (FORWARDING_TEST_BINARIES) alongside its known-bad-tests file
    # (FORWARDING_TEST_EXTRA) — see fboss/oss/scripts/package.py. run_test.py,
    # fboss2-dev and setup_fboss_env come from the production forwarding image
    # already on the DUT, so (like the other forwarding runners) they're not
    # listed here.
    STACK = STACK_FORWARDING
    BINARIES = ("bin/fboss2_integration_test",)
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    def test_args(self, model: str) -> str:
        return "fboss2_integration"

    def pre_test(self):
        """No-op: run_test.py fboss2_integration owns the agent lifecycle.

        The fboss2_integration subcommand detects whether production
        multi-switch agents are already running, snapshots their config, and
        cold-boots both agents per test (restoring on teardown). The base
        class warm-boot-state wipe would race with that prod-agent detection,
        so we deliberately skip it here.
        """
