"""Platform-stack hardware test runners: platform services and BSP."""

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.deploy import STACK_PLATFORM, STACK_SHARE


class PlatformTestRunner(BaseHwTestRunner):
    """Runner for platform services hardware tests.

    Supports all platform test types via the --type flag:
    platform_hw_test, fan_service_hw_test, sensor_service_hw_test,
    fw_util_hw_test, weutil_hw_test, data_corral_service_hw_test,
    platform_manager_hw_test.
    """

    STACK = STACK_PLATFORM
    BINARIES = (
        "bin/platform_hw_test",
        "bin/fan_service_hw_test",
        "bin/sensor_service_hw_test",
        "bin/fw_util_hw_test",
        "bin/weutil_hw_test",
        "bin/data_corral_service_hw_test",
        "bin/platform_manager_hw_test",
    )
    # run_test.py and setup_fboss_env come from the production image already on
    # the DUT (same as the forwarding runners and BspTestRunner), so only the
    # test binaries ship. Platform tests read no share/ configs
    # (STACK_SHARE[platform] is empty).
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    def __init__(self, test_type="platform_hw_test"):
        super().__init__()
        self.test_type = test_type

    def test_args(self, model: str) -> str:
        return f"platform --type {self.test_type}"


class BspTestRunner(BaseHwTestRunner):
    """Runner for BSP hardware tests. Delegates to run_test.py bsp.

    All service lifecycle management (fan_service, qsfp_service, led_service
    stop/start, platform_manager restart, /run/devmap wait) and the
    --enable_stress_tests flag are handled on-DUT by run_test.py bsp.
    """
    STACK = STACK_PLATFORM
    BINARIES = ("bin/bsp_tests",)
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    def test_args(self, model: str) -> str:
        return "bsp"

    def set_filters(self, src_filepath, dst_filepath):
        """BSP runs all cases via run_test.py bsp — no filter file needed."""
        return True

    def build_test_cmd(self, model: str) -> str:
        # Omit --filter_file so run_test.py bsp runs all cases (see set_filters).
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {self.test_args(model)} "
            f"' > {self.testlog_filepath} 2>&1"
        )
