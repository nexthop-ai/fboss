"""
Hardware Test Runner for FBOSS

This module provides a base class and specialized test runners for different FBOSS test types.
Each test runner subclass specifies its default configuration directories.
"""

import functools
import logging
import os
import time
import shlex
import re
import csv
import copy
import json
import tempfile
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from tests.libs.device.device_ssh_helper import DeviceSCPClient, DeviceSSHClient

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

    Wraps both the base run_test and the SmokeTestRunner/BenchmarkTestRunner
    overrides. Because the floor is measured from the outermost entry, a
    subclass that calls super().run_test() is never double-padded.
    """

    @functools.wraps(run_test)
    def wrapper(self, *args, **kwargs):
        start = time.monotonic()
        success = run_test(self, *args, **kwargs)
        if not success:
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

# Map normalized model (from device DB model name) to FBOSS config codename
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
    "nh4215f": "m4062nhp",
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
    "wedge800cact": "leaba/25.11.4210/25.11.4210/graphene202x",
    "nh4010f": "brcm/13.3.0.0_odp/13.3.0.0_odp/tomahawk5",
    "nh4215f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
    "nh4220f": "brcm/14.2.0.0_odp/14.2.0.0_odp/tomahawk6",
}


def _sai_skip_known_bad(model: str) -> str:
    key = _SAI_KNOWN_BAD_KEY.get(model)
    return f" --skip-known-bad-tests {key}" if key else ""


def _benchmark_skip_known_bad(model: str) -> str:
    # sai_bench.materialized_JSON keys on vendor/sdk/asic (3-part), unlike the SAI
    # known-bad files which use vendor/coldboot-sai/warmboot-sai/asic. Collapse the
    # duplicated SDK segment so the benchmark platform key matches the config;
    # otherwise the lookup misses and unsupported (VOQ/Fabric/SRv6) benchmarks run.
    key = _SAI_KNOWN_BAD_KEY.get(model)
    if not key:
        return ""
    parts = key.split("/")
    if len(parts) == 4 and parts[1] == parts[2]:
        key = f"{parts[0]}/{parts[1]}/{parts[3]}"
    return f" --skip-known-bad-tests {key}"


def _normalize_model(model: str) -> str:
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

# Link test configs use non-standard naming (no .agent. infix), so kept
# separate from _HW_TEST_CONFIG_NAME.
_LINK_TEST_CONFIG_NAME: dict[str, str] = {
    "minipack3": "montblanc",
    "nh4215f": "m4062nhp",
}

# ACT DUTs use the NHP qsfp_test_config so we don't have to touch the
# upstream bact config.
_QSFP_TEST_CONFIG_NAME: dict[str, str] = {
    "wedge800bact": "wedge800bnhp",
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

    def build_test_cmd(self, model: str) -> str:
        test_args = self.test_args(model)
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {test_args} --filter_file=/home/admin/tests.conf "
            f"' > {self.testlog_filepath} 2>&1"
        )

    @_enforce_min_failure_duration
    def run_test(self, test_context, skip_tr_xml=False):
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

        model = _normalize_model(self.tc["model"])

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
            cmd = self.build_test_cmd(model)
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

        if not skip_tr_xml:
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

    def test_args(self, model: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{_sai_skip_known_bad(model)}"


class SaiAgentTestRunner(BaseHwTestRunner):
    """Runner for SAI agent tests."""

    @staticmethod
    def _enable_production_features(model: str) -> str:
        PROD_FEEATURES_KEY: dict[str, str] = {
            "minipack3": "tomahawk5",
            "wedge800bact": "tomahawk5",
            "wedge800bnhp": "tomahawk5",
            "wedge800cact": "g202x",
            "nh4010f": "tomahawk5",
            "nh4215f": "tomahawk6",
            "nh4220f": "tomahawk6",
        }
        key = PROD_FEEATURES_KEY.get(model)
        return f" --enable-production-features {key}" if key else ""

    def test_args(self, model: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"sai_agent --agent-run-mode mono --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON \
            {_sai_skip_known_bad(model)}{self._enable_production_features(model)}"


class QsfpTestRunner(BaseHwTestRunner):
    """Runner for QSFP hardware tests."""

    def test_args(self, model: str) -> str:
        config_name = _QSFP_TEST_CONFIG_NAME.get(model, model)
        return f"qsfp --qsfp-config ./share/qsfp_test_configs/{config_name}.materialized_JSON"


class _PortInfo(NamedTuple):
    logical_id: int
    profile_id: int
    speed: int


class LinkTestRunner(BaseHwTestRunner):
    """Runner for link tests."""

    _CABLING_ENV_VAR = "LINK_TEST_CABLING"
    _BASE_CONFIG_DIR = Path("fboss/oss/link_test_configs")
    _PLATFORM_MAPPING_DIR = Path(
        "fboss/lib/platform_mapping_v2/generated_platform_mappings"
    )
    _REMOTE_CONFIG_PATH = "/home/netops/link_test_config.materialized_JSON"
    _SYSTEM_QSFP_CONFIG_PATH = "/etc/coop/qsfp.conf"
    _REMOTE_QSFP_CONFIG_PATH = "/home/netops/link_test_qsfp.conf"
    # JSON map key for LLDPTag.PORT: see fboss/agent/switch_config.thrift.
    _LLDP_PORT_TAG = "2"

    def __init__(self):
        super().__init__()
        self._use_generated_config = False
        self._use_generated_qsfp = False

    @classmethod
    def _config_name(cls, model: str) -> str:
        return _LINK_TEST_CONFIG_NAME.get(model, model)

    @staticmethod
    def _repo_dir(relative: Path) -> Path:
        for parent in Path(__file__).resolve().parents:
            if (parent / relative).is_dir():
                return parent / relative
        raise FileNotFoundError(f"could not locate {relative} above {__file__}")

    @classmethod
    def _base_config_path(cls, config_name: str) -> Path:
        return cls._repo_dir(cls._BASE_CONFIG_DIR) / f"{config_name}.materialized_JSON"

    @classmethod
    def _load_platform_mapping(cls, config_name: str) -> dict[str, _PortInfo]:
        path = cls._repo_dir(cls._PLATFORM_MAPPING_DIR) / f"{config_name}_platform_mapping.json"
        with open(path, encoding="utf-8") as f:
            mapping = json.load(f)
        speed_of = {
            p["factor"]["profileID"]: p["profile"]["speed"]
            for p in mapping["platformSupportedProfiles"]
        }
        index = {}
        for entry in mapping["ports"].values():
            profiles = [int(pid) for pid in entry["supportedProfiles"]]
            profile_id = max(profiles, key=lambda pid: speed_of.get(pid, 0))
            index[entry["mapping"]["name"]] = _PortInfo(
                entry["mapping"]["id"], profile_id, speed_of.get(profile_id, 0)
            )
        return index

    @classmethod
    def _synthesize_port(
        cls, base_json: dict, port_map: dict[str, _PortInfo], name: str, vlan_id: int
    ) -> dict:
        info = port_map.get(name)
        if info is None:
            raise ValueError(f"netbox port {name} is not in the platform mapping")
        sw = base_json["sw"]
        # The agent requires every port to own exactly one interface, so a synthesized
        # port needs a matching vlan, vlanPort and interface too.
        template = sw["ports"][0]["ingressVlan"]
        port = copy.deepcopy(sw["ports"][0])
        port.update({"logicalID": info.logical_id, "name": name, "state": 2,
                     "speed": info.speed, "profileID": info.profile_id,
                     "ingressVlan": vlan_id})
        vlan = copy.deepcopy(next(v for v in sw["vlans"] if v["id"] == template))
        vlan.update({"id": vlan_id, "intfID": vlan_id, "name": f"vlan{vlan_id}"})
        vlan_port = copy.deepcopy(next(p for p in sw["vlanPorts"] if p["vlanID"] == template))
        vlan_port.update({"vlanID": vlan_id, "logicalPort": info.logical_id})
        intf = copy.deepcopy(next(i for i in sw["interfaces"] if i.get("vlanID") == template))
        intf.update({"intfID": vlan_id, "vlanID": vlan_id, "ipAddresses": []})
        sw["ports"].append(port)
        sw["vlans"].append(vlan)
        sw["vlanPorts"].append(vlan_port)
        sw["interfaces"].append(intf)
        return port

    @classmethod
    def _overlay_cabling(
        cls,
        base_json: dict,
        pairs: dict[str, str],
        port_map: dict[str, _PortInfo],
    ) -> dict:
        if not pairs:
            raise ValueError("refusing to generate link test config: no cabling pairs")
        sw = base_json["sw"]
        by_name = {port["name"]: port for port in sw["ports"]}
        for port in sw["ports"]:
            port["expectedLLDPValues"] = {}
        used_vlans = {v["id"] for v in sw["vlans"]}
        # Allocate from the "type-1" interface band (2000-2251).
        free_vlans = (v for v in range(2000, 2252) if v not in used_vlans)
        for name, peer in pairs.items():
            port = by_name.get(name)
            if port is None:
                port = cls._synthesize_port(base_json, port_map, name, next(free_vlans))
            port["expectedLLDPValues"] = {cls._LLDP_PORT_TAG: peer}
            # Use the lower speed if there is a speed mismatch. This might not always work.
            if peer in by_name and port["speed"] > by_name[peer]["speed"]:
                port["speed"] = by_name[peer]["speed"]
                port["profileID"] = by_name[peer]["profileID"]
        return base_json

    def _stage_qsfp_config(self):
        # The agent doesn't publish port status to FSDB in time, so a qsfp_service
        # that subscribes to FSDB never sees a transceiver reach ACTIVE. Disable
        # the subscription so qsfp polls getPortStatus() directly.
        with tempfile.NamedTemporaryFile(suffix=".conf", delete=False) as f:
            local_path = f.name
        try:
            exit_status, output = self.scp_client.get_file(
                self._SYSTEM_QSFP_CONFIG_PATH, local_path
            )
            if exit_status != 0:
                raise RuntimeError(f"Failed to fetch system qsfp config: {output}")
            with open(local_path, encoding="utf-8") as f:
                qsfp = json.load(f)
            qsfp.setdefault("defaultCommandLineArgs", {})[
                "subscribe_to_state_from_fsdb"
            ] = "false"
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(qsfp, f)
            exit_status, output = self.scp_client.put_file(
                local_path, self._REMOTE_QSFP_CONFIG_PATH
            )
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            raise RuntimeError(f"Failed to upload generated qsfp config: {output}")
        self._use_generated_qsfp = True

    def pre_test(self):
        super().pre_test()

        model = _normalize_model(self.tc["model"])
        self._stage_qsfp_config()

        # Set by the nhtest executor to a {port: peer_port} JSON file when cabling
        # was generated from netbox; absent for standalone dev runs.
        cabling_path = os.getenv(self._CABLING_ENV_VAR)
        if not cabling_path:
            return

        config_name = self._config_name(model)

        with open(self._base_config_path(config_name), encoding="utf-8") as f:
            base = json.load(f)
        with open(cabling_path, encoding="utf-8") as f:
            pairs = json.load(f)

        # Ports netbox reports that the base config doesn't already have are the
        # only ones we need to synthesize, and the only reason to load the
        # platform mapping. Skipping the load otherwise.
        base_names = {port["name"] for port in base["sw"]["ports"]}
        ports_to_synthesize = pairs.keys() - base_names
        port_map = (
            self._load_platform_mapping(config_name) if ports_to_synthesize else {}
        )
        config = self._overlay_cabling(base, pairs, port_map)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".materialized_JSON", delete=False
        ) as f:
            json.dump(config, f)
            local_path = f.name
        try:
            exit_status, output = self.scp_client.put_file(
                local_path, self._REMOTE_CONFIG_PATH
            )
        finally:
            os.unlink(local_path)
        if exit_status != 0:
            raise RuntimeError(f"Failed to upload generated link config: {output}")
        self._use_generated_config = True

    def test_args(self, model: str) -> str:
        if self._use_generated_config:
            config_arg = self._REMOTE_CONFIG_PATH
        else:
            config_arg = f"./share/link_test_configs/{self._config_name(model)}.materialized_JSON"
        qsfp_arg = (
            self._REMOTE_QSFP_CONFIG_PATH
            if self._use_generated_qsfp
            else self._SYSTEM_QSFP_CONFIG_PATH
        )
        args = (
            "link --agent-run-mode mono "
            f"--config {config_arg} "
            f"--qsfp-config {qsfp_arg}"
        )
        if model == "wedge800cact":
            # warmboot acting strange, will readd once fixed
            args += " --coldboot_only"
        return args

    def post_test(self):
        # The link gtest stops production qsfp_service / fsdb (via the
        # internal cleanup_*_service helpers) but never restarts them.
        self.ssh_client.run_cmd("sudo systemctl start fsdb qsfp_service")


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

    def test_args(self, model: str) -> str:
        return f"platform --type {self.test_type}"

class BspTestRunner(BaseHwTestRunner):
    """Runner for BSP hardware tests. Delegates to run_test.py bsp.

    All service lifecycle management (fan_service, qsfp_service, led_service
    stop/start, platform_manager restart, /run/devmap wait) and the
    --enable_stress_tests flag are handled on-DUT by run_test.py bsp.
    """

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

class SmokeTestRunner(BaseHwTestRunner):
    """Runner for the FBOSS agent smoke test.

    Unlike the gtest-based runners above, this one invokes
    ``agent_smoke.py`` directly on the DUT — no filter file, no
    ``run_test.py`` indirection — and consumes the JUnit XML it produces
    at ``self.testresult_filepath``.
    """

    AGENT_SMOKE_PATH = "/opt/fboss/bin/python_tests/agent_smoke.py"

    def test_args(self, model: str) -> str:
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

    @_enforce_min_failure_duration
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


class BenchmarkTestRunner(BaseHwTestRunner):
    """Runner for benchmark tests."""

    def test_args(self, model: str) -> str:
        config_name = _HW_TEST_CONFIG_NAME.get(model, model)
        logger.info("model=%s hw_test_config=%s", model, config_name)
        return f"benchmark --config ./share/hw_test_configs/{config_name}.agent.materialized_JSON{_benchmark_skip_known_bad(model)}"

    def set_filters(self, src_filepath, dst_filepath):
        """Benchmarks run every registered case — no filter file needed.

        run_test.py's benchmark sub-command treats a missing --filter_file as
        "run all" and prunes known-bad/unsupported cases from sai_bench config;
        an empty filter file would instead select zero benchmarks.
        """
        return True

    def build_test_cmd(self, model: str) -> str:
        # Omit --filter_file so run_test.py runs all benchmarks (see set_filters).
        return (
            f"sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && "
            f" ./bin/run_test.py {self.test_args(model)} "
            f"' > {self.testlog_filepath} 2>&1"
        )

    # Benchmark binaries spin up their own agent (binds thrift port 5909, owns
    # the ASIC), so the production agents must be down first or the bind aborts
    # (Address already in use) and the ASIC contends (SIGBUS/SIGSEGV). run_test.py
    # stops these for the gtest runners but not for the benchmark sub-command.
    BENCHMARK_DISABLE_SERVICES = ["fboss_sw_agent", "fboss_hw_agent@0"]

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
            r"Benchmark results written to: (benchmark_results_\S+\.csv)",
            content
        )
        if match:
            return match.group(1)

        logger.warning(f"Could not find benchmark results CSV filename in {local_log_path}")
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

    def _generate_tr_xml_from_csv(self,
                                  csv_path: str,
                                  xml_path: str,
                                  csv_timestamp: str,
                                  skipped_count: int=0
                                 ) -> bool:
        """
        Convert a benchmark CSV into a minimal JUnit-style tr.xml.

        Args:
            csv_path: Path to benchmark_results_*.csv
            xml_path: Output XML path (e.g. /tmp/tr.xml)
            timestamp: timestamp on the original CSV

        Returns:
            bool: if tr.xml creation was successful
        """

        # Convert original CSV timestamp to correct format
        suite_timestamp = datetime.strptime(csv_timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        # Create XML tree
        testsuites_el = ET.Element("testsuites")
        testsuite_el = ET.SubElement(
            testsuites_el,
            "testsuite",
            {
                "tests": "0",                   # filled later
                "failures": "0",                # filled later
                "disabled": "0",                # cannot be inferred from CSV
                "errors": "0",                  # cannot be inferred from CSV
                "skipped": str(skipped_count),
                "time": "0.000",                # filled later
                "timestamp": suite_timestamp,
                "name": "AllTests",
            },
        )

        # Calculate stats that require row-by-row inspection
        total_failures = 0
        total_time_sec = 0.0

        with open(csv_path, mode="r") as f:
            rows = list(csv.DictReader(f))

        logger.info("Parsing CSV file...")

        for row in rows:
            # Benchmark names aren't structured as ClassName.testName
            name = row.get("benchmark_test_name")
            classname = "Benchmarks"
            # No obvious way to get the actual source file name;
            # using compiled binary as placeholder
            filename = row.get("benchmark_binary_name")

            # Benchmark time is in picoseconds; convert to seconds
            benchmark_time_ps = row.get("benchmark_time_ps", "")
            try:
                case_time_sec = max(float(benchmark_time_ps) / 1e12, 0.0) if benchmark_time_ps else 0.0
            except (TypeError, ValueError):
                case_time_sec = 0.0
            total_time_sec += case_time_sec

            # Get benchmark results
            test_status = (row.get("test_status") or "").upper()
            threshold_status = (row.get("threshold_status") or "").upper()
            threshold_details = row.get("threshold_details") or ""

            # Add testcase element
            testcase_el = ET.SubElement(
                testsuite_el,
                "testcase",
                {
                    "name": name,
                    "file": filename,
                    "line": "",
                    "status": "run",
                    "result": "timed-out" if (test_status == "TIMEOUT") else "completed",
                    "time": f"{case_time_sec:.6f}",
                    "timestamp": suite_timestamp,   # Per-test timestamp not in CSV
                    "classname": classname,
                },
            )

            # Add failure subelement if appropriate
            failure_reasons = []

            if test_status == "FAILED":
                failure_reasons.append("test_status=FAILED")
            elif test_status == "TIMEOUT":
                failure_reasons.append("test_status=TIMEOUT")

            if threshold_status == "EXCEEDED":
                if threshold_details:
                    failure_reasons.append(f"threshold exceeded: {threshold_details}")
                else:
                    failure_reasons.append("threshold exceeded")

            if failure_reasons:
                total_failures += 1
                message = "; ".join(failure_reasons)

                failure_el = ET.SubElement(
                    testcase_el,
                    "failure",
                    {"message": message},
                )

        total_tests = len(rows) + skipped_count

        testsuite_el.set("tests", str(total_tests))
        testsuite_el.set("failures", str(total_failures))
        testsuite_el.set("time", f"{total_time_sec:.6f}")

        logger.info("Successfully parsed CSV --> writing results to xml file")

        tree = ET.ElementTree(testsuites_el)
        ET.indent(tree, space=" ", level=0)
        tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
        return True

    @_enforce_min_failure_duration
    def run_test(self, test_context: dict) -> bool:
        """
        Run the benchmark test on the DUT.
        This acts as a wrapper around the base class implementation of
        run_test and adds additional functionality for generating
        a tr.xml based on a benchmark_result.csv, as benchmarks
        do not produce a tr.xml automatically.
        """
        success = super().run_test(test_context, skip_tr_xml=True)
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
        csv_timestamp = csv_filename.replace("benchmark_results_", "").replace(".csv", "")
        skipped_count = self._get_skipped_bm_count("/tmp/test.log")

        logger.info("Generating /tmp/tr.xml from %s", local_csv_path)
        success = self._generate_tr_xml_from_csv(local_csv_path, "/tmp/tr.xml", csv_timestamp, skipped_count)
        if not success:
            logger.error("Failed to generate /tmp/tr.xml from %s", local_csv_path)
            return False

        self.normalize_test_results_file()

        return True
