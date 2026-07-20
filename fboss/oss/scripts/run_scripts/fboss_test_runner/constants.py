#!/usr/bin/env python3
# @noautodeps
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# Common argparse option strings shared across run_test.py and multiple runners
OPT_ARG_COLDBOOT = "--coldboot_only"
OPT_ARG_FILTER = "--filter"
OPT_ARG_FILTER_FILE = "--filter_file"
OPT_ARG_PROFILE = "--profile"
OPT_ARG_LIST_TESTS = "--list_tests"
OPT_ARG_CONFIG_FILE = "--config"
OPT_ARG_QSFP_CONFIG_FILE = "--qsfp-config"
OPT_ARG_PLATFORM_MAPPING_OVERRIDE_PATH = "--platform_mapping_override_path"
OPT_ARG_BSP_PLATFORM_MAPPING_OVERRIDE_PATH = "--bsp_platform_mapping_override_path"
OPT_ARG_SAI_REPLAYER_LOGGING = "--sai_replayer_logging"
OPT_ARG_SKIP_KNOWN_BAD_TESTS = "--skip-known-bad-tests"
OPT_ARG_MGT_IF = "--mgmt-if"
OPT_ARG_FRUID_PATH = "--fruid-path"
OPT_ARG_SIMULATOR = "--simulator"
OPT_ARG_SAI_LOGGING = "--sai_logging"
OPT_ARG_FBOSS_LOGGING = "--fboss_logging"
OPT_KNOWN_BAD_TESTS_FILE = "--known-bad-tests-file"
OPT_UNSUPPORTED_TESTS_FILE = "--unsupported-tests-file"
OPT_ARG_SETUP_CB = "--setup-for-coldboot"
OPT_ARG_SETUP_WB = "--setup-for-warmboot"
OPT_ARG_TEST_RUN_TIMEOUT = "--test-run-timeout"
OPT_ARG_NUM_WARMBOOT_ITERATIONS = "--num-warmboot-iterations"
OPT_ARG_DISABLE_FSDB = "--disable-fsdb"
OPT_ARG_FSDB_CONFIG_FILE = "--fsdb-config"

# Subcommand names
SUB_CMD_BCM = "bcm"
SUB_CMD_SAI = "sai"
SUB_CMD_QSFP = "qsfp"
SUB_CMD_LINK = "link"
SUB_CMD_SAI_AGENT = "sai_agent"
SUB_CMD_SAI_AGENT_SCALE = "sai_agent_scale"
SUB_CMD_SAI_INVARIANT_AGENT = "sai_invariant_agent"
SUB_CMD_PLATFORM = "platform"
SUB_CMD_LED = "led"
SUB_CMD_FBOSS2_INTEGRATION = "fboss2_integration"
SUB_CMD_BENCHMARK = "benchmark"

# Subcommand args shared across multiple runners
SUB_ARG_AGENT_RUN_MODE = "--agent-run-mode"
SUB_ARG_AGENT_RUN_MODE_MONO = "mono"
SUB_ARG_AGENT_RUN_MODE_MULTI = "multi_switch"
SUB_ARG_NUM_NPUS = "--num-npus"

<<<<<<< HEAD
# Benchmark subcommand args
OPT_ARG_SAI_BENCH = "--sai"
OPT_ARG_QSFP_BENCH = "--qsfp"
OPT_ARG_FORCE_5PIM_FUJI = "--force-5pim-fuji"
OPT_ARG_PORT_MANAGER_MODE = "--port-manager-mode"
=======
# Platform-service test-type names shared between the platform-services runners
# and TEST_DISABLE_SERVICES below. The remaining platform test-type names live
# in platform_services_test_runner.py since they are only used there.
SUB_ARG_PLATFORM_MANAGER_HW_TEST = "platform_manager_hw_test"
SUB_ARG_BSP_HW_TEST = "bsp_tests"
SUB_ARG_LED_HW_TEST = "led_service_hw_test"
SUB_ARG_QSFP_HW_TEST = "qsfp_hw_test"
>>>>>>> f241ee1f3a (NOS-10800: Fix qsfp_hw_test suite on WEDGE800BNHP (#1363))

XGS_SIMULATOR_ASICS = ["th3", "th4", "th4_b0", "th5"]
DNX_SIMULATOR_ASICS = ["j3"]
ALL_SIMUALTOR_ASICS_STR = "|".join(XGS_SIMULATOR_ASICS + DNX_SIMULATOR_ASICS)

# Environment overlaid onto the test process when running against an ASIC
# simulator (selected via --simulator).
XGS_SIMULATOR_ENV: dict[str, str] = {
    "SOC_TARGET_SERVER": "127.0.0.1",
    "BCM_SIM_PATH": "1",
    "SOC_BOOT_FLAGS": "4325376",
    "SAI_BOOT_FLAGS": "4325376",
    "SOC_TARGET_PORT": "22222",
    "SOC_TARGET_COUNT": "1",
}

DNX_SIMULATOR_ENV: dict[str, str] = {
    "BCM_SIM_PATH": "1",
    "SOC_BOOT_FLAGS": "0x1020000",
    "ADAPTER_DEVID_0": "8860",
    "ADAPTER_REVID_0": "1",
    "ADAPTER_SERVER_MODE": "1",
    "CMODEL_DEVID_0": "8860",
    "CMODEL_REVID_0": "1",
    "CMODEL_MEMORY_PORT_0": "1222",
    "CMODEL_PACKET_PORT_0": "6815",
    "CMODEL_SDK_INTERFACE_PORT_0": "6816",
    "CMODEL_EXTERNAL_EVENTS_PORT_0": "6817",
    "cmodel_ip_address": "localhost",
    "SOC_TARGET_SERVER": "localhost",
    "SOC_TARGET_SERVER_0": "localhost",
    "SAI_BOOT_FLAGS": "0x1020000",
}

DEFAULT_TEST_RUN_TIMEOUT_IN_SECOND = 1200

# Shared known-bad / unsupported SAI-agent test list paths (relative to /opt/fboss CWD)
SAI_AGENT_TEST_KNOWN_BAD_TESTS = (
    "./share/hw_known_bad_tests/sai_agent_known_bad_tests.materialized_JSON"
)
SAI_AGENT_UNSUPPORTED_TESTS = (
    "./share/sai_hw_unsupported_tests/sai_agent_hw_unsupported_tests.materialized_JSON"
)
<<<<<<< HEAD
=======

_SAI_AGENT_DISABLE_SERVICES = ["fboss_sw_agent", "fboss_hw_agent@0", "bgpd"]

# Shared by SAI hw_test and link binaries: prod agents hold port 5909 /
# the SAI device; qsfp_service holds the transceivers.
_SAI_DISABLE_SERVICES = ["fboss_sw_agent", "fboss_hw_agent@0", "qsfp_service"]

TEST_DISABLE_SERVICES = {
    # qsfp_hw_test has its own qsfp_service and must own the xcvr i2c bus, but
    # the prod qsfp_service and led_service both poll it
    SUB_ARG_QSFP_HW_TEST: ["qsfp_service", "led_service"],
    SUB_ARG_BSP_HW_TEST: ["fan_service", "qsfp_service", "led_service"],
    SUB_ARG_PLATFORM_MANAGER_HW_TEST: [
        "platform_manager",
        "sensor_service",
        "fan_service",
        "data_corral_service",
        "qsfp_service",
        "led_service",
    ],
    SUB_CMD_SAI_BINARY: _SAI_DISABLE_SERVICES,
    SUB_CMD_SAI_AGENT_MONO_BINARY: _SAI_AGENT_DISABLE_SERVICES,
    SUB_CMD_SAI_AGENT_MULTI_BINARY: _SAI_AGENT_DISABLE_SERVICES,
    SUB_CMD_LINK_MONO_BINARY: _SAI_AGENT_DISABLE_SERVICES,
    SUB_CMD_LINK_MULTI_BINARY: _SAI_AGENT_DISABLE_SERVICES,
}

>>>>>>> f241ee1f3a (NOS-10800: Fix qsfp_hw_test suite on WEDGE800BNHP (#1363))
# Scale-specific known-bad list (scale test names differ from functional ones).
SAI_AGENT_SCALE_KNOWN_BAD_TESTS = (
    "./share/hw_known_bad_tests/sai_agent_scale_known_bad_tests.materialized_JSON"
)
