#!/usr/bin/env python3
"""Generate an FBOSS agent.conf JSON from platform description CSV files.

Usage:
    generate_agent_config.py --platform <name> [--platforms-dir <path>]
                             [--asic-config-source <path>] [--output <path>]

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

# Profile ID → speed_mbps, derived from switch_config.thrift PortProfileID enum.
PROFILE_SPEED: dict[int, int] = {
    0: 0,
    1: 10000,
    3: 25000,
    8: 100000,
    9: 200000,
    10: 400000,
    11: 10000,
    12: 10000,
    14: 25000,
    16: 25000,
    19: 50000,
    21: 50000,
    22: 100000,
    23: 100000,
    24: 200000,
    25: 200000,
    26: 400000,
    30: 25000,
    32: 400000,
    35: 400000,
    36: 53000,
    37: 53000,
    38: 400000,
    39: 800000,
    41: 106000,
    42: 106000,
    43: 400000,
    45: 400000,
    47: 100000,
    48: 50000,
    49: 100000,
    50: 800000,
    54: 800000,
    55: 800000,
    56: 800000,
    62: 25000,
    63: 1600000,
    64: 1600000,
}

OPTICAL_PROFILES = {
    1,
    3,
    8,
    9,
    10,
    12,
    23,
    25,
    26,
    30,
    37,
    38,
    39,
    42,
    47,
    48,
    54,
    55,
    56,
    62,
    63,
    64,
}

CORE_TYPE_TO_ASIC: dict[str, int] = {
    "TH5_NIF": 13,
    "J3_NIF": 15,
    "TH6_NIF": 18,
    "G200": 20,
}

DEFAULT_ASIC_TYPE = 13

# Platforms whose ASIC cannot be inferred: no materialized HW test config, and a
# core type shared with a different ASIC (nh5010f and blackwolf800banw are both
# Q4D_NIF, but are Qumran3D and Qumran4D respectively).
PLATFORM_ASIC_TYPE: dict[str, int] = {"nh5010f": 27}

# Jericho2/3/4 and the Qumran parts derived from them accept only VOQ. Ramon is
# DNX too but is FABRIC, so it is deliberately absent.
VOQ_ASIC_TYPES = {11, 14, 23, 24, 27}

SWITCH_TYPE_NPU = 0
SWITCH_TYPE_VOQ = 2

# switch_config.thrift PortType, as spelled in the Port_Type CSV column.
PORT_TYPE_INTERFACE = "0"
PORT_TYPE_MANAGEMENT = "4"

# Shown in the Description column of "fboss2 show interface". These ports read
# "down" with an empty cage, which is easily mistaken for the BMC/CPU
# management NIC being down.
MANAGEMENT_PORT_DESCRIPTION = "Management port (front-panel)"

# G202X (asicType 20) only has 8 CPU queues; queue 9 crashes SAI on trap install.
HIGH_PRIO_CPU_QUEUE_BY_ASIC: dict[int, int] = {20: 7}
DEFAULT_HIGH_PRIO_CPU_QUEUE = 9

# intfIDs start at INTF_ID_OFFSET + 1. TunManager uses the intfID as the
# kernel routing table ID (enable_1to1_intf_route_table_mapping), which must
# avoid the kernel-reserved tables 0/253/254/255.
INTF_ID_OFFSET = 2000

# Map every supported --platform value to the FBOSS platform_mapping_v2
# directory name (codename).  Entries are only needed when the two differ;
# platforms whose name already matches (nh4010f, wedge800bnhp, ...) are
# resolved automatically by _resolve_codename().
#
# Sources of truth:
#   • platform_mapping_v2.py  _PLATFORM_VARIANTS_MAP
#   • platform_name_lib.py    sanitize_platform_name()
#   • nhdiags                 platform_map.py
PLATFORM_CODENAME: dict[str, str] = {
    # dmidecode / run-config name  ->  platform_mapping_v2 codename
    "minipack3": "montblanc",
    # NH marketing aliases (add new platforms here as they ship).
    # Keys are stored in normalised form (lowercase, no separators) so that
    # _resolve_codename() matches "golden_eagle", "goldeneagle", "Golden-Eagle", etc.
    "goldeneagle": "nh4010f",
    "crownedeagle": "wedge800bnhp",
    "friscoeagle": "wedge800cnhp",
    "blackkite": "nh4220f",
}

CODENAMES_REQUIRING_PLATFORM_DESCRIPTOR = {
    "m4062nhp",
    "nh4010f",
    "nh4220f",
    "wedge800bact",
}


def _resolve_codename(platform: str, platforms_dir: pathlib.Path | None = None) -> str:
    """Resolve a platform name to the FBOSS platform_mapping_v2 codename.

    1. Direct match — platform dir exists under platforms_dir.
    2. Explicit alias — PLATFORM_CODENAME lookup.
    3. Normalised match — lowercase, strip hyphens/underscores/spaces
       (mimics fboss_init.sh logic), then retry 1 and 2.
    """
    # 1. Direct directory match
    if platforms_dir and (platforms_dir / platform).is_dir():
        return platform

    # 2. Explicit alias
    if platform in PLATFORM_CODENAME:
        return PLATFORM_CODENAME[platform]

    # 3. Normalise and retry
    normalised = platform.lower().replace("-", "").replace("_", "").replace(" ", "")
    if normalised != platform:
        if platforms_dir and (platforms_dir / normalised).is_dir():
            return normalised
        if normalised in PLATFORM_CODENAME:
            return PLATFORM_CODENAME[normalised]

    # Fall through — caller will use the original name and get a
    # FileNotFoundError with a clear message.
    return platform


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


def _find_hw_test_config(
    codename: str, script_path: pathlib.Path
) -> pathlib.Path | None:
    """Locate the materialized HW test config for the resolved codename."""
    hw_test_dir = script_path.parent.parent / "hw_test_configs"
    if not hw_test_dir.is_dir():
        return None
    for suffix in ("agent.materialized_JSON", "materialized_JSON"):
        candidate = hw_test_dir / f"{codename}.{suffix}"
        if candidate.exists():
            return candidate
    return None


def _load_asic_config(
    source: pathlib.Path | None, platform: str, script_path: pathlib.Path
) -> dict:
    """Load ASIC config from a materialized JSON or standalone YAML file.

    Auto-detects from hw_test_configs/ when *source* is None.
    Returns the dict for ``platform.chip.asicConfig.common``.
    """
    if source is None:
        source = _find_hw_test_config(platform, script_path)
    if source is None:
        print(
            f"WARNING: No ASIC config source found for '{platform}'. "
            "The generated config will have an empty platform section.",
            file=sys.stderr,
        )
        return {}

    if source.suffix in (".yml", ".yaml"):
        return {"yamlConfig": source.read_text()}

    with source.open() as fh:
        data = json.load(fh)
    try:
        return data["platform"]["chip"]["asicConfig"]["common"]
    except KeyError:
        print(
            f"WARNING: Could not extract platform.chip.asicConfig.common "
            f"from {source}.",
            file=sys.stderr,
        )
        return {}


def _load_switch_info(source: pathlib.Path | None) -> dict:
    """Return the first switchIdToSwitchInfo entry from a materialized JSON."""
    if source is None or source.suffix in (".yml", ".yaml"):
        return {}

    with source.open() as fh:
        data = json.load(fh)
    info = data.get("sw", {}).get("switchSettings", {}).get("switchIdToSwitchInfo", {})
    if not info:
        return {}
    return info[sorted(info)[0]]


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _detect_asic_type(static_rows: list[dict[str, str]]) -> int:
    """Infer asicType integer from core-type values in the static mapping."""
    for row in static_rows:
        for col in ("Z_CORE_TYPE", "A_CORE_TYPE"):
            core_type = row.get(col, "").strip()
            if core_type in CORE_TYPE_TO_ASIC:
                return CORE_TYPE_TO_ASIC[core_type]
    return DEFAULT_ASIC_TYPE


def _choose_profile(supported_profiles_str: str) -> tuple[int, int]:
    """Return (profile_id, speed_mbps) for the highest-speed optical profile.

    Falls back to the highest-speed profile overall when no optical profiles
    are available.
    """
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


def _build_cpu_traffic_policy(high_prio_queue_id: int = 9) -> dict:
    return {
        "rxReasonToQueueOrderedList": [
            {"rxReason": 8, "queueId": high_prio_queue_id},
            {"rxReason": 1, "queueId": high_prio_queue_id},
            {"rxReason": 10, "queueId": high_prio_queue_id},
            {"rxReason": 11, "queueId": high_prio_queue_id},
            {"rxReason": 12, "queueId": high_prio_queue_id},
            {"rxReason": 13, "queueId": high_prio_queue_id},
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
    """8 DSCP blocks -> 8 traffic classes, 1:1 TC-to-queue."""
    dscp_maps = [
        {
            "internalTrafficClass": tc,
            "fromDscpToTrafficClass": list(range(tc * 8, tc * 8 + 8)),
        }
        for tc in range(8)
    ]
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


def _port_name_sort_key(name: str) -> list[int | str]:
    """Natural sort key for port names like 'eth1/42/1'."""
    return [int(tok) if tok.isdigit() else tok for tok in re.split(r"(\d+)", name)]


def _select_ports_of_type(
    ppm_rows: list[dict[str, str]], port_type: str
) -> list[dict[str, str]]:
    """Filter to primary ports (ending in /1) of one type, in front-panel order."""
    selected = []
    for row in ppm_rows:
        port_name = row.get("Port_Name", "").strip()
        if (
            row.get("Port_Type", "0").strip() == port_type
            and _is_primary_port(port_name)
            and row.get("Supported_Port_Profiles", "").strip()
        ):
            selected.append(row)
    selected.sort(key=lambda r: _port_name_sort_key(r["Port_Name"].strip()))
    return selected


def _select_primary_ports(ppm_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter to primary INTERFACE ports (ending in /1), sorted by front-panel order."""
    return _select_ports_of_type(ppm_rows, PORT_TYPE_INTERFACE)


def _select_management_ports(ppm_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Filter to the primary MANAGEMENT ports, sorted by front-panel order.

    Platforms with two entries come in two flavours: two distinct front-panel
    management ports (nh4220f's eth1/65/1 and eth1/66/1), both of which are
    kept, and a breakout subsidiary of a single port (wedge800bact's eth1/33/3
    under eth1/33/1), which is elided exactly like a data-port breakout.
    """
    return _select_ports_of_type(ppm_rows, PORT_TYPE_MANAGEMENT)


def _build_management_ports(selected_rows: list[dict[str, str]]) -> list[dict]:
    """Build DISABLED port entries for the management ports.

    A MANAGEMENT_PORT is an ASIC front-panel port wired to a QSFP28/OSFP cage
    and reserved for management traffic -- not the BMC/CPU NIC that carries
    ssh, which no platform mapping describes. Expect these to read "down" in
    ``fboss2 show interface`` whenever their cage is empty.

    The SDK creates these at init regardless of the agent config, so they must
    be in the SwitchState for warm boot to claim the reloaded SAI handles --
    without them ``checkUnexpectedUnclaimedWarmbootHandles`` aborts the agent.
    DISABLED keeps them out of the VLAN/interface topology.
    """
    ports = []
    for row in selected_rows:
        profile_id, speed = _choose_profile(
            row.get("Supported_Port_Profiles", "").strip()
        )
        scope_str = row.get("Scope", "0").strip()
        ports.append(
            {
                "logicalID": int(row.get("Global_PortID", "0").strip()),
                "name": row.get("Port_Name", "").strip(),
                "description": MANAGEMENT_PORT_DESCRIPTION,
                "state": 1,  # DISABLED
                "speed": speed,
                "profileID": profile_id,
                "minFrameSize": 64,
                "maxFrameSize": 9412,
                "parserType": 1,
                "routable": False,
                "ingressVlan": 4094,
                "pause": {"rx": False, "tx": False},
                "sFlowIngressRate": 0,
                "sFlowEgressRate": 0,
                "loopbackMode": 0,
                "portType": int(PORT_TYPE_MANAGEMENT),
                "drainState": 0,
                "scope": int(scope_str) if scope_str.isdigit() else 0,
                "conditionalEntropyRehash": False,
            }
        )
    return ports


def _build_ports_vlans_interfaces(
    selected_rows: list[dict[str, str]], is_npu: bool
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Build the ports, per-port VLANs, vlanPorts and interfaces lists.

    NPU: one VLAN + SVI per port (vlanID == intfID), default VLAN 4094 left
    to the CPU. VOQ: port-based L3 interfaces (type=3).
    """
    ports = []
    port_vlans = []
    vlan_ports = []
    interfaces = []

    for idx, row in enumerate(selected_rows):
        global_port_id = int(row.get("Global_PortID", "0").strip())
        port_name = row.get("Port_Name", "").strip()
        scope_str = row.get("Scope", "0").strip()
        scope = int(scope_str) if scope_str.isdigit() else 0
        profile_id, speed = _choose_profile(
            row.get("Supported_Port_Profiles", "").strip()
        )

        # intfIDs are sequential in front-panel order (2001, 2002, ...); on
        # NPU the per-port VLAN reuses the same ID.
        intf_id = INTF_ID_OFFSET + idx + 1
        ingress_vlan = intf_id if is_npu else 4094

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
                "ingressVlan": ingress_vlan,
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

        if is_npu:
            # Names follow the CLI's VlanManager conventions ("Vlan<id>" /
            # "fboss<id>") so CLI-created and bootstrap objects look alike.
            port_vlans.append(
                {
                    "name": f"Vlan{ingress_vlan}",
                    "id": ingress_vlan,
                    "recordStats": True,
                    "routable": True,
                    "ipAddresses": [],
                }
            )
            vlan_ports.append(
                {
                    "vlanID": ingress_vlan,
                    "logicalPort": global_port_id,
                    "spanningTreeState": 2,  # FORWARDING
                    "emitTags": False,
                }
            )
            interfaces.append(
                {
                    "intfID": intf_id,
                    "routerID": 0,
                    "vlanID": ingress_vlan,
                    "name": f"fboss{ingress_vlan}",
                    "ipAddresses": [],
                    "mtu": 9412,
                    "isVirtual": False,
                    "isStateSyncDisabled": False,
                    "type": 1,  # VLAN
                    "scope": 0,
                }
            )
        else:
            interfaces.append(
                {
                    "intfID": intf_id,
                    "routerID": 0,
                    "portID": global_port_id,
                    "ipAddresses": [],
                    "mtu": 9412,
                    "isVirtual": False,
                    "isStateSyncDisabled": False,
                    "type": 3,  # PORT
                    "scope": 0,
                }
            )

    return ports, port_vlans, vlan_ports, interfaces


def generate_config(
    platform: str,
    platforms_dir: pathlib.Path,
    asic_config_source: pathlib.Path | None = None,
) -> dict:
    """Build and return the agent config dict.

    NPU platforms get one VLAN + SVI per port (type=1); VOQ platforms keep
    port-based L3 interfaces (type=3).
    ASIC config is loaded from hw_test_configs/ materialized JSON by default.
    """
    codename = _resolve_codename(platform, platforms_dir)
    platform_dir = platforms_dir / codename
    if not platform_dir.is_dir():
        raise FileNotFoundError(f"Platform directory not found: {platform_dir}")

    ppm_path = platform_dir / f"{codename}_port_profile_mapping.csv"
    static_path = platform_dir / f"{codename}_static_mapping.csv"

    if not ppm_path.exists():
        raise FileNotFoundError(f"Port profile mapping not found: {ppm_path}")
    if not static_path.exists():
        raise FileNotFoundError(f"Static mapping not found: {static_path}")

    ppm_rows = _read_csv(ppm_path)
    static_rows = _read_csv(static_path)
    selected_rows = _select_primary_ports(ppm_rows)

    # The materialized HW test config is authoritative for switch info; the CSV
    # core types only cover NPUs listed in CORE_TYPE_TO_ASIC.
    script_path = pathlib.Path(__file__).resolve()
    if asic_config_source is None:
        asic_config_source = _find_hw_test_config(codename, script_path)
    switch_info = _load_switch_info(asic_config_source)
    if "asicType" in switch_info:
        asic_type = switch_info["asicType"]
    elif codename in PLATFORM_ASIC_TYPE:
        asic_type = PLATFORM_ASIC_TYPE[codename]
    else:
        asic_type = _detect_asic_type(static_rows)
    switch_type = switch_info.get(
        "switchType",
        SWITCH_TYPE_VOQ if asic_type in VOQ_ASIC_TYPES else SWITCH_TYPE_NPU,
    )
    connection_handle = switch_info.get("connectionHandle")

    switch_id_to_switch_info = {
        "switchType": switch_type,
        "asicType": asic_type,
        "switchIndex": 0,
        "portIdRange": {"minimum": 0, "maximum": 2047},
    }
    if connection_handle is not None:
        switch_id_to_switch_info["connectionHandle"] = connection_handle
    switch_id_to_switch_info["firmwareNameToFirmwareInfo"] = {}

    ports, port_vlans, vlan_ports, interfaces = _build_ports_vlans_interfaces(
        selected_rows, is_npu=switch_type == SWITCH_TYPE_NPU
    )
    ports.extend(_build_management_ports(_select_management_ports(ppm_rows)))

    # Loopback interface (VLAN-based, virtual, no physical port)
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
            "type": 1,  # VLAN
            "scope": 0,
        },
    )

    vlans = [
        {
            "name": "fbossLoopback0",
            "id": 10,
            "recordStats": True,
            "routable": True,
            "ipAddresses": [],
        },
        *port_vlans,
        {
            "name": "default",
            "id": 4094,
            "recordStats": True,
            "routable": False,
            "ipAddresses": [],
        },
    ]

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
        "aclTableGroups": [
            {
                "name": "acl-table-group-ingress",
                "aclTables": [
                    {
                        "name": "AclTable1",
                        "priority": 0,
                        "aclEntries": [],
                        "actionTypes": [],
                        "qualifiers": [],
                        "udfGroups": [],
                    }
                ],
                "stage": 0,
            }
        ],
        "aggregatePorts": [],
        "sFlowCollectors": [],
        "cpuQueues": _build_cpu_queues(),
        "cpuTrafficPolicy": _build_cpu_traffic_policy(
            HIGH_PRIO_CPU_QUEUE_BY_ASIC.get(asic_type, DEFAULT_HIGH_PRIO_CPU_QUEUE)
        ),
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
            "l2LearningMode": 1,
            "qcmEnable": False,
            "ptpTcEnable": False,
            "l2AgeTimerSeconds": 300,
            "maxRouteCounterIDs": 0,
            "blockNeighbors": [],
            "macAddrsToBlock": [],
            "switchType": switch_type,
            "exactMatchTableConfigs": [],
            "switchDrainState": 0,
            "switchIdToSwitchInfo": {"0": switch_id_to_switch_info},
            "vendorMacOuis": [],
            "metaMacOuis": [],
            "needL2EntryForNeighbor": True,
        },
        "dsfNodes": {},
        "defaultVoqConfig": [],
        "mirrorOnDropReports": [],
    }

    # Platform section — ASIC config from materialized HW test config
    asic_common = _load_asic_config(asic_config_source, codename, script_path)

    default_command_line_args = {
        "check_wb_handles": "true",
        "cleanup_probed_kernel_data": "true",
        "counter_refresh_interval": "0",
        "disable_neighbor_updates": "false",
        "ecmp_width": "320",
        "enable_1to1_intf_route_table_mapping": "true",
        "enable_acl_table_group": "true",
        "enable_replayer": "true",
        "log_variable_name": "true",
        "multi_switch": "true",
        "publish_state_to_fsdb": "true",
        "publish_stats_to_fsdb": "true",
        "sai_configure_six_tap": "true",
        "use_full_dlb_scale": "true",
    }
    if codename in CODENAMES_REQUIRING_PLATFORM_DESCRIPTOR:
        default_command_line_args["platform_descriptor_config_path"] = (
            "/tmp/platform_descriptors/"
        )

    return {
        "defaultCommandLineArgs": dict(sorted(default_command_line_args.items())),
        "sw": sw,
        "platform": {"chip": {"asicConfig": {"common": asic_common}}},
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_path = pathlib.Path(__file__).resolve()
    try:
        default_platforms_dir = str(_find_platforms_dir(script_path))
    except FileNotFoundError:
        default_platforms_dir = None

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--platform", required=True, help="Platform name (e.g. nh4010f, wedge800bnhp)"
    )
    parser.add_argument(
        "--platforms-dir",
        default=default_platforms_dir,
        help="Path to platform_mapping_v2/platforms (auto-detected by default)",
    )
    parser.add_argument(
        "--asic-config-source",
        default=None,
        help="Path to materialized JSON or YAML with ASIC config (auto-detected)",
    )
    parser.add_argument(
        "--output", default="-", help="Output file path (default: stdout)"
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

    asic_source = (
        pathlib.Path(args.asic_config_source) if args.asic_config_source else None
    )

    try:
        config = generate_config(
            platform=args.platform,
            platforms_dir=platforms_dir,
            asic_config_source=asic_source,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(config, indent=2)

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
