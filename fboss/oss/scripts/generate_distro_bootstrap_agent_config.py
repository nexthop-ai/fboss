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
# core type (Q4D_NIF) absent from CORE_TYPE_TO_ASIC.
PLATFORM_ASIC_TYPE: dict[str, int] = {"m4340nhp": 23}

# Jericho2/3/4 and the Qumran parts derived from them accept only VOQ. Ramon is
# DNX too but is FABRIC, so it is deliberately absent.
VOQ_ASIC_TYPES = {11, 14, 23, 24}

SWITCH_TYPE_NPU = 0
SWITCH_TYPE_VOQ = 2

PORT_MAX_FRAME_SIZE = 9412
INTERFACE_MTU = 9000

# switch_config.thrift PortType, as spelled in the Port_Type CSV column.
PORT_TYPE_INTERFACE = "0"
PORT_TYPE_RECYCLE = "3"
PORT_TYPE_MANAGEMENT = "4"
PORT_TYPE_EVENTOR = "5"

# switch_config.thrift PortState
PORT_STATE_DISABLED = 1
PORT_STATE_ENABLED = 2

# fboss_common.thrift PlatformType, needed for the VOQ switch's own DSF node.
PLATFORM_TYPE: dict[str, int] = {"m4340nhp": 59}

# VOQ (DSF) settings for a standalone switch: one DSF node (itself, switchId 0).
VOQ_SWITCH_ID = 0
# System port id = logical port id + offset, while the platform-created CPU
# system ports keep their raw ids, so each VOQ platform's offset must clear
# them: Q4D creates 17 (ids 0-16). The range must cover every logical port id
# plus the offset.
VOQ_SYSTEM_PORT_OFFSET: dict[str, int] = {"m4340nhp": 17}


def _system_port_offset(codename: str, switch_type: int) -> int:
    """System-port offset for a VOQ platform; NPU platforms have no system ports."""
    if switch_type != SWITCH_TYPE_VOQ:
        return 0
    if codename not in VOQ_SYSTEM_PORT_OFFSET:
        raise ValueError(
            f"VOQ_SYSTEM_PORT_OFFSET has no system-port offset for VOQ platform {codename}"
        )
    return VOQ_SYSTEM_PORT_OFFSET[codename]


VOQ_SYSTEM_PORT_RANGE_MAX = 1024
DSF_NODE_TYPE_INTERFACE_NODE = 2
DSF_NODE_SCHEDULING_DEFAULT = 1000  # QueueScheduling.INTERNAL
INTERFACE_TYPE_VLAN = 1
INTERFACE_TYPE_SYSTEM_PORT = 2

# Shown in the Description column of "fboss2 show interface". These ports read
# "down" with an empty cage, which is easily mistaken for the BMC/CPU
# management NIC being down.
MANAGEMENT_PORT_DESCRIPTION = "Management port (front-panel)"

# G202X (asicType 20) only has 8 CPU queues; queue 9 crashes SAI on trap install.
HIGH_PRIO_CPU_QUEUE_BY_ASIC: dict[int, int] = {20: 7}
DEFAULT_HIGH_PRIO_CPU_QUEUE = 9

# G202X CPU queues are UNICAST (G202xAsic::getQueueStreamTypes); the agent
# rejects a config whose cpuQueues use a streamType the CPU port does not support.
CPU_QUEUE_STREAM_TYPE_BY_ASIC: dict[int, int] = {20: 0}
DEFAULT_CPU_QUEUE_STREAM_TYPE = 1

# switch_config.thrift PacketRxReason values used by the ACL-based policy.
RX_REASON_TTL_1 = 6
RX_REASON_PORT_MTU_ERROR = 21

# Qumran4D reports NO_RX_REASON_TRAP and runs the SAI with
# sai_custom_init_profile=1, which refuses host-interface traps for protocol
# rx reasons ("Trap id 0x2009 Not allowed to be created via HostIf trap" for
# NDP). FBOSS punts that traffic with CPU ACLs instead, in an L2/IPv4 table and
# a separate IPv6 table, and keeps only TTL_1 and PORT_MTU_ERROR as rx reasons.
# Qumran4D gets the config FBOSS's test utilities build for it:
# getCoppRxReasonToQueuesForSai, defaultIngressCpuAclsForSai,
# setDefaultCpuTrafficPolicyConfig and AclConfigUtils addDefaultAclTable.
# Other ASIC types keep the generic policy.
ACL_COPP_ASIC_TYPES = {23}

# Qumran4D CPU queues (Jericho3Asic ids): high 7, mid 3, low 0, with the queue
# and VOQ limits Meta's Jericho3 configs use.
Q4D_HIGH_PRIO_CPU_QUEUE = 7
Q4D_MID_PRIO_CPU_QUEUE = 3
Q4D_LOW_PRIO_CPU_QUEUE = 0
Q4D_CPU_QUEUE_MAX_DYNAMIC_SHARED_BYTES = 20 * 1024 * 1024
Q4D_LOW_PRIO_CPU_QUEUE_KBITS = 100 * 1024

# switch_config.thrift enum values used in the Qumran4D CPU ACLs and queues.
STREAM_TYPE_UNICAST = 0
QUEUE_SCHEDULING_INTERNAL = 1000
ACL_ACTION_PERMIT = 1
TO_CPU_ACTION_TRAP = 1
ETHER_TYPE_IPV4 = 0x0800
ETHER_TYPE_IPV6 = 0x86DD
ETHER_TYPE_ARP = 0x0806
ETHER_TYPE_LACP = 0x8809
ETHER_TYPE_LLDP = 0x88CC
IP_TYPE_ARP_REQUEST = 4
IP_TYPE_ARP_REPLY = 5
LOOKUP_CLASS_DST_L3_LOCAL_1 = 1  # route to a local (my) IP
LOOKUP_CLASS_DST_L3_LOCAL_2 = 2  # unresolved or connected route
IP_PROTO_TCP = 6
IP_PROTO_UDP = 17
IP_PROTO_ICMPV6 = 58
BGP_PORT = 179
DSCP_NETWORK_CONTROL = 48
CPU_PORT_ID = 0
LINK_LOCAL_UCAST_NETWORK = "fe80::/10"
LINK_LOCAL_MCAST_NETWORK = "ff02::/16"
LACP_DST_MAC = "01:80:c2:00:00:02"
LLDP_DST_MAC = "01:80:c2:00:00:0e"
LLDP_CUSTOMER_BRIDGE_MAC = "01:80:c2:00:00:00"
NDP_ICMPV6_TYPES = (
    ("router-solicit", 133),
    ("router-advertisement", 134),
    ("neighbor-solicit", 135),
    ("neighbor-advertisement", 136),
    ("redirect", 137),
)
DHCP_CPU_ACLS = (
    ("dhcp-to-server", ETHER_TYPE_IPV4, 67),
    ("dhcp-to-client", ETHER_TYPE_IPV4, 68),
    ("dhcpv6-to-server", ETHER_TYPE_IPV6, 547),
    ("dhcpv6-to-client", ETHER_TYPE_IPV6, 546),
)

# AclConfigUtils addDefaultAclTable for Qumran4D (ACL_METADATA_QUALIFER),
# as switch_config.thrift AclTableQualifier values.
Q4D_IPV4_ACL_TABLE_QUALIFIERS = [
    16,  # DST_MAC
    22,  # ETHER_TYPE
    17,  # IP_TYPE
    2,  # SRC_IPV4
    3,  # DST_IPV4
    8,  # SRC_PORT
    6,  # IP_PROTOCOL_NUMBER
    15,  # DSCP
    18,  # TTL
    4,  # L4_SRC_PORT
    5,  # L4_DST_PORT
    7,  # TCP_FLAGS
    11,  # ICMPV4_TYPE
    12,  # ICMPV4_CODE
    20,  # LOOKUP_CLASS_NEIGHBOR
    21,  # LOOKUP_CLASS_ROUTE
]
Q4D_IPV6_ACL_TABLE_QUALIFIERS = [
    0,  # SRC_IPV6
    1,  # DST_IPV6
    17,  # IP_TYPE
    8,  # SRC_PORT
    26,  # IPV6_NEXT_HEADER
    22,  # ETHER_TYPE
    15,  # DSCP
    18,  # TTL
    4,  # L4_SRC_PORT
    5,  # L4_DST_PORT
    7,  # TCP_FLAGS
    13,  # ICMPV6_TYPE
    14,  # ICMPV6_CODE
    20,  # LOOKUP_CLASS_NEIGHBOR
    21,  # LOOKUP_CLASS_ROUTE
]

# Qumran4D has no HASH_FIELDS_CUSTOMIZATION: SaiHashManager throws "hash field
# customization is unsupported" for any load balancer with field selection,
# and FBOSS's addLoadBalancerToConfig adds none, so it gets none.
NO_HASH_FIELDS_CUSTOMIZATION_ASIC_TYPES = {23}

# TunManager::getInterfaceStatus only derives a status for VLAN and PORT
# interfaces, so a SYSTEM_PORT interface's kernel tap (fboss<intfID>) stays
# admin down and the host cannot send ARP/NDP or any control-plane packet
# through it unless the interface is virtual or isStateSyncDisabled. Meta's
# VOQ configs set isStateSyncDisabled on every system-port interface; the tap
# then stays up while its port is down (no auto-state).
STATE_SYNC_DISABLED_SYSTEM_PORT_INTF_ASIC_TYPES = {23}

# VOQ ports carry no VLAN: FBOSS's createDefaultPortConfig gives them
# ingressVlan 0 and Meta's VOQ configs do the same. With the bootstrap's 4094
# the port VLAN id is set before the router interfaces exist on a cold boot,
# but a warm boot re-applies it to ports that already have one and the SAI
# refuses ("Failed to set attribute PortSaiId(...) to PortVlanId: 4094: NOT
# EXECUTED"), which aborts the HW agent.
NO_INGRESS_VLAN_ASIC_TYPES = {23}

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
#   • fboss/configs/platforms  <vendor>/<platform>[/variants/<variant>]
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
    "bluekite": "m4061nhp",
    "sunbird": "m4340nhp",
}

# The agent programs the platform mapping's TX/RX precoding and RX reach only
# on ports whose config sets txPrecoding/rxPrecoding.
CODENAMES_WITH_SERDES_PRECODING = {"m4061nhp", "nh4220f"}

# Platforms whose platform mapping carries vendor-keyed port config overrides.
CODENAMES_WITH_TRANSCEIVER_VENDOR_OVERRIDES = {"m4062nhp"}
TRANSCEIVER_VENDOR_OVERRIDE_MAP_PATH = (
    "/opt/fboss/share/transceiver_vendor_overrides/nexthop.json"
)

CODENAMES_REQUIRING_PLATFORM_DESCRIPTOR = {
    "m4061nhp",
    "m4062nhp",
    "m4340nhp",
    "nh4010f",
    "nh4220f",
    "wedge800bact",
    "wedge800bnhp",
    "wedge800cact",
    "wedge800cnhp",
}


def _find_platform_dir(
    platforms_dir: pathlib.Path | None, codename: str
) -> pathlib.Path | None:
    """Locate <platforms_dir>/<vendor>/<codename>/platform_mapping."""
    if platforms_dir is None:
        return None
    for candidate in sorted(platforms_dir.glob(f"*/{codename}/platform_mapping")):
        if candidate.is_dir():
            return candidate
    return None


def _resolve_codename(platform: str, platforms_dir: pathlib.Path | None = None) -> str:
    """Resolve a platform name to the FBOSS platform_mapping_v2 codename.

    1. Direct match — platform dir exists under platforms_dir.
    2. Explicit alias — PLATFORM_CODENAME lookup.
    3. Normalised match — lowercase, strip hyphens/underscores/spaces
       (mimics fboss_init.sh logic), then retry 1 and 2.
    """
    # 1. Direct directory match
    if _find_platform_dir(platforms_dir, platform):
        return platform

    # 2. Explicit alias
    if platform in PLATFORM_CODENAME:
        return PLATFORM_CODENAME[platform]

    # 3. Normalise and retry
    normalised = platform.lower().replace("-", "").replace("_", "").replace(" ", "")
    if normalised != platform:
        if _find_platform_dir(platforms_dir, normalised):
            return normalised
        if normalised in PLATFORM_CODENAME:
            return PLATFORM_CODENAME[normalised]

    # Fall through — caller will use the original name and get a
    # FileNotFoundError with a clear message.
    return platform


def _find_platforms_dir(script_path: pathlib.Path) -> pathlib.Path:
    """Walk up from the script to locate the configs/platforms dir."""
    candidates = [
        script_path.parent.parent.parent / "configs" / "platforms",
        script_path.parent.parent.parent.parent / "fboss" / "configs" / "platforms",
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


def _build_cpu_queues(asic_type: int) -> list[dict]:
    if asic_type in ACL_COPP_ASIC_TYPES:
        return _build_q4d_cpu_queues(scheduling=1)
    high_prio_queue_id = HIGH_PRIO_CPU_QUEUE_BY_ASIC.get(
        asic_type, DEFAULT_HIGH_PRIO_CPU_QUEUE
    )
    stream_type = CPU_QUEUE_STREAM_TYPE_BY_ASIC.get(
        asic_type, DEFAULT_CPU_QUEUE_STREAM_TYPE
    )
    return [
        {
            "id": high_prio_queue_id,
            "streamType": stream_type,
            "scheduling": 1,
            "name": "cpuQueue-high",
        },
        {"id": 2, "streamType": stream_type, "scheduling": 1, "name": "cpuQueue-mid"},
        {
            "id": 1,
            "streamType": stream_type,
            "scheduling": 1,
            "name": "cpuQueue-default",
            "portQueueRate": {"pktsPerSec": {"minimum": 0, "maximum": 1000}},
        },
        {
            "id": 0,
            "streamType": stream_type,
            "scheduling": 1,
            "name": "cpuQueue-low",
            "portQueueRate": {"pktsPerSec": {"minimum": 0, "maximum": 500}},
        },
    ]


def _build_q4d_cpu_queues(scheduling: int) -> list[dict]:
    """Qumran4D CPU queues (scheduling STRICT_PRIORITY) or CPU VOQs (INTERNAL)."""
    prefix = "cpuVoq" if scheduling == QUEUE_SCHEDULING_INTERNAL else "cpuQueue"
    high = {
        "id": Q4D_HIGH_PRIO_CPU_QUEUE,
        "streamType": STREAM_TYPE_UNICAST,
        "scheduling": scheduling,
        "name": f"{prefix}-high",
    }
    mid = {
        "id": Q4D_MID_PRIO_CPU_QUEUE,
        "streamType": STREAM_TYPE_UNICAST,
        "scheduling": scheduling,
        "name": f"{prefix}-mid",
        "maxDynamicSharedBytes": Q4D_CPU_QUEUE_MAX_DYNAMIC_SHARED_BYTES,
    }
    low = {
        "id": Q4D_LOW_PRIO_CPU_QUEUE,
        "streamType": STREAM_TYPE_UNICAST,
        "scheduling": scheduling,
        "name": f"{prefix}-low",
        "maxDynamicSharedBytes": Q4D_CPU_QUEUE_MAX_DYNAMIC_SHARED_BYTES,
    }
    if scheduling != QUEUE_SCHEDULING_INTERNAL:
        low["portQueueRate"] = {
            "kbitsPerSec": {"minimum": 0, "maximum": Q4D_LOW_PRIO_CPU_QUEUE_KBITS}
        }
    return [high, mid, low]


def _build_cpu_voqs(asic_type: int) -> list[dict]:
    if asic_type in ACL_COPP_ASIC_TYPES:
        return _build_q4d_cpu_queues(scheduling=QUEUE_SCHEDULING_INTERNAL)
    return []


def _cpu_acl_action(queue_id: int) -> dict:
    """getToQueueActionForSai with sai_user_defined_trap off and a TRAP action."""
    return {"sendToQueue": {"queueId": queue_id}, "toCpuAction": TO_CPU_ACTION_TRAP}


def _build_cpu_acls() -> list[tuple[dict, dict]]:
    """(AclEntry, MatchAction) pairs in defaultIngressCpuAclsForSai order for a
    NO_RX_REASON_TRAP ASIC with ACL_METADATA_QUALIFER and ACL_ENTRY_ETHER_TYPE."""
    high = _cpu_acl_action(Q4D_HIGH_PRIO_CPU_QUEUE)
    mid = _cpu_acl_action(Q4D_MID_PRIO_CPU_QUEUE)
    low = _cpu_acl_action(Q4D_LOW_PRIO_CPU_QUEUE)
    acls: list[tuple[dict, dict]] = []

    def add(entry: dict, action: dict, ether_types: tuple[int, ...] = ()) -> None:
        if not ether_types:
            acls.append((entry, action))
        for ether_type in ether_types:
            suffix = "-v4" if ether_type == ETHER_TYPE_IPV4 else "-v6"
            acls.append(
                (
                    {**entry, "name": entry["name"] + suffix, "etherType": ether_type},
                    action,
                )
            )

    ip_both = (ETHER_TYPE_IPV4, ETHER_TYPE_IPV6)
    ip6 = (ETHER_TYPE_IPV6,)
    # Link-local traffic the CPU itself sends: no action.
    add(
        {
            "name": f"cpuPolicing-CPU-Port-linkLocal-v6-{LINK_LOCAL_UCAST_NETWORK}",
            "dstIp": LINK_LOCAL_UCAST_NETWORK,
            "srcPort": CPU_PORT_ID,
        },
        {},
        ip6,
    )
    add(
        {
            "name": f"cpuPolicing-CPU-Port-Mcast-v6-{LINK_LOCAL_MCAST_NETWORK}",
            "dstIp": LINK_LOCAL_MCAST_NETWORK,
            "srcPort": CPU_PORT_ID,
        },
        {},
        ip6,
    )
    for network in (LINK_LOCAL_MCAST_NETWORK, LINK_LOCAL_UCAST_NETWORK):
        add(
            {
                "name": f"cpuPolicing-high-{network}-network-control",
                "dstIp": network,
                "dscp": DSCP_NETWORK_CONTROL,
            },
            high,
            ip6,
        )
    for network in (LINK_LOCAL_MCAST_NETWORK, LINK_LOCAL_UCAST_NETWORK):
        add({"name": f"cpuPolicing-mid-{network}", "dstIp": network}, mid, ip6)
    add(
        {
            "name": "cpuPolicing-high-myip-network-control-acl",
            "lookupClassRoute": LOOKUP_CLASS_DST_L3_LOCAL_1,
            "dscp": DSCP_NETWORK_CONTROL,
        },
        high,
        ip_both,
    )
    add(
        {
            "name": "cpu-unresolved-route-acl",
            "lookupClassRoute": LOOKUP_CLASS_DST_L3_LOCAL_2,
        },
        low,
        ip_both,
    )
    add(
        {
            "name": "cpuPolicing-high-arp-request-acl",
            "etherType": ETHER_TYPE_ARP,
            "ipType": IP_TYPE_ARP_REQUEST,
        },
        high,
    )
    add(
        {
            "name": "cpuPolicing-high-arp-reply-acl",
            "etherType": ETHER_TYPE_ARP,
            "ipType": IP_TYPE_ARP_REPLY,
        },
        high,
    )
    for name, icmp_type in NDP_ICMPV6_TYPES:
        add(
            {
                "name": f"cpuPolicing-high-ndp-{name}-acl",
                "etherType": ETHER_TYPE_IPV6,
                "proto": IP_PROTO_ICMPV6,
                "ttl": {"value": 255, "mask": 255},
                "icmpType": icmp_type,
            },
            high,
        )
    for direction, field in (("dst", "l4DstPort"), ("src", "l4SrcPort")):
        add(
            {
                "name": f"cpuPolicing-high-{direction}-port-bgp-acl",
                field: BGP_PORT,
                "lookupClassRoute": LOOKUP_CLASS_DST_L3_LOCAL_1,
                "proto": IP_PROTO_TCP,
            },
            high,
            ip_both,
        )
    add(
        {
            "name": "cpuPolicing-mid-ip2me-acl",
            "lookupClassRoute": LOOKUP_CLASS_DST_L3_LOCAL_1,
        },
        mid,
        ip_both,
    )
    add(
        {
            "name": "cpuPolicing-high-lacp-acl",
            "etherType": ETHER_TYPE_LACP,
            "dstMac": LACP_DST_MAC,
        },
        high,
    )
    for name, dst_mac in (
        ("cpuPolicing-mid-lldp-acl", LLDP_DST_MAC),
        ("cpuPolicing-mid-lldp-dstMac00", LLDP_CUSTOMER_BRIDGE_MAC),
    ):
        add({"name": name, "etherType": ETHER_TYPE_LLDP, "dstMac": dst_mac}, mid)
    for name, ether_type, port in DHCP_CPU_ACLS:
        add(
            {
                "name": f"cpuPolicing-mid-{name}",
                "proto": IP_PROTO_UDP,
                "l4DstPort": port,
                "etherType": ether_type,
            },
            mid,
        )
    for entry, _ in acls:
        entry.setdefault("actionType", ACL_ACTION_PERMIT)
    return acls


def _acl_table(
    name: str, priority: int, qualifiers: list[int], entries: list[dict]
) -> dict:
    return {
        "name": name,
        "priority": priority,
        "aclEntries": entries,
        "actionTypes": [],
        "qualifiers": qualifiers,
        "udfGroups": [],
    }


def _build_acl_table_groups(asic_type: int) -> list[dict]:
    if asic_type not in ACL_COPP_ASIC_TYPES:
        tables = [_acl_table("AclTable1", 0, [], [])]
    else:
        # IPv6 entries go to the IPv6 table: the L2/IPv4 table has no IPv6
        # qualifiers, so they would never match there.
        entries = [entry for entry, _ in _build_cpu_acls()]
        tables = [
            _acl_table(
                "AclTable1",
                0,
                Q4D_IPV4_ACL_TABLE_QUALIFIERS,
                [e for e in entries if e.get("etherType") != ETHER_TYPE_IPV6],
            ),
            _acl_table(
                "ipv6-acl-table",
                1,
                Q4D_IPV6_ACL_TABLE_QUALIFIERS,
                [e for e in entries if e.get("etherType") == ETHER_TYPE_IPV6],
            ),
        ]
    return [{"name": "acl-table-group-ingress", "aclTables": tables, "stage": 0}]


def _build_cpu_traffic_policy(asic_type: int) -> dict:
    if asic_type in ACL_COPP_ASIC_TYPES:
        return _build_acl_cpu_traffic_policy()
    high_prio_queue_id = HIGH_PRIO_CPU_QUEUE_BY_ASIC.get(
        asic_type, DEFAULT_HIGH_PRIO_CPU_QUEUE
    )
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


def _build_acl_cpu_traffic_policy() -> dict:
    """CPU ACL matchers plus the rx reasons left on an ACL_COPP_ASIC_TYPES ASIC."""
    return {
        "trafficPolicy": {
            "matchToAction": [
                {"matcher": entry["name"], "action": action}
                for entry, action in _build_cpu_acls()
            ]
        },
        "rxReasonToQueueOrderedList": [
            {"rxReason": RX_REASON_TTL_1, "queueId": Q4D_LOW_PRIO_CPU_QUEUE},
            {"rxReason": RX_REASON_PORT_MTU_ERROR, "queueId": Q4D_LOW_PRIO_CPU_QUEUE},
        ],
    }


def _build_load_balancers(asic_type: int) -> list[dict]:
    """ECMP (L3+L4 hash) + AGGREGATE_PORT (L3-only hash), both CRC16."""
    if asic_type in NO_HASH_FIELDS_CUSTOMIZATION_ASIC_TYPES:
        return []
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
                "state": PORT_STATE_DISABLED,
                "speed": speed,
                "profileID": profile_id,
                "minFrameSize": 64,
                "maxFrameSize": PORT_MAX_FRAME_SIZE,
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


def _select_internal_ports(
    ppm_rows: list[dict[str, str]], port_type: str
) -> list[dict[str, str]]:
    """All RECYCLE / EVENTOR rows of a DNX port profile mapping, by port id.

    These have no front-panel cage, so every row is kept (no "/1" filter).
    """
    selected = [
        row
        for row in ppm_rows
        if row.get("Port_Type", "0").strip() == port_type
        and row.get("Supported_Port_Profiles", "").strip()
    ]
    selected.sort(key=lambda r: int(r.get("Global_PortID", "0").strip()))
    return selected


def _inband_port_id(ppm_rows: list[dict[str, str]]) -> int:
    """The GLOBAL-scope recycle port a VOQ switch uses to reach its own CPU path.

    The agent CHECKs that switchInfo/dsfNode carry an inbandPortId; on DNX it is
    the recycle port with Scope=1 (blackwolf800banw: rcy 35, meru800bia: rcy 1).
    """
    candidates = [
        int(row.get("Global_PortID", "0").strip())
        for row in _select_internal_ports(ppm_rows, PORT_TYPE_RECYCLE)
        if row.get("Scope", "0").strip() == "1"
    ]
    if len(candidates) != 1:
        raise ValueError(
            "VOQ platform needs exactly one GLOBAL-scope (Scope=1) recycle port "
            f"for inbandPortId, found {candidates}"
        )
    return candidates[0]


def _build_internal_ports(ppm_rows: list[dict[str, str]]) -> list[dict]:
    """Build the recycle and eventor port entries of a VOQ switch.

    The SDK creates these at init like the management ports, so they must be
    in the SwitchState. Recycle ports are ENABLED (the GLOBAL one carries the
    inband CPU path); eventor ports are DISABLED until eventor is in use.
    """
    ports = []
    for port_type, state, routable in (
        (PORT_TYPE_RECYCLE, PORT_STATE_ENABLED, True),
        (PORT_TYPE_EVENTOR, PORT_STATE_DISABLED, False),
    ):
        for row in _select_internal_ports(ppm_rows, port_type):
            profile_id, speed = _choose_profile(
                row.get("Supported_Port_Profiles", "").strip()
            )
            scope_str = row.get("Scope", "0").strip()
            ports.append(
                {
                    "logicalID": int(row.get("Global_PortID", "0").strip()),
                    "name": row.get("Port_Name", "").strip(),
                    "state": state,
                    "speed": speed,
                    "profileID": profile_id,
                    "minFrameSize": 64,
                    "maxFrameSize": PORT_MAX_FRAME_SIZE,
                    "parserType": 1,
                    "routable": routable,
                    "ingressVlan": 4094,
                    "pause": {"rx": False, "tx": False},
                    "sFlowIngressRate": 0,
                    "sFlowEgressRate": 0,
                    "loopbackMode": 0,
                    "portType": int(port_type),
                    "drainState": 0,
                    "scope": int(scope_str) if scope_str.isdigit() else 0,
                    "conditionalEntropyRehash": False,
                }
            )
    return ports


def _system_port_interface(port: dict, system_port_offset: int) -> dict:
    """SYSTEM_PORT interface for one VOQ port.

    On a VOQ switch the agent derives each port's interface itself
    (ApplyThriftConfig::processInterfaceForPortForVoqSwitches): interface id ==
    system port id == logical port id + system-port offset.
    """
    return {
        "intfID": port["logicalID"] + system_port_offset,
        "routerID": 0,
        "vlanID": 0,
        "ipAddresses": [],
        "mtu": INTERFACE_MTU,
        "isVirtual": False,
        "isStateSyncDisabled": False,
        "type": INTERFACE_TYPE_SYSTEM_PORT,
        "scope": port["scope"],
    }


def _with_q4d_port_ingress_vlan(ports: list[dict], asic_type: int) -> list[dict]:
    """Clear the ingress VLAN of every port on NO_INGRESS_VLAN_ASIC_TYPES."""
    if asic_type in NO_INGRESS_VLAN_ASIC_TYPES:
        for port in ports:
            port["ingressVlan"] = 0
    return ports


def _with_system_port_intf_state_sync(
    interfaces: list[dict], asic_type: int
) -> list[dict]:
    """Keep SYSTEM_PORT interfaces' kernel taps up on the ASICs in
    STATE_SYNC_DISABLED_SYSTEM_PORT_INTF_ASIC_TYPES."""
    if asic_type in STATE_SYNC_DISABLED_SYSTEM_PORT_INTF_ASIC_TYPES:
        for interface in interfaces:
            if interface["type"] == INTERFACE_TYPE_SYSTEM_PORT:
                interface["isStateSyncDisabled"] = True
    return interfaces


def _build_voq_switch_settings(
    switch_id_to_switch_info: dict,
    codename: str,
    ppm_rows: list[dict[str, str]],
    system_port_offset: int,
) -> dict:
    """Add the DSF fields to switchInfo and return the switch's own dsfNode.

    A standalone VOQ switch is a one-node DSF fabric; the agent CHECKs for its
    own dsfNodes entry, the system-port ranges/offsets and the inbandPortId.
    """
    max_port_id = max(
        int(row.get("Global_PortID", "0").strip())
        for row in ppm_rows
        if row.get("Global_PortID", "").strip().isdigit()
    )
    if max_port_id + system_port_offset >= VOQ_SYSTEM_PORT_RANGE_MAX:
        raise ValueError(
            f"logical port {max_port_id} + offset {system_port_offset} "
            f"exceeds the system port range [0, {VOQ_SYSTEM_PORT_RANGE_MAX})"
        )
    if codename not in PLATFORM_TYPE:
        raise ValueError(
            f"PLATFORM_TYPE has no PlatformType for VOQ platform {codename}"
        )
    system_port_ranges = {
        "systemPortRanges": [{"minimum": 0, "maximum": VOQ_SYSTEM_PORT_RANGE_MAX}]
    }
    inband_port_id = _inband_port_id(ppm_rows)
    switch_id_to_switch_info.update(
        {
            "systemPortRanges": system_port_ranges,
            "localSystemPortOffset": system_port_offset,
            "globalSystemPortOffset": system_port_offset,
            "inbandPortId": inband_port_id,
        }
    )
    return {
        "name": f"{codename}{VOQ_SWITCH_ID}",
        "switchId": VOQ_SWITCH_ID,
        "type": DSF_NODE_TYPE_INTERFACE_NODE,
        "loopbackIps": [],
        "asicType": switch_id_to_switch_info["asicType"],
        "platformType": PLATFORM_TYPE[codename],
        "localSystemPortOffset": system_port_offset,
        "globalSystemPortOffset": system_port_offset,
        "systemPortRanges": system_port_ranges,
        "inbandPortId": inband_port_id,
        "scheduling": DSF_NODE_SCHEDULING_DEFAULT,
    }


def _build_ports_vlans_interfaces(
    selected_rows: list[dict[str, str]],
    is_npu: bool,
    system_port_offset: int = 0,
    serdes_precoding: bool = False,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Build the ports, per-port VLANs, vlanPorts and interfaces lists.

    NPU: one VLAN + SVI per port (vlanID == intfID), default VLAN 4094 left
    to the CPU. VOQ: one SYSTEM_PORT interface per port (interface id ==
    system port id), no VLANs.
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
                "maxFrameSize": PORT_MAX_FRAME_SIZE,
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
        if serdes_precoding:
            ports[-1]["txPrecoding"] = True
            ports[-1]["rxPrecoding"] = True

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
                    "mtu": INTERFACE_MTU,
                    "isVirtual": False,
                    "isStateSyncDisabled": False,
                    "type": 1,  # VLAN
                    "scope": 0,
                }
            )
        else:
            interfaces.append(_system_port_interface(ports[-1], system_port_offset))

    return ports, port_vlans, vlan_ports, interfaces


def _build_default_command_line_args(codename: str) -> dict[str, str]:
    args = {
        "check_wb_handles": "false",
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
        args["platform_descriptor_config_path"] = "/tmp/platform_descriptors/"
    if codename in CODENAMES_WITH_TRANSCEIVER_VENDOR_OVERRIDES:
        args["transceiver_vendor_override_map_path"] = (
            TRANSCEIVER_VENDOR_OVERRIDE_MAP_PATH
        )
    return dict(sorted(args.items()))


def generate_config(
    platform: str,
    platforms_dir: pathlib.Path,
    asic_config_source: pathlib.Path | None = None,
) -> dict:
    """Build and return the agent config dict.

    NPU platforms get one VLAN + SVI per port (type=1); VOQ platforms get
    SYSTEM_PORT interfaces (type=2), their recycle/eventor ports and a
    one-node DSF fabric (dsfNodes self entry, inbandPortId).
    ASIC config is loaded from hw_test_configs/ materialized JSON by default.
    """
    codename = _resolve_codename(platform, platforms_dir)
    platform_dir = _find_platform_dir(platforms_dir, codename)
    if platform_dir is None:
        raise FileNotFoundError(
            f"Platform directory not found: {platforms_dir}/*/{codename}/platform_mapping"
        )

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

    system_port_offset = _system_port_offset(codename, switch_type)
    ports, port_vlans, vlan_ports, interfaces = _build_ports_vlans_interfaces(
        selected_rows,
        is_npu=switch_type == SWITCH_TYPE_NPU,
        system_port_offset=system_port_offset,
        serdes_precoding=codename in CODENAMES_WITH_SERDES_PRECODING,
    )
    ports.extend(_build_management_ports(_select_management_ports(ppm_rows)))

    dsf_nodes: dict = {}
    if switch_type == SWITCH_TYPE_VOQ:
        internal_ports = _build_internal_ports(ppm_rows)
        ports.extend(internal_ports)
        interfaces.extend(
            _system_port_interface(port, system_port_offset)
            for port in internal_ports
            if port["portType"] == int(PORT_TYPE_RECYCLE)
        )
        dsf_nodes[str(VOQ_SWITCH_ID)] = _build_voq_switch_settings(
            switch_id_to_switch_info, codename, ppm_rows, system_port_offset
        )
        # No VLANs on a VOQ switch: interfaces are system ports.
        vlans: list[dict] = []
        default_vlan = 0
    else:
        # Loopback interface (VLAN-based, virtual, no physical port)
        interfaces.insert(
            0,
            {
                "intfID": 10,
                "routerID": 0,
                "vlanID": 10,
                "ipAddresses": [],
                "mtu": INTERFACE_MTU,
                "isVirtual": True,
                "isStateSyncDisabled": False,
                "type": INTERFACE_TYPE_VLAN,
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
        default_vlan = 4094

    sw = {
        "version": 0,
        "ports": _with_q4d_port_ingress_vlan(ports, asic_type),
        "vlans": vlans,
        "vlanPorts": vlan_ports,
        "defaultVlan": default_vlan,
        "interfaces": _with_system_port_intf_state_sync(interfaces, asic_type),
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
        "aclTableGroups": _build_acl_table_groups(asic_type),
        "aggregatePorts": [],
        "sFlowCollectors": [],
        "cpuQueues": _build_cpu_queues(asic_type),
        **({"cpuVoqs": cpu_voqs} if (cpu_voqs := _build_cpu_voqs(asic_type)) else {}),
        "cpuTrafficPolicy": _build_cpu_traffic_policy(asic_type),
        "loadBalancers": _build_load_balancers(asic_type),
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
        "dsfNodes": dsf_nodes,
        "defaultVoqConfig": [],
        "mirrorOnDropReports": [],
    }

    # Platform section — ASIC config from materialized HW test config
    asic_common = _load_asic_config(asic_config_source, codename, script_path)

    return {
        "defaultCommandLineArgs": _build_default_command_line_args(codename),
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
        help="Path to fboss/configs/platforms (auto-detected by default)",
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
