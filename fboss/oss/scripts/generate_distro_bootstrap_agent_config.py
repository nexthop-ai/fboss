#!/usr/bin/env python3
"""Generate an FBOSS agent.conf JSON from platform description CSV files.

Usage:
    generate_agent_config.py --platform <name> [--platforms-dir <path>]
                             [--output <path>]

Example:
    generate_agent_config.py --platform nh4010f --output agent.conf
    generate_agent_config.py --platform wedge800bnhp
"""

import argparse
import csv
import json
import pathlib
import re
import sys

# ---------------------------------------------------------------------------
# Profile ID → speed_mbps table
# Derived from switch_config.thrift PortProfileID enum.
# ---------------------------------------------------------------------------
PROFILE_SPEED: dict[int, int] = {
    0: 0,  # DEFAULT
    1: 10000,  # 10G_NRZ
    3: 25000,  # 25G_NRZ
    8: 100000,  # 100G_4_NRZ_RS528
    9: 200000,  # 200G_4_PAM4
    10: 400000,  # 400G_8_PAM4
    11: 10000,  # 10G_COPPER
    14: 25000,  # 25G_COPPER
    19: 50000,  # 50G_1_NRZ_NOFEC_COPPER (guessed)
    21: 50000,  # 50G_1_NRZ_RS528_COPPER (guessed)
    22: 100000,  # 100G_4_RS528_COPPER
    23: 100000,  # 100G_4_RS528_OPTICAL
    24: 200000,  # 200G_4_COPPER
    25: 200000,  # 200G_4_OPTICAL
    26: 400000,  # 400G_8_OPTICAL
    32: 400000,  # 400G (guessed)
    35: 400000,  # 400G_8_COPPER
    36: 53000,  # 53G_1_COPPER
    37: 53000,  # 53G_1_OPTICAL
    38: 400000,  # 400G_4_OPTICAL  ← primary preferred
    39: 800000,  # 800G_8_OPTICAL
    41: 106000,  # 106G_1_COPPER
    42: 106000,  # 106G_1_OPTICAL
    43: 400000,  # 400G (guessed, copper variant)
    45: 400000,  # 400G_4_COPPER
    47: 100000,  # 100G_1_OPTICAL
    49: 100000,  # 100G_1_NOFEC_COPPER
    50: 800000,  # 800G_8_COPPER
    54: 800000,  # 800G (guessed)
    55: 800000,  # 800G (guessed)
    56: 800000,  # 800G (guessed)
}

# Optical profile IDs (prefer these over copper when choosing best profile)
OPTICAL_PROFILES = {
    1,
    3,
    8,
    9,
    10,
    23,
    25,
    26,
    37,
    38,
    39,
    42,
    47,
    54,
    55,
    56,
}

# ASIC core type string → asicType integer
CORE_TYPE_TO_ASIC: dict[str, int] = {
    "TH5_NIF": 13,  # MEMORY_ASIC_TYPE_MEMORY_BCM56990
    "J3_NIF": 15,  # Jericho3
}

DEFAULT_ASIC_TYPE = 13


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_platforms_dir(script_path: pathlib.Path) -> pathlib.Path:
    """Walk up from the script to locate the platform_mapping_v2/platforms dir."""
    candidates = [
        script_path.parent.parent.parent / "lib" / "platform_mapping_v2" / "platforms",
        script_path.parent.parent.parent.parent
        / "fboss"
        / "lib"
        / "platform_mapping_v2"
        / "platforms",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        "Cannot auto-detect platforms directory. Use --platforms-dir."
    )


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _detect_asic_type(static_rows: list[dict[str, str]]) -> int:
    """Infer asicType integer from Z_CORE_TYPE values in the static mapping."""
    for row in static_rows:
        core_type = row.get("Z_CORE_TYPE", "").strip()
        if core_type in CORE_TYPE_TO_ASIC:
            return CORE_TYPE_TO_ASIC[core_type]
        core_type = row.get("A_CORE_TYPE", "").strip()
        if core_type in CORE_TYPE_TO_ASIC:
            return CORE_TYPE_TO_ASIC[core_type]
    return DEFAULT_ASIC_TYPE


def _choose_profile(supported_profiles_str: str) -> tuple[int, int]:
    """Return (profile_id, speed_mbps) for the highest-speed optical profile.

    Falls back to the highest-speed profile overall only if no optical
    profiles are available.
    """
    if not supported_profiles_str.strip():
        return 0, 0

    ids = [int(p) for p in supported_profiles_str.split("-") if p.strip()]
    if not ids:
        return 0, 0

    optical = [
        (pid, PROFILE_SPEED.get(pid, 0)) for pid in ids if pid in OPTICAL_PROFILES
    ]
    if optical:
        return max(optical, key=lambda x: x[1])

    all_speeds = [(pid, PROFILE_SPEED.get(pid, 0)) for pid in ids]
    return max(all_speeds, key=lambda x: x[1])


def _is_primary_port(port_name: str) -> bool:
    """Return True if the port name ends with /1 (primary port of an OSFP group)."""
    parts = port_name.rsplit("/", 1)
    return len(parts) == 2 and parts[1] == "1"


def _build_cpu_queues() -> list[dict]:
    """4 CPU queues: high, mid, default (1000 pps), low (500 pps)."""
    return [
        {"id": 9, "streamType": 1, "scheduling": 1, "name": "cpuQueue-high"},
        {"id": 2, "streamType": 1, "scheduling": 1, "name": "cpuQueue-mid"},
        {
            "id": 1,
            "streamType": 1,
            "scheduling": 1,
            "name": "cpuQueue-default",
            "portQueueRate": {"pktsPerSec": {"minimum": 0, "maximum": 1000}},
        },
        {
            "id": 0,
            "streamType": 1,
            "scheduling": 1,
            "name": "cpuQueue-low",
            "portQueueRate": {"pktsPerSec": {"minimum": 0, "maximum": 500}},
        },
    ]


def _build_cpu_traffic_policy() -> dict:
    return {
        "rxReasonToQueueOrderedList": [
            {"rxReason": 8, "queueId": 9},
            {"rxReason": 1, "queueId": 9},
            {"rxReason": 10, "queueId": 9},
            {"rxReason": 11, "queueId": 9},
            {"rxReason": 12, "queueId": 9},
            {"rxReason": 13, "queueId": 9},
            {"rxReason": 9, "queueId": 2},
            {"rxReason": 7, "queueId": 2},
            {"rxReason": 2, "queueId": 2},
            {"rxReason": 17, "queueId": 2},
            {"rxReason": 6, "queueId": 0},
            {"rxReason": 14, "queueId": 0},
            {"rxReason": 0, "queueId": 1},
        ]
    }


def _build_load_balancers() -> list[dict]:
    """ECMP (L3+L4 hash) + AGGREGATE_PORT (L3-only hash), both CRC16."""
    return [
        {
            "id": 1,
            "fieldSelection": {
                "ipv4Fields": [1, 2],
                "ipv6Fields": [1, 2],
                "transportFields": [1, 2],
                "mplsFields": [],
                "udfGroups": [],
            },
            "algorithm": 1,
        },
        {
            "id": 2,
            "fieldSelection": {
                "ipv4Fields": [1, 2],
                "ipv6Fields": [1, 2],
                "transportFields": [],
                "mplsFields": [],
                "udfGroups": [],
            },
            "algorithm": 1,
        },
    ]


def _build_qos_policies() -> list[dict]:
    """SONiC-standard QoS: 8 DSCP blocks → 8 traffic classes, 1:1 TC-to-queue."""
    dscp_maps = []
    for tc in range(8):
        dscp_maps.append(
            {
                "internalTrafficClass": tc,
                "fromDscpToTrafficClass": list(range(tc * 8, tc * 8 + 8)),
            }
        )
    return [
        {
            "name": "default",
            "qosMap": {
                "dscpMaps": dscp_maps,
                "expMaps": [],
                "trafficClassToQueueId": {str(i): i for i in range(8)},
            },
        }
    ]


def _select_primary_ports(ppm_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter to primary INTERFACE ports (ending in /1), sorted by port name."""
    selected = [
        row
        for row in ppm_rows
        if row.get("Port_Type", "0").strip() == "0"
        and _is_primary_port(row.get("Port_Name", "").strip())
        and row.get("Supported_Port_Profiles", "").strip()
    ]
    selected.sort(
        key=lambda r: [
            int(x) for x in re.findall(r"\d+", r.get("Port_Name", "").strip())
        ]
    )
    return selected


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------


def generate_config(
    platform: str,
    platforms_dir: pathlib.Path,
) -> dict:
    """Build and return the agent config dict."""

    platform_dir = platforms_dir / platform
    if not platform_dir.is_dir():
        raise FileNotFoundError(f"Platform directory not found: {platform_dir}")

    ppm_path = platform_dir / f"{platform}_port_profile_mapping.csv"
    static_path = platform_dir / f"{platform}_static_mapping.csv"

    if not ppm_path.exists():
        raise FileNotFoundError(f"Port profile mapping not found: {ppm_path}")
    if not static_path.exists():
        raise FileNotFoundError(f"Static mapping not found: {static_path}")

    ppm_rows = _read_csv(ppm_path)
    static_rows = _read_csv(static_path)

    asic_type = _detect_asic_type(static_rows)
    selected_rows = _select_primary_ports(ppm_rows)

    # Each interface uses a kernel routing table, but only 253 are available for use. Thus we cannot leave gaps to
    # account for future breakouts at the moment.
    vlan_stride = 1

    # ------------------------------------------------------------------
    # Build port, VLAN, vlanPort, and interface lists
    # ------------------------------------------------------------------
    ports = []
    vlans = []
    vlan_ports = []
    interfaces = []

    vlan_offset = 1
    for row in selected_rows:
        global_port_id = int(row.get("Global_PortID", "0").strip())
        port_name = row.get("Port_Name", "").strip()
        scope_str = row.get("Scope", "0").strip()
        scope = int(scope_str) if scope_str.isdigit() else 0
        supported = row.get("Supported_Port_Profiles", "").strip()

        profile_id, speed = _choose_profile(supported)
        vlan_id = 2000 + vlan_offset
        vlan_offset += vlan_stride

        ports.append(
            {
                "logicalID": global_port_id,
                "name": port_name,
                "state": 2,
                "speed": speed,
                "profileID": profile_id,
                "minFrameSize": 64,
                "maxFrameSize": 9412,
                "parserType": 1,
                "routable": True,
                "ingressVlan": vlan_id,
                "pause": {"rx": False, "tx": False},
                "sFlowIngressRate": 0,
                "sFlowEgressRate": 0,
                "loopbackMode": 0,
                "portType": 0,
                "drainState": 0,
                "scope": scope,
                "conditionalEntropyRehash": False,
            }
        )

        vlans.append(
            {
                "name": f"vlan{vlan_id}",
                "id": vlan_id,
                "recordStats": True,
                "routable": True,
                "ipAddresses": [],
            }
        )

        vlan_ports.append(
            {
                "vlanID": vlan_id,
                "logicalPort": global_port_id,
                "spanningTreeState": 2,
                "emitTags": False,
            }
        )

        interfaces.append(
            {
                "intfID": vlan_id,
                "routerID": 0,
                "vlanID": vlan_id,
                "ipAddresses": [],
                "mtu": 9412,
                "isVirtual": False,
                "isStateSyncDisabled": False,
                "type": 1,
                "scope": 0,
            }
        )

    # Add loopback VLAN (10) and default VLAN (4094)
    vlans.insert(
        0,
        {
            "name": "fbossLoopback0",
            "id": 10,
            "recordStats": True,
            "routable": True,
            "ipAddresses": [],
        },
    )
    vlans.append(
        {
            "name": "default",
            "id": 4094,
            "recordStats": True,
            "routable": False,
            "ipAddresses": [],
        }
    )

    # Loopback interface
    interfaces.insert(
        0,
        {
            "intfID": 10,
            "routerID": 0,
            "vlanID": 10,
            "ipAddresses": [],
            "mtu": 9412,
            "isVirtual": True,
            "isStateSyncDisabled": False,
            "type": 1,
            "scope": 0,
        },
    )

    # ------------------------------------------------------------------
    # Assemble sw section
    # ------------------------------------------------------------------
    sw = {
        "version": 0,
        "ports": ports,
        "vlans": vlans,
        "vlanPorts": vlan_ports,
        "defaultVlan": 4094,
        "interfaces": interfaces,
        "arpTimeoutSeconds": 60,
        "arpRefreshSeconds": 20,
        "arpAgerInterval": 5,
        "proactiveArp": False,
        "maxNeighborProbes": 300,
        "staleEntryInterval": 10,
        "staticRoutesWithNhops": [],
        "staticRoutesToNull": [],
        "staticRoutesToCPU": [],
        "acls": [],
        "aggregatePorts": [],
        "sFlowCollectors": [],
        "cpuQueues": _build_cpu_queues(),
        "cpuTrafficPolicy": _build_cpu_traffic_policy(),
        "loadBalancers": _build_load_balancers(),
        "mirrors": [],
        "trafficCounters": [],
        "qosPolicies": _build_qos_policies(),
        "defaultPortQueues": [],
        "staticMplsRoutesWithNhops": [],
        "staticMplsRoutesToNull": [],
        "staticMplsRoutesToCPU": [],
        "staticIp2MplsRoutes": [],
        "portQueueConfigs": {},
        "switchSettings": {
            "l2LearningMode": 0,
            "qcmEnable": False,
            "ptpTcEnable": False,
            "l2AgeTimerSeconds": 300,
            "maxRouteCounterIDs": 0,
            "blockNeighbors": [],
            "macAddrsToBlock": [],
            "switchType": 0,
            "exactMatchTableConfigs": [],
            "switchDrainState": 0,
            "switchIdToSwitchInfo": {
                "0": {
                    "switchType": 0,
                    "asicType": asic_type,
                    "switchIndex": 0,
                    "portIdRange": {"minimum": 0, "maximum": 2047},
                    "firmwareNameToFirmwareInfo": {},
                }
            },
            "vendorMacOuis": [],
            "metaMacOuis": [],
            "needL2EntryForNeighbor": True,
        },
        "dsfNodes": {},
        "defaultVoqConfig": [],
        "mirrorOnDropReports": [],
    }

    # ------------------------------------------------------------------
    # Platform section (ASIC YAML populated externally or left empty)
    # ------------------------------------------------------------------
    platform_section: dict = {"chip": {"asicConfig": {"common": {}}}}

    # ------------------------------------------------------------------
    # Assemble top-level config
    # ------------------------------------------------------------------
    config: dict = {
        "defaultCommandLineArgs": {
            "check_wb_handles": "true",
            "counter_refresh_interval": "0",
            "disable_neighbor_updates": "true",
            "ecmp_width": "320",
            "enable_replayer": "true",
            "log_variable_name": "true",
            "sai_configure_six_tap": "true",
            "multi_switch": "false",
            "publish_state_to_fsdb": "true",
            "publish_stats_to_fsdb": "true",
            "use_full_dlb_scale": "true",
        },
        "sw": sw,
        "platform": platform_section,
    }

    return config


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_path = pathlib.Path(__file__).resolve()
    try:
        default_platforms_dir = str(_find_platforms_dir(script_path))
    except FileNotFoundError:
        default_platforms_dir = None

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--platform",
        required=True,
        help="Platform name (e.g. nh4010f, wedge800bnhp)",
    )
    parser.add_argument(
        "--platforms-dir",
        default=default_platforms_dir,
        help=(
            "Path to the platform_mapping_v2/platforms directory "
            "(auto-detected by default)"
        ),
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output file path (default: stdout)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.platforms_dir:
        print(
            "ERROR: Could not auto-detect platforms directory. "
            "Pass --platforms-dir explicitly.",
            file=sys.stderr,
        )
        return 1

    platforms_dir = pathlib.Path(args.platforms_dir)
    if not platforms_dir.is_dir():
        print(f"ERROR: platforms directory not found: {platforms_dir}", file=sys.stderr)
        return 1

    try:
        config = generate_config(
            platform=args.platform,
            platforms_dir=platforms_dir,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(config, indent=2, sort_keys=True)

    if args.output == "-":
        print(output)
    else:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n")
        print(f"Wrote {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
