"""QSFP and LED-service hardware test runners."""

import copy
import logging
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.cabling import CablingAwareRunnerMixin, neighbor_pairs
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_SHARE
from tests.libs.test_runner.platform_configs import LINK_QSFP_TEST_CONFIG_NAME
from tests.libs.test_runner.platform_mapping import media_speed_mbps, PortInfo
from tests.libs.test_runner.variants import (
    cage_of,
    CageResolution,
    resolve_cage,
    resolve_pairs,
    Variant,
)

logger = logging.getLogger("test_runner")


class QsfpTestRunner(CablingAwareRunnerMixin, BaseHwTestRunner):
    """Runner for QSFP hardware tests."""

    _VARIANT_SUMMARY_PREFIX = "QSFP TEST"

    STACK = STACK_FORWARDING
    BINARIES = ("bin/qsfp_hw_test",)
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    _BASE_CONFIG_DIR = Path("fboss/oss/qsfp_test_configs")
    _REMOTE_CONFIG_PATH = "/home/netops/qsfp_test.materialized_JSON"
    _FALLBACK_PROFILE_ID = 38

    # These hard-assert a non-empty optical/active transceiver set.
    _OPTICS_ONLY_FILTER_SUBSTRINGS = (
        "i2cStressWrite",
        "i2cLogCapacityWrite",
        "cmisPageChange",
        "verifyResetControl",
    )

    # These abort on modules whose self-reporting no profile can satisfy
    # (e.g. loopback plugs); see _strict_unverifiable_reason().
    _MEDIA_STRICT_FILTER_SUBSTRINGS = (
        "CheckPortsProgrammed",
        "CheckTransceiverRemoved",
        "CheckAgentConfigChanged",
        # Expects stateChanged == (transmitterTech != COPPER) on passive
        # cables; fails on modules reporting UNKNOWN transmitter technology.
        "resetTranscieverAndDetectStateChanged",
    )

    # Passive DACs do not support 200G serdes, so limit them to 100G lane speeds.
    _PASSIVE_CU_MAX_LANE_SPEED_MBPS = 106_250

    # Copper profiles HwTransceiverUtils::verifyPortNameToLaneMap handles on a
    # CR8_800G module; others throw "Unhandled profile" (other media never do).
    _LANE_MAP_GATED_MEDIA = "CR8_800G"
    _VERIFIABLE_COPPER_LANE_MAP_PROFILES = frozenset({45, 50, 60})

    def _medium_profile(self, port: str, info: PortInfo) -> int | None:
        max_lane_speed = (
            self._PASSIVE_CU_MAX_LANE_SPEED_MBPS
            if self._media_tech_by_port.get(port) == "PASSIVE_CU"
            else None
        )
        return info.profile_for_medium(
            self._is_copper_by_port.get(port),
            media_speed_mbps(self._media_by_port.get(port)),
            max_lane_speed,
            self._host_apps_by_port.get(port),
        )

    def _port_profile_id(self, port: str, port_map: dict) -> int:
        """Medium- and speed-aware pick, falling back to max speed when no
        profile matches the medium."""
        info = port_map.get(port)
        if not info:
            return self._FALLBACK_PROFILE_ID
        profile_id = self._medium_profile(port, info)
        return profile_id if profile_id is not None else info.profile_id

    def _strict_unverifiable_reason(self, port: str, port_map: dict) -> str | None:
        """Why the media-strict verifiers cannot pass on this port, or None."""
        info = port_map.get(port)
        if not info:
            return "port is not in the platform mapping"
        is_copper = self._is_copper_by_port.get(port)
        if is_copper is None:
            return "module reports no usable medium information"
        profile_id = self._medium_profile(port, info)
        if profile_id is None:
            return "copper cable but the platform mapping offers no copper profile"
        media = self._media_by_port.get(port)
        media_speed = media_speed_mbps(media)
        if media_speed is not None and media_speed != info.profiles[profile_id]:
            return (
                f"module media {media} ({media_speed} Mbps) does not match "
                f"selected profile {profile_id} ({info.profiles[profile_id]} Mbps)"
            )
        if is_copper and self._transmitter_tech_by_port.get(port) == "UNKNOWN":
            return "copper profile selected but module reports UNKNOWN transmitter technology"
        return None

    def _resolve_cages(
        self, config_name: str, variant: Variant, ports: list[str]
    ) -> dict[str, CageResolution]:
        cages = self._full_platform_mapping(config_name)
        return {
            cage_of(p): resolve_cage(
                p,
                variant,
                cages,
                self._host_speeds_by_port,
                self._is_copper_by_port,
                self._host_apps_by_port,
            )
            for p in ports
        }

    def _variant_lane_map_gap(self, config_name: str, ports: list[str]) -> dict[str, int]:
        """{port: variant profile} the hw test cannot lane-map; empty at max."""
        if not self._is_variant_run():
            return {}
        gated = [
            p
            for p in ports
            if self._media_tech_by_port.get(p) == "PASSIVE_CU"
            and self._media_by_port.get(p) == self._LANE_MAP_GATED_MEDIA
        ]
        if not gated:
            return {}
        variant = self._requested_variant(config_name)
        # Cages of an excluded pair stay at max in _build_cabled_config.
        excluded = resolve_pairs(
            self._pass_pairs(ports),
            variant,
            self._full_platform_mapping(config_name),
            self._host_speeds_by_port,
            self._is_copper_by_port,
            self._host_apps_by_port,
        ).excluded_pairs
        excluded_cages = {cage_of(p) for p in excluded}
        gated = [p for p in gated if cage_of(p) not in excluded_cages]
        if not gated:
            return {}
        cages = self._resolve_cages(config_name, variant, gated)
        return {
            p: cage.profile_id
            for p in gated
            if (cage := cages[cage_of(p)]).ok
            and cage.profile_id not in self._VERIFIABLE_COPPER_LANE_MAP_PROFILES
        }

    def _strict_eligible_ports(self, model: str, ports: list[str]) -> list[str]:
        config_name = LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        _, port_map = self._load_base_config_and_port_map(self._BASE_CONFIG_DIR, config_name)
        lane_map_gap = self._variant_lane_map_gap(config_name, ports)
        eligible = []
        for port in ports:
            reason = self._strict_unverifiable_reason(port, port_map)
            if reason is None and port in lane_map_gap:
                reason = f"qsfp hw test has no lane-map rule for copper profile {lane_map_gap[port]}"
            if reason is None:
                eligible.append(port)
            else:
                logger.warning("Excluding %s from the media-strict pass: %s", port, reason)
        return eligible

    def _pair_profile_id(self, a_port: str, z_port: str, port_map: dict) -> int:
        # Both ends of a pair get the same profile (HwPortUtils::getCabledPortsAndProfiles),
        # so pick the narrower end rather than risk asking for more than one side supports.
        if not port_map.get(a_port) or not port_map.get(z_port):
            return self._FALLBACK_PROFILE_ID
        narrow_port = min((a_port, z_port), key=lambda p: port_map[p].speed)
        return self._port_profile_id(narrow_port, port_map)

    def _build_cabled_config(
        self,
        base_config: dict,
        ports: list[str],
        port_map: dict,
        pairs: dict,
        resolution=None,
        variant_cages: Mapping[str, CageResolution] = MappingProxyType({}),
    ) -> dict:
        config = copy.deepcopy(base_config)
        cabled = []
        # Self-pairs carry the variant per cage, not per cable: the qsfp tests are
        # per transceiver and HwPortUtils builds its cabled set per PortID. Cages
        # of an excluded pair stay at max to agree with their neighbor entry.
        excluded_cages = (
            {cage_of(p) for p in resolution.excluded_pairs} if resolution is not None else set()
        )
        emitted = set()
        for port in ports:
            cages = {} if cage_of(port) in excluded_cages else variant_cages
            for name, profile_id in self._self_pair_ports(port, port_map, cages):
                if name in emitted:
                    continue
                emitted.add(name)
                cabled.append({"aPortName": name, "zPortName": name, "profileID": profile_id})
        # Appended after every self-pair, on purpose: the hw test's neighbor map is
        # keyed by transceiver id and last-write-wins, so a real pair must come after
        # that transceiver's self-pair to actually take effect.
        if resolution is None:
            neighbors = neighbor_pairs(ports, pairs)
            for a, z in neighbors:
                cabled.append({"aPortName": a, "zPortName": z, "profileID": self._pair_profile_id(a, z, port_map)})
        else:
            # One entry per active subport with the variant profile.
            # getCabledPortsAndProfiles honors these per PortID (HwPortUtils.cpp);
            # only the transceiver-keyed neighbor map collapses them, harmless
            # since a cage's subports share one peer transceiver.
            cages_in_pass = {cage_of(p) for p in ports}
            neighbors = []
            for a in sorted(resolution.expanded_pairs):
                z = resolution.expanded_pairs[a]
                if a > z:
                    continue
                if cage_of(a) not in cages_in_pass or cage_of(z) not in cages_in_pass:
                    continue
                neighbors.append((a, z))
                cabled.append(
                    {"aPortName": a, "zPortName": z, "profileID": resolution.profile_overrides[a]}
                )
            # Excluded pairs are still cabled: HwI2cSelectTest's duplicate-serial
            # check needs both DAC ends to name each other.
            for a in sorted(resolution.excluded_pairs):
                z = resolution.excluded_pairs[a]
                if a > z:
                    continue
                if cage_of(a) not in cages_in_pass or cage_of(z) not in cages_in_pass:
                    continue
                neighbors.append((a, z))
                cabled.append(
                    {"aPortName": a, "zPortName": z, "profileID": self._pair_profile_id(a, z, port_map)}
                )
        config["qsfpTestConfig"]["cabledPortPairs"] = cabled
        logger.info("qsfp cabled pairs: %d neighbor pairs added for %d ports", len(neighbors), len(ports))
        # Skip discovery-time firmware upgrade: fails when fboss_firmware.yaml is missing.
        args = config.setdefault("defaultCommandLineArgs", {})
        args["firmware_upgrade_on_coldboot"] = "false"
        args["firmware_upgrade_on_tcvr_insert"] = "false"
        return config

    def _self_pair_ports(
        self, port: str, port_map: dict, variant_cages: Mapping[str, CageResolution]
    ) -> list[tuple[str, int]]:
        """(port name, profile) per self-pair: the cage's active subports at the
        variant profile when this cage alone can run it, else the port as-is."""
        cage = variant_cages.get(cage_of(port))
        if cage is not None and cage.ok:
            return [(f"{cage_of(port)}/{sub}", cage.profile_id) for sub in cage.subports]
        return [(port, self._port_profile_id(port, port_map))]

    def _prepare_pass(self, model: str, ports: list[str]) -> None:
        config_name = self._config_name(model)
        base_config, port_map = self._load_base_config_and_port_map(self._BASE_CONFIG_DIR, config_name)
        resolution = self._pass_variant_resolution
        variant_cages = {}
        if resolution is not None:
            variant_cages = self._resolve_cages(config_name, resolution.variant, ports)
        config = self._build_cabled_config(
            base_config, ports, port_map, self._load_snake_pairs(), resolution, variant_cages
        )
        self._upload_generated_config(config)

    def test_args(self, model: str) -> str:
        if self._use_generated_config:
            return f"qsfp --qsfp-config {self._REMOTE_CONFIG_PATH}"
        config_name = LINK_QSFP_TEST_CONFIG_NAME.get(model, model)
        config_arg = self._variantized_config_arg(
            f"./share/qsfp_test_configs/{config_name}.materialized_JSON",
            "/home/netops/variant_qsfp_test.materialized_JSON",
        )
        return f"qsfp --qsfp-config {config_arg}"


class LedTestRunner(BaseHwTestRunner):
    """Runner for LED service hardware tests.

    led_service_hw_test ships in the forwarding tarball. It reads its platform
    from /etc/coop/led.conf on the DUT, so no --config is passed — run_test.py
    led just runs the binary against the wrapper's filter file. Only the binary
    is sliced; the runner needs none of the forwarding share/ configs.
    """

    def test_args(self, model: str) -> str:  # noqa: ARG002
        return "led"
    STACK = STACK_FORWARDING
    BINARIES = ("bin/led_service_hw_test",)
    REQUIRED_PATHS = BINARIES
