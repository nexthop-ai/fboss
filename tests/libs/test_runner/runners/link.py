"""Link test runner, including per-DUT link test config synthesis from the
platform mapping and netbox cabling.
"""

import copy
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

from tests.libs.test_runner.base import BaseHwTestRunner, normalize_model
from tests.libs.test_runner.cabling import CablingAwareRunnerMixin
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_SHARE
from tests.libs.test_runner.platform_mapping import load_platform_mapping, PortInfo

logger = logging.getLogger("test_runner")


class _PortTemplate(NamedTuple):
    port: dict
    vlan: dict
    vlan_port: dict
    interface: dict


class LinkTestRunner(CablingAwareRunnerMixin, BaseHwTestRunner):
    """Runner for link tests."""

    # A passive DAC cannot carry 200G/lane, so a breakout variant that asks for
    # it will never link. Exclude those cages rather than report a dead link.
    _VARIANT_PASSIVE_CU_MAX_LANE_SPEED_MBPS = 106_250

    _VARIANT_SUMMARY_PREFIX = "LINK TEST"

    # Must stay in step with the PRBS_*_TEST instantiations in AgentEnsemblePrbsTest.cpp.
    _MEDIA_INTERFACE_TOKENS = (
        "FR1_100G",
        "FR4_200G",
        "FR4_400G",
        "DR4_400G",
        "CR4_400G",
        "CR8_800G",
        "FR8_800G",
        "DR4_800G",
    )

    # These hard-assert a non-empty optical/active transceiver set. CR codes belong
    # here too: the PRBS pair source drops passive copper before checkValidMedia runs.
    _OPTICS_ONLY_FILTER_SUBSTRINGS = (
        "verifyTxRxLatches",
        "opticsTxDisableRandomPorts",
        "opticsTxDisableEnable",
        "opticsVdmPerformanceMonitoring",
        *_MEDIA_INTERFACE_TOKENS,
    )

    # TCVR_L-to-TCVR_L programs PRBS on both ends of a pair; ASIC-to-TCVR_S only on
    # the one port it tests. Matched against the generated class names.
    _BOTH_ENDS_TOKEN = "TCVR_L"

    # Must stay in step with kNumPort in AgentEnsemblePtpTests.cpp: these tests
    # flap the first 5 cabled ports (by port id) and need one snake pair
    # untouched by the flap to keep the PTP loop routable.
    _PTP_FLAP_TEST_SUBSTRINGS = ("enablePtpPortDown", "verifyPtpTcAfterLinkFlap")
    _PTP_FLAPPED_PORT_COUNT = 5

    _BASE_CONFIG_DIR = Path("fboss/oss/link_test_configs")
    _REMOTE_CONFIG_PATH = "/home/netops/link_test_config.materialized_JSON"
    _SYSTEM_QSFP_CONFIG_PATH = "/etc/coop/qsfp.conf"
    _REMOTE_QSFP_CONFIG_PATH = "/home/netops/link_test_qsfp.conf"
    # JSON map key for LLDPTag.PORT: see fboss/agent/switch_config.thrift.
    _LLDP_PORT_TAG = "2"
    _DEFAULT_ECMP_WIDTH = 64

    STACK = STACK_FORWARDING
    # Both binaries ship: --agent-run-mode picks mono vs multi at run time.
    BINARIES = ("bin/sai_mono_link_test-sai_impl", "bin/sai_multi_link_test-sai_impl")
    REQUIRED_PATHS = (*BINARIES, *STACK_SHARE[STACK])

    def __init__(self):
        super().__init__()
        self._use_generated_qsfp = False
        self._pass_ports: list[str] | None = None

    def _prepare_pass(self, model: str, ports: list[str]) -> None:  # noqa: ARG002
        self._pass_ports = ports

    @classmethod
    def _media_token_in(cls, pattern: str) -> str | None:
        return next((token for token in cls._MEDIA_INTERFACE_TOKENS if token in pattern), None)

    @classmethod
    def _media_cabled(
        cls, pattern: str, media: str, media_by_port: dict[str, str | None], pairs: dict[str, str]
    ) -> bool:
        if not pairs:
            # No pairs to check ends against; fall back to "cabled anywhere".
            return media in media_by_port.values()
        if cls._BOTH_ENDS_TOKEN in pattern:
            return any(
                media_by_port.get(port) == media and media_by_port.get(peer) == media
                for port, peer in pairs.items()
            )
        return any(media_by_port.get(port) == media for port in pairs)

    def _port_sort_key(self, port_name: str):
        """Order ports the way the flat_set<PortDescriptor> in the tests does:
        by platform-mapping port id, falling back to the numeric fields of the
        name when the mapping is unavailable."""
        if self._cached_port_map is None:
            try:
                model = normalize_model(self.tc["model"])
                self._cached_port_map = load_platform_mapping(self._config_name(model))
            except (OSError, KeyError, ValueError):
                self._cached_port_map = {}
        info = self._cached_port_map.get(port_name)
        if info is not None:
            return (0, info.logical_id)
        return (1, tuple(int(n) for n in re.findall(r"\d+", port_name)))

    def _ptp_flap_pair_survives(self, pass_ports: list[str]) -> bool:
        """The PTP flap tests flap the first _PTP_FLAPPED_PORT_COUNT cabled
        ports, purging their ECMP next hops; the loop only survives if a snake
        pair sits fully outside that set. No snake-pairs data: don't gate."""
        allowed = set(pass_ports)
        # Only ports of a pair with both ends present are cabled in the
        # generated config (see pre_test); the rest never come up.
        pairs = {
            port: peer
            for port, peer in self._load_snake_pairs().items()
            if port in allowed and peer in allowed
        }
        if not pairs:
            return True
        cabled = set(pairs) | set(pairs.values())
        flapped = set(sorted(cabled, key=self._port_sort_key)[: self._PTP_FLAPPED_PORT_COUNT])
        return any(
            port not in flapped and peer not in flapped for port, peer in pairs.items()
        )

    def _gate_filters(
        self, patterns: list[str], media_by_port: dict[str, str | None], optics_ports: list[str]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Keep only patterns whose referenced media is actually cabled on this DUT.

        PRBS patterns naming no media are gated too: they would expand to every
        media-templated class, including ones with no ports, and abort the binary.

        PTP flap patterns are gated on a snake pair surviving the flap.
        """
        ptp_flap_ok = self._ptp_flap_pair_survives(list(media_by_port))
        optical = set(optics_ports)
        eligible = {p: m for p, m in media_by_port.items() if p in optical}
        pairs = {p: peer for p, peer in self._load_snake_pairs().items() if p in eligible and peer in eligible}
        # qsfp_service reports the media code of the application a module runs,
        # so at a breakout speed no port matches the full-speed media classes.
        is_variant = self._is_variant_run()
        kept, skipped = [], []
        for pattern in patterns:
            if is_variant and "Prbs" in pattern:
                skipped.append(
                    (pattern, "PRBS classes match full-speed media codes only; not run on breakout variants")
                )
                continue
            if any(s in pattern for s in self._PTP_FLAP_TEST_SUBSTRINGS):
                if ptp_flap_ok:
                    kept.append(pattern)
                else:
                    reason = (
                        f"no snake pair outside the first {self._PTP_FLAPPED_PORT_COUNT} "
                        "flapped ports; PTP loop unroutable after flap"
                    )
                    logger.warning("Skipping %s: %s", pattern, reason)
                    skipped.append((pattern, reason))
                continue
            media = self._media_token_in(pattern)
            if media is None and "Prbs" not in pattern:
                kept.append(pattern)
            elif media is None:
                # Must precede the no-optics case: such a pattern is copper-safe, so
                # it would otherwise reach the main pass and abort the binary there.
                skipped.append((pattern, "PRBS filter names no media interface"))
            elif not eligible:
                # No optical/active ports at all; the optics-pass check reports that.
                kept.append(pattern)
            elif not any(eligible.values()):
                skipped.append((pattern, "port media interface unavailable"))
            elif self._media_cabled(pattern, media, eligible, pairs):
                kept.append(pattern)
            else:
                skipped.append((pattern, f"no {media} optics cabled on this DUT"))
        return kept, skipped

    @classmethod
    def _synthesize_port(
        cls,
        base_json: dict,
        port_map: dict[str, PortInfo],
        name: str,
        vlan_id: int,
        template: _PortTemplate,
        profile_id: int | None = None,
        voq_intf_id: int | None = None,
    ) -> dict:
        info = port_map.get(name)
        if info is None:
            raise ValueError(f"netbox port {name} is not in the platform mapping")
        if profile_id is not None and profile_id not in info.profiles:
            raise ValueError(f"port {name} does not support profile {profile_id}")
        sw = base_json["sw"]
        # The agent requires every port to own exactly one interface, so a synthesized
        # port needs a matching vlan, vlanPort and interface too. On a VOQ switch the
        # interface is the port's system-port RIF instead and vlan_id only indexes its IPs.
        port = copy.deepcopy(template.port)
        port.update(
            {
                "logicalID": info.logical_id,
                "name": name,
                "state": 2,
                "speed": info.speed if profile_id is None else info.profiles[profile_id],
                "profileID": info.profile_id if profile_id is None else profile_id,
                "ingressVlan": vlan_id if voq_intf_id is None else 0,
                "portType": 0,
                "expectedLLDPValues": {},
            }
        )
        intf = copy.deepcopy(template.interface)
        # Synthesized, not inherited from the base config: the fboss ECMP helper
        # skips IP-less interfaces, silently dropping the port from L3 tests.
        intf.update(
            {
                "intfID": vlan_id if voq_intf_id is None else voq_intf_id,
                "vlanID": vlan_id if voq_intf_id is None else 0,
                "ipAddresses": [
                    f"2600:0:0:{vlan_id:x}::/64",
                    f"100.{64 + (vlan_id >> 8)}.{vlan_id & 0xFF}.0/24",
                ],
            }
        )
        sw["ports"].append(port)
        if voq_intf_id is None:
            vlan = copy.deepcopy(template.vlan)
            vlan.update({"id": vlan_id, "intfID": vlan_id, "name": f"vlan{vlan_id}"})
            vlan_port = copy.deepcopy(template.vlan_port)
            vlan_port.update({"vlanID": vlan_id, "logicalPort": info.logical_id})
            sw["vlans"].append(vlan)
            sw["vlanPorts"].append(vlan_port)
        sw["interfaces"].append(intf)
        return port

    @staticmethod
    def _voq_intf_offsets(sw: dict) -> list[tuple[int, int, int]] | None:
        """(min port id, max port id, system port offset) per switch, or None if not VOQ."""
        settings = sw.get("switchSettings", {})
        # cfg::SwitchType::VOQ
        if settings.get("switchType") != 2:
            return None
        return [
            (
                info["portIdRange"]["minimum"],
                info["portIdRange"]["maximum"],
                info["localSystemPortOffset"],
            )
            for info in settings["switchIdToSwitchInfo"].values()
        ]

    @staticmethod
    def _voq_intf_id(offsets: list[tuple[int, int, int]], logical_id: int) -> int:
        for low, high, offset in offsets:
            if low <= logical_id <= high:
                return offset + logical_id
        raise ValueError(f"port {logical_id} is outside every switch's port id range")

    @classmethod
    def _overlay_cabling(
        cls,
        base_json: dict,
        pairs: dict[str, str],
        port_map: dict[str, PortInfo],
        profile_overrides: dict[str, int] | None = None,
    ) -> dict:
        if not pairs:
            raise ValueError("refusing to generate link test config: no cabling pairs")
        sw = base_json["sw"]
        voq_offsets = cls._voq_intf_offsets(sw)
        if voq_offsets is not None:
            return cls._overlay_cabling_voq(
                base_json, pairs, port_map, profile_overrides, voq_offsets
            )
        template_vlan_id = sw["ports"][0]["ingressVlan"]
        template = _PortTemplate(
            port=sw["ports"][0],
            vlan=next(v for v in sw["vlans"] if v["id"] == template_vlan_id),
            vlan_port=next(p for p in sw["vlanPorts"] if p["vlanID"] == template_vlan_id),
            interface=next(i for i in sw["interfaces"] if i.get("vlanID") == template_vlan_id),
        )
        # Re-synthesize all front-panel ports from the platform mapping and
        # netbox cabling; the base config contributes only non-port scaffolding
        # and non-front-panel ports (mgmt, fabric/recycle).
        sw["ports"] = [p for p in sw["ports"] if p["portType"] != 0]
        kept_vlans = {p["ingressVlan"] for p in sw["ports"]} | {sw.get("defaultVlan")}
        sw["vlans"] = [v for v in sw["vlans"] if v["id"] in kept_vlans]
        sw["vlanPorts"] = [vp for vp in sw["vlanPorts"] if vp["vlanID"] in kept_vlans]
        sw["interfaces"] = [
            i for i in sw["interfaces"] if "vlanID" not in i or i["vlanID"] in kept_vlans
        ]
        for port in sw["ports"]:
            port["expectedLLDPValues"] = {}
        used_vlans = {v["id"] for v in sw["vlans"]} | {sw.get("defaultVlan")}
        # "Type-1" interface band; wider than the historical 2000-2251 so
        # full 8-way breakout fits, capped below 4094.
        free_vlans = (v for v in range(2000, 4094) if v not in used_vlans)
        return cls._synthesize_cabled_ports(
            base_json, pairs, port_map, profile_overrides, template, free_vlans
        )

    @classmethod
    def _overlay_cabling_voq(
        cls,
        base_json: dict,
        pairs: dict[str, str],
        port_map: dict[str, PortInfo],
        profile_overrides: dict[str, int] | None,
        voq_offsets: list[tuple[int, int, int]],
    ) -> dict:
        sw = base_json["sw"]
        template_port = next(p for p in sw["ports"] if p["portType"] == 0)
        template_intf_id = cls._voq_intf_id(voq_offsets, template_port["logicalID"])
        template = _PortTemplate(
            port=template_port,
            vlan={},
            vlan_port={},
            interface=next(i for i in sw["interfaces"] if i["intfID"] == template_intf_id),
        )
        # Front-panel ports and their system-port interfaces are re-synthesized as
        # on NPU; recycle, CPU and mgmt ports keep theirs.
        dropped = {
            cls._voq_intf_id(voq_offsets, p["logicalID"])
            for p in sw["ports"]
            if p["portType"] == 0
        }
        sw["ports"] = [p for p in sw["ports"] if p["portType"] != 0]
        sw["interfaces"] = [i for i in sw["interfaces"] if i["intfID"] not in dropped]
        for port in sw["ports"]:
            port["expectedLLDPValues"] = {}
        # Only indexes the synthesized IPs; the same band as NPU keeps addresses alike.
        free_ids = iter(range(2000, 4094))
        return cls._synthesize_cabled_ports(
            base_json, pairs, port_map, profile_overrides, template, free_ids, voq_offsets
        )

    @classmethod
    def _synthesize_cabled_ports(
        cls,
        base_json: dict,
        pairs: dict[str, str],
        port_map: dict[str, PortInfo],
        profile_overrides: dict[str, int] | None,
        template: _PortTemplate,
        free_vlans,
        voq_offsets: list[tuple[int, int, int]] | None = None,
    ) -> dict:
        sw = base_json["sw"]

        def intf_id(name):
            if voq_offsets is None or name not in port_map:
                return None
            return cls._voq_intf_id(voq_offsets, port_map[name].logical_id)

        overrides = profile_overrides or {}
        try:
            for name, peer in pairs.items():
                port = cls._synthesize_port(
                    base_json,
                    port_map,
                    name,
                    next(free_vlans),
                    template,
                    overrides.get(name),
                    intf_id(name),
                )
                port["expectedLLDPValues"] = {cls._LLDP_PORT_TAG: peer}
            # The SDK exposes SAI port objects for every cage's default port
            # regardless of config, and warmboot aborts on port objects the
            # config doesn't claim. Cover every cage without a cabled pair
            # with its controlling port, disabled so it never links up.
            cabled_cages = {name.rsplit("/", 1)[0] for name in pairs}
            kept_names = {p["name"] for p in sw["ports"]}
            for name in sorted(port_map):
                if (
                    not name.startswith("eth")
                    or not name.endswith("/1")
                    or name.rsplit("/", 1)[0] in cabled_cages
                    or name in kept_names
                ):
                    continue
                port = cls._synthesize_port(
                    base_json, port_map, name, next(free_vlans), template, None, intf_id(name)
                )
                port["state"] = 1
        except StopIteration:
            raise ValueError(
                "ran out of vlans in the 2000-4093 band while synthesizing ports"
            ) from None
        # One ECMP group must span every cabled port; SAI sizes it from the
        # ecmp_width flag, the applied config from switchSettings.ecmpWidth.
        args = base_json.get("defaultCommandLineArgs", {})
        width = max(
            int(args.get("ecmp_width", cls._DEFAULT_ECMP_WIDTH)),
            sw.get("switchSettings", {}).get("ecmpWidth", 0),
        )
        if len(pairs) > width:
            width = len(pairs)
            base_json.setdefault("defaultCommandLineArgs", {})["ecmp_width"] = str(width)
            sw.setdefault("switchSettings", {})["ecmpWidth"] = width
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
            args = qsfp.setdefault("defaultCommandLineArgs", {})
            args["subscribe_to_state_from_fsdb"] = "false"
            # Remediation hard-resets optics whose ports have been down >120s,
            # counting time a test holds them down (e.g. PRBS); its ASIC-PRBS
            # exemption needs the FSDB subscription disabled above.
            args["remediation_enabled"] = "false"
            self._inject_variant_flags(qsfp)
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(qsfp, f, indent=4)
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

        model = normalize_model(self.tc["model"])
        self._stage_qsfp_config()

        # Set by the nhtest executor to a {port: peer_port} JSON file (TEST_SNAKE_PAIRS)
        # when cabling was generated from netbox; absent for standalone dev runs.
        pairs = self._load_snake_pairs()
        if not pairs:
            return

        if self._pass_ports is not None:
            allowed = set(self._pass_ports)
            pairs = {port: peer for port, peer in pairs.items() if port in allowed and peer in allowed}
        # The pairs come from netbox while _pass_ports comes from the DUT, so a
        # documented cable whose optic is absent drops out here. Falling back to the
        # stock config beats letting _overlay_cabling raise mid-run, which would skip
        # post_test and leave fsdb/qsfp_service stopped.
        if not pairs:
            logger.warning("No cabled pairs left after filtering to this pass's ports; using the stock config")
            # An earlier pass may have uploaded one; don't silently reuse its cabling.
            self._use_generated_config = False
            return

        config_name = self._config_name(model)
        base_config, port_map = self._load_base_config_and_port_map(self._BASE_CONFIG_DIR, config_name)
        # Set by _run_cabling_aware for this pass; None on the max path, which
        # is the only way pre_test is reached without one.
        resolution = self._pass_variant_resolution
        profile_overrides = None
        if resolution is not None:
            pairs = resolution.expanded_pairs
            profile_overrides = resolution.profile_overrides
        config = self._overlay_cabling(
            copy.deepcopy(base_config), pairs, port_map, profile_overrides
        )
        self._upload_generated_config(config)

    def test_args(self, model: str) -> str:
        if self._use_generated_config:
            config_arg = self._REMOTE_CONFIG_PATH
        else:
            config_arg = self._variantized_config_arg(
                f"./share/link_test_configs/{self._config_name(model)}.materialized_JSON",
                "/home/netops/variant_link_test.materialized_JSON",
            )
        qsfp_arg = (
            self._REMOTE_QSFP_CONFIG_PATH
            if self._use_generated_qsfp
            else self._SYSTEM_QSFP_CONFIG_PATH
        )
        return (
            f"link --config {config_arg} --qsfp-config {qsfp_arg}"
        )

    def post_test(self):
        # The link gtest stops production qsfp_service / fsdb (via the
        # internal cleanup_*_service helpers) but never restarts them.
        self.ssh_client.run_cmd("sudo systemctl start fsdb qsfp_service")
