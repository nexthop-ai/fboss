#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

# pyre-unsafe

"""
BGP++ JSON to fboss2 CLI converter (j2c tool)

Converts BGP++ thrift-compatible JSON configuration to fboss2 CLI commands.
This enables round-trip conversion: JSON -> CLI -> JSON (via fboss2).

Usage:
    python3 bgp_json_to_cli.py <input.json> [--output output.sh]

Example:
    python3 bgp_json_to_cli.py rsw_bgp_config.json > configure_bgp.sh
"""

import argparse
import json
import sys
from typing import Any


<<<<<<< HEAD
def escape_shell_arg(arg: str) -> str:
    """Escape argument for shell usage.

    Backslash-escapes the characters that stay special inside double quotes
    (backslash, double quote, dollar, backtick) so free-form fields like
    descriptions cannot terminate the quoted string or trigger expansion in
    the generated script.
    """
    if " " in arg or '"' in arg or "'" in arg or any(c in arg for c in "!$`\\"):
        escaped = (
            arg.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
            .replace("`", "\\`")
        )
        return f'"{escaped}"'
    return arg
||||||| a86baef3b7
def escape_shell_arg(arg: str) -> str:
    """Escape argument for shell usage."""
    return shlex.quote(str(arg))
=======
def escape_shell_arg(arg: Any) -> str:
    """Quote a JSON-sourced value for the generated shell script.

    Applied to every value taken from the input JSON, numeric fields included:
    the script does not validate types, and shlex.quote leaves plain digits
    and identifiers unchanged, so valid input produces identical output.
    """
    return shlex.quote(str(arg))
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177


<<<<<<< HEAD
||||||| a86baef3b7
def _generate_global_basic_commands(config: Dict[str, Any]) -> List[str]:
=======
def _shell_bool(value: Any) -> str:
    return escape_shell_arg(str(value).lower())


>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
def _generate_global_basic_commands(config: dict[str, Any]) -> list[str]:
    """Generate basic global BGP commands."""
    commands = []
    if "router_id" in config:
        commands.append(
            f"config protocol bgp global router-id {escape_shell_arg(str(config['router_id']))}"
        )
    if "local_as_4_byte" in config:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global local-asn {config['local_as_4_byte']}"
||||||| a86baef3b7
            f"config protocol bgp global local-asn {escape_shell_arg(str(config['local_as_4_byte']))}"
=======
            f"config protocol bgp global local-asn {escape_shell_arg(config['local_as_4_byte'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "hold_time" in config:
<<<<<<< HEAD
        commands.append(f"config protocol bgp global hold-time {config['hold_time']}")
||||||| a86baef3b7
        commands.append(
            f"config protocol bgp global hold-time {escape_shell_arg(str(config['hold_time']))}"
        )
=======
        commands.append(
            f"config protocol bgp global hold-time {escape_shell_arg(config['hold_time'])}"
        )
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    if "local_confed_as_4_byte" in config:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global confed-asn {config['local_confed_as_4_byte']}"
||||||| a86baef3b7
            f"config protocol bgp global confed-asn {escape_shell_arg(str(config['local_confed_as_4_byte']))}"
        )
    if "cluster_id" in config:
        commands.append(
            f"config protocol bgp global cluster-id {escape_shell_arg(config['cluster_id'])}"
=======
            f"config protocol bgp global confed-asn {escape_shell_arg(config['local_confed_as_4_byte'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    return commands


def _generate_network6_commands(networks: list[dict[str, Any]]) -> list[str]:
    """Generate network6 commands for global BGP config."""
    commands = []
    for network in networks:
        prefix = network.get("prefix", "")
        if not prefix:
            continue
        cmd_parts = [f"config protocol bgp global network6 add {prefix}"]
        if "policy_name" in network:
            cmd_parts.append(f"policy {escape_shell_arg(network['policy_name'])}")
        if "install_to_fib" in network:
            cmd_parts.append(f"install-to-fib {_shell_bool(network['install_to_fib'])}")
        if "minimum_supporting_routes" in network:
<<<<<<< HEAD
            cmd_parts.append(f"min-routes {network['minimum_supporting_routes']}")
||||||| a86baef3b7
            cmd_parts.append(
                f"min-routes {escape_shell_arg(str(network['minimum_supporting_routes']))}"
            )
=======
            cmd_parts.append(
                f"min-routes {escape_shell_arg(network['minimum_supporting_routes'])}"
            )
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        commands.append(" ".join(cmd_parts))
    return commands


def _generate_switch_limit_commands(switch_limit: dict[str, Any]) -> list[str]:
    """Generate switch_limit_config commands."""
    commands = []
    if "prefix_limit" in switch_limit:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global switch-limit {switch_limit['prefix_limit']}"
||||||| a86baef3b7
            f"config protocol bgp global switch-limit {escape_shell_arg(str(switch_limit['prefix_limit']))}"
=======
            f"config protocol bgp global switch-limit {escape_shell_arg(switch_limit['prefix_limit'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "total_path_limit" in switch_limit:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global switch-limit-total-path {switch_limit['total_path_limit']}"
||||||| a86baef3b7
            f"config protocol bgp global switch-limit-total-path {escape_shell_arg(str(switch_limit['total_path_limit']))}"
=======
            f"config protocol bgp global switch-limit-total-path {escape_shell_arg(switch_limit['total_path_limit'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "max_golden_vips" in switch_limit:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global switch-limit-max-golden-vips {switch_limit['max_golden_vips']}"
||||||| a86baef3b7
            f"config protocol bgp global switch-limit-max-golden-vips {escape_shell_arg(str(switch_limit['max_golden_vips']))}"
=======
            f"config protocol bgp global switch-limit-max-golden-vips {escape_shell_arg(switch_limit['max_golden_vips'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "overload_protection_mode" in switch_limit:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp global switch-limit-overload-protection-mode {switch_limit['overload_protection_mode']}"
||||||| a86baef3b7
            f"config protocol bgp global switch-limit-overload-protection-mode {escape_shell_arg(str(switch_limit['overload_protection_mode']))}"
=======
            f"config protocol bgp global switch-limit-overload-protection-mode {escape_shell_arg(switch_limit['overload_protection_mode'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    return commands


def generate_global_commands(config: dict[str, Any]) -> list[str]:
    """Generate CLI commands for global BGP settings."""
    commands = []
    commands.extend(_generate_global_basic_commands(config))
    commands.extend(_generate_network6_commands(config.get("networks6", [])))
    commands.extend(
        _generate_switch_limit_commands(config.get("switch_limit_config", {}))
    )
    return commands


def _generate_peer_group_basic_commands(
    peer_group: dict[str, Any], escaped_name: str
) -> list[str]:
    """Generate basic peer-group commands (remote-asn, description, policies)."""
    commands = []
    if "remote_as_4_byte" in peer_group:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} remote-asn {peer_group['remote_as_4_byte']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} remote-asn {escape_shell_arg(str(peer_group['remote_as_4_byte']))}"
=======
            f"config protocol bgp peer-group {escaped_name} remote-asn {escape_shell_arg(peer_group['remote_as_4_byte'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "description" in peer_group:
        commands.append(
            f"config protocol bgp peer-group {escaped_name} description {escape_shell_arg(peer_group['description'])}"
        )
    if "ingress_policy_name" in peer_group:
        commands.append(
            f"config protocol bgp peer-group {escaped_name} ingress-policy {escape_shell_arg(peer_group['ingress_policy_name'])}"
        )
    if "egress_policy_name" in peer_group:
        commands.append(
            f"config protocol bgp peer-group {escaped_name} egress-policy {escape_shell_arg(peer_group['egress_policy_name'])}"
        )
    if "peer_tag" in peer_group:
        commands.append(
            f"config protocol bgp peer-group {escaped_name} peer-tag {escape_shell_arg(peer_group['peer_tag'])}"
        )
    return commands


def _generate_peer_group_bool_commands(
    peer_group: dict[str, Any], escaped_name: str
) -> list[str]:
    """Generate boolean flag commands for peer-group."""
    commands = []
    bool_fields = [
        ("is_rr_client", "rr-client"),
        ("next_hop_self", "next-hop-self"),
        ("is_confed_peer", "confed-peer"),
        ("v4_over_v6_nexthop", "v4-over-v6-nh"),
        ("disable_ipv4_afi", "disable-ipv4-afi"),
    ]
    for field, cli_name in bool_fields:
        if field in peer_group:
            commands.append(
                f"config protocol bgp peer-group {escaped_name} {cli_name} {_shell_bool(peer_group[field])}"
            )
    return commands


def _generate_peer_group_timer_commands(
    timers: dict[str, Any], escaped_name: str
) -> list[str]:
    """Generate timer commands for peer-group."""
    commands = []
    if timers.get("hold_time_seconds"):
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} timers hold-time {timers['hold_time_seconds']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} timers hold-time {escape_shell_arg(str(timers['hold_time_seconds']))}"
=======
            f"config protocol bgp peer-group {escaped_name} timers hold-time {escape_shell_arg(timers['hold_time_seconds'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if timers.get("keep_alive_seconds"):
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} timers keepalive {timers['keep_alive_seconds']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} timers keepalive {escape_shell_arg(str(timers['keep_alive_seconds']))}"
=======
            f"config protocol bgp peer-group {escaped_name} timers keepalive {escape_shell_arg(timers['keep_alive_seconds'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "out_delay_seconds" in timers:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} timers out-delay {timers['out_delay_seconds']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} timers out-delay {escape_shell_arg(str(timers['out_delay_seconds']))}"
=======
            f"config protocol bgp peer-group {escaped_name} timers out-delay {escape_shell_arg(timers['out_delay_seconds'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "withdraw_unprog_delay_seconds" in timers:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} timers withdraw-unprog-delay {timers['withdraw_unprog_delay_seconds']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} timers withdraw-unprog-delay {escape_shell_arg(str(timers['withdraw_unprog_delay_seconds']))}"
=======
            f"config protocol bgp peer-group {escaped_name} timers withdraw-unprog-delay {escape_shell_arg(timers['withdraw_unprog_delay_seconds'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    return commands


def _generate_peer_group_prefilter_commands(
    pre_filter: dict[str, Any], escaped_name: str
) -> list[str]:
    """Generate pre_filter commands for peer-group."""
    commands = []
    if pre_filter.get("max_routes"):
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} max-routes {pre_filter['max_routes']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} max-routes {escape_shell_arg(str(pre_filter['max_routes']))}"
=======
            f"config protocol bgp peer-group {escaped_name} max-routes {escape_shell_arg(pre_filter['max_routes'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "warning_limit" in pre_filter:
        commands.append(
<<<<<<< HEAD
            f"config protocol bgp peer-group {escaped_name} warning-limit {pre_filter['warning_limit']}"
||||||| a86baef3b7
            f"config protocol bgp peer-group {escaped_name} warning-limit {escape_shell_arg(str(pre_filter['warning_limit']))}"
=======
            f"config protocol bgp peer-group {escaped_name} warning-limit {escape_shell_arg(pre_filter['warning_limit'])}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        )
    if "warning_only" in pre_filter:
        commands.append(
            f"config protocol bgp peer-group {escaped_name} warning-only {_shell_bool(pre_filter['warning_only'])}"
        )
    return commands


def generate_peer_group_commands(peer_group: dict[str, Any]) -> list[str]:
    """Generate CLI commands for a peer group."""
    name = peer_group.get("name", "")
    if not name:
        return []

    escaped_name = escape_shell_arg(name)
    commands = []
    commands.extend(_generate_peer_group_basic_commands(peer_group, escaped_name))
    commands.extend(_generate_peer_group_bool_commands(peer_group, escaped_name))
    commands.extend(
        _generate_peer_group_timer_commands(
            peer_group.get("bgp_peer_timers", {}), escaped_name
        )
    )
    commands.extend(
        _generate_peer_group_prefilter_commands(
            peer_group.get("pre_filter", {}), escaped_name
        )
    )
    return commands


def format_bandwidth(bps: int) -> str:
<<<<<<< HEAD
    """Format bandwidth in bps to human-readable format (e.g., 10G)."""
    if bps >= 1_000_000_000_000 and bps % 1_000_000_000_000 == 0:
        return f"{bps // 1_000_000_000_000}T"
||||||| a86baef3b7
    """Format bandwidth in bps to human-readable format (e.g., 10G)."""
    if bps >= 1_000_000_000_000 and bps % 1_000_000_000_000 == 0:
        return f"{bps // 1_000_000_000_000}T"
    elif bps >= 1_000_000_000 and bps % 1_000_000_000 == 0:
=======
    """Format bandwidth in bps with the largest exact K/M/G suffix.

    Only K, M and G are emitted: those are the multipliers bgpd's
    link-bandwidth parser accepts, so a "T" spelling would not round-trip.
    """
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    if bps >= 1_000_000_000 and bps % 1_000_000_000 == 0:
        return f"{bps // 1_000_000_000}G"
    if bps >= 1_000_000 and bps % 1_000_000 == 0:
        return f"{bps // 1_000_000}M"
    if bps >= 1_000 and bps % 1_000 == 0:
        return f"{bps // 1_000}K"
    return str(bps)


<<<<<<< HEAD
# (json field, CLI attribute, escape as free-form shell arg) — fields whose
# value maps 1:1 onto a neighbor attribute token.
_NEIGHBOR_SCALAR_FIELDS = [
    ("remote_as_4_byte", "remote-asn", False),
    ("local_as_4_byte", "local-asn", False),
    ("peer_group_name", "peer-group", True),
    ("description", "description", True),
    ("peer_tag", "peer-tag", True),
    ("local_addr", "bind-addr address", True),
    ("ingress_policy_name", "ingress-policy", True),
    ("egress_policy_name", "egress-policy", True),
    ("next_hop4", "next-hop4", True),
    ("next_hop6", "next-hop6", True),
    ("peer_id", "peer-id", True),
    ("type", "type", True),
]
||||||| a86baef3b7
def _generate_peer_basic_commands(peer: Dict[str, Any], peer_addr: str) -> List[str]:
    """Generate basic peer commands (remote-asn, peer-group, description, etc.)."""
    commands = []
    if "remote_as_4_byte" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} remote-asn {escape_shell_arg(str(peer['remote_as_4_byte']))}"
        )
    if "peer_group_name" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} peer-group {escape_shell_arg(peer['peer_group_name'])}"
        )
    if "description" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} description {escape_shell_arg(peer['description'])}"
        )
    if "local_addr" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} local-addr {escape_shell_arg(peer['local_addr'])}"
        )
    if "ingress_policy_name" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} ingress-policy {escape_shell_arg(peer['ingress_policy_name'])}"
        )
    if "egress_policy_name" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} egress-policy {escape_shell_arg(peer['egress_policy_name'])}"
        )
    return commands
=======
def _printable(text: Any) -> str:
    """A JSON-sourced name made safe for a `#` comment line: no control
    characters, so it cannot break out of the comment."""
    return "".join(ch if ch.isprintable() else "?" for ch in str(text))


# ---------------------------------------------------------------------------
# Fields BgpPeer and PeerGroup share. The neighbor and peer-group dispatchers
# spell these attributes identically, so one table drives both generators.
# ---------------------------------------------------------------------------

# (json field, CLI attribute) — boolean flags.
_BOOL_FIELDS = [
    ("is_rr_client", "rr-client"),
    ("is_confed_peer", "confed-peer"),
    ("is_redistribute_peer", "redistribute-peer"),
    ("enhanced_route_refresh", "enhanced-route-refresh"),
    ("route_refresh", "route-refresh"),
    ("remove_private_as", "remove-private-as"),
    ("enforce_first_as", "enforce-first-as"),
    ("disable_ipv4_afi", "afi disable-ipv4-afi"),
    ("disable_ipv6_afi", "afi disable-ipv6-afi"),
    ("v4_over_v6_nexthop", "afi ipv4-over-ipv6-nh"),
    ("enable_stateful_ha", "graceful-restart stateful-ha"),
    ("next_hop_self", "next-hop-self"),
]

# (json field, CLI attribute) — integer-valued attributes.
_INT_FIELDS = [("ttl_security_hops", "ttl-security-hops")]

_TIMER_FIELDS = [
    ("hold_time_seconds", "timers hold-time"),
    ("keep_alive_seconds", "timers keepalive"),
    ("out_delay_seconds", "timers out-delay"),
    ("withdraw_unprog_delay_seconds", "timers withdraw-unprog-delay"),
    ("graceful_restart_seconds", "graceful-restart restart-time"),
]

# RouteLimit leaves, as (json field, attribute suffix, is_bool); the prefix is
# `max-route pre-` or `max-route post-`.
_ROUTE_LIMIT_FIELDS = [
    ("max_routes", "filter", False),
    ("warning_limit", "warning-threshold", False),
    ("warning_only", "warning-only", True),
]

# Every shared key the generators below convert. Anything else present on the
# JSON object is reported (see _unconverted_field_warnings) instead of being
# dropped silently.
_SHARED_HANDLED_FIELDS = (
    {
        "is_passive",
        "link_bandwidth_bps",
        "advertise_link_bandwidth",
        "receive_link_bandwidth",
        "add_path",
        "bgp_peer_timers",
        "pre_filter",
        "post_filter",
    }
    | {field for field, _ in _BOOL_FIELDS}
    | {field for field, _ in _INT_FIELDS}
)
_TIMER_HANDLED_FIELDS = {field for field, _ in _TIMER_FIELDS}
_ROUTE_LIMIT_HANDLED_FIELDS = {field for field, _, _ in _ROUTE_LIMIT_FIELDS}


def _generate_scalar_commands(
    obj: dict[str, Any], prefix: str, fields: list[tuple[str, str]]
) -> list[str]:
    """Generate `<prefix> <attribute> <value>` for each present scalar field."""
    commands = []
    for field, cli_name in fields:
        if field in obj:
            commands.append(f"{prefix} {cli_name} {escape_shell_arg(obj[field])}")
    return commands
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177


<<<<<<< HEAD
def _generate_neighbor_basic_commands(peer: dict[str, Any], prefix: str) -> list[str]:
    """Generate scalar neighbor commands (ASNs, names, policies, addresses)."""
||||||| a86baef3b7
def _generate_peer_bool_commands(peer: Dict[str, Any], peer_addr: str) -> List[str]:
    """Generate boolean flag commands for peer."""
=======
def _generate_bool_commands(obj: dict[str, Any], prefix: str) -> list[str]:
    """Generate boolean flag commands for a neighbor or peer group."""
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    commands = []
<<<<<<< HEAD
    for field, cli_name, escape in _NEIGHBOR_SCALAR_FIELDS:
        if field in peer:
            value = escape_shell_arg(str(peer[field])) if escape else peer[field]
            commands.append(f"{prefix} {cli_name} {value}")
    if "is_passive" in peer:
        mode = "PASSIVE" if peer["is_passive"] else "ACTIVE"
        commands.append(f"{prefix} connect-mode {mode}")
    if "link_bandwidth_bps" in peer:
        bw = peer["link_bandwidth_bps"]
||||||| a86baef3b7
    bool_fields = [
        ("is_passive", "passive"),
        ("is_rr_client", "rr-client"),
        ("next_hop_self", "next-hop-self"),
        ("v4_over_v6_nexthop", "v4-over-v6-nh"),
        ("disable_ipv4_afi", "disable-ipv4-afi"),
        ("advertise_link_bandwidth", "advertise-lbw"),
    ]
    for field, cli_name in bool_fields:
        if field in peer:
            commands.append(
                f"config protocol bgp peer {peer_addr} {cli_name} {str(peer[field]).lower()}"
            )
    return commands


def _generate_peer_nexthop_commands(peer: Dict[str, Any], peer_addr: str) -> List[str]:
    """Generate next-hop and link-bandwidth commands for peer."""
    commands = []
    if "next_hop4" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} next-hop4 {escape_shell_arg(peer['next_hop4'])}"
        )
    if "next_hop6" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} next-hop6 {escape_shell_arg(peer['next_hop6'])}"
        )
    if "link_bandwidth_bps" in peer:
        bw = peer["link_bandwidth_bps"]
=======
    for field, cli_name in _BOOL_FIELDS:
        if field in obj:
            commands.append(f"{prefix} {cli_name} {_shell_bool(obj[field])}")
    return commands


def _generate_link_bandwidth_commands(obj: dict[str, Any], prefix: str) -> list[str]:
    """Generate the link-bandwidth trio for a neighbor or peer group.

    advertise/receive enum values are passed through as found (name or
    integer): the dispatchers accept both spellings for a thrift enum.
    """
    commands = []
    if "link_bandwidth_bps" in obj:
        bw = obj["link_bandwidth_bps"]
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
        bw_str = format_bandwidth(bw) if isinstance(bw, int) else str(bw)
<<<<<<< HEAD
        commands.append(f"{prefix} link-bandwidth {bw_str}")
    if "advertise_link_bandwidth" in peer:
        commands.append(f"{prefix} advertise-lbw {peer['advertise_link_bandwidth']}")
    if "receive_link_bandwidth" in peer:
        commands.append(f"{prefix} receive-lbw {peer['receive_link_bandwidth']}")
||||||| a86baef3b7
        commands.append(
            f"config protocol bgp peer {peer_addr} link-bandwidth {escape_shell_arg(bw_str)}"
        )
=======
        commands.append(f"{prefix} link-bandwidth {escape_shell_arg(bw_str)}")
    if "advertise_link_bandwidth" in obj:
        commands.append(
            f"{prefix} advertise-lbw {escape_shell_arg(obj['advertise_link_bandwidth'])}"
        )
    if "receive_link_bandwidth" in obj:
        commands.append(
            f"{prefix} receive-lbw {escape_shell_arg(obj['receive_link_bandwidth'])}"
        )
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    return commands


<<<<<<< HEAD
def _generate_neighbor_bool_commands(peer: dict[str, Any], prefix: str) -> list[str]:
    """Generate boolean flag commands for a neighbor."""
||||||| a86baef3b7
def _generate_peer_timer_commands(timers: Dict[str, Any], peer_addr: str) -> List[str]:
    """Generate timer commands for peer."""
=======
def _generate_add_path_commands(obj: dict[str, Any], prefix: str) -> list[str]:
    """Generate add-path commands from the AddPath enum (RECEIVE=1, SEND=2, BOTH=3)."""
    if "add_path" not in obj:
        return []
    raw = obj["add_path"]
    value = (
        {"RECEIVE": 1, "SEND": 2, "BOTH": 3}.get(raw, raw)
        if isinstance(raw, str)
        else raw
    )
    value = int(value)
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    commands = []
<<<<<<< HEAD
    bool_fields = [
        ("is_rr_client", "rr-client"),
        ("is_confed_peer", "confed-peer"),
        ("is_redistribute_peer", "redistribute-peer"),
        ("enhanced_route_refresh", "enhanced-route-refresh"),
        ("disable_ipv4_afi", "afi disable-ipv4-afi"),
        ("disable_ipv6_afi", "afi disable-ipv6-afi"),
        ("v4_over_v6_nexthop", "afi ipv4-over-ipv6-nh"),
        ("enable_stateful_ha", "graceful-restart stateful-ha"),
        ("next_hop_self", "next-hop-self"),
    ]
    for field, cli_name in bool_fields:
        if field in peer:
            commands.append(f"{prefix} {cli_name} {str(peer[field]).lower()}")
    return commands


def _generate_neighbor_add_path_commands(
    peer: dict[str, Any], prefix: str
) -> list[str]:
    """Generate add-path commands from the AddPath enum (RECEIVE=1, SEND=2, BOTH=3)."""
    if "add_path" not in peer:
        return []
    raw = peer["add_path"]
    value = (
        {"RECEIVE": 1, "SEND": 2, "BOTH": 3}.get(raw, raw)
        if isinstance(raw, str)
        else raw
    )
    value = int(value)
    commands = []
    if value & 1:
        commands.append(f"{prefix} add-path receive true")
    if value & 2:
        commands.append(f"{prefix} add-path send true")
    return commands


def _generate_neighbor_timer_commands(timers: dict[str, Any], prefix: str) -> list[str]:
    """Generate timer and graceful-restart commands for a neighbor."""
    commands = []
    if "hold_time_seconds" in timers:
        commands.append(f"{prefix} timers hold-time {timers['hold_time_seconds']}")
    if "keep_alive_seconds" in timers:
        commands.append(f"{prefix} timers keepalive {timers['keep_alive_seconds']}")
    if "out_delay_seconds" in timers:
        commands.append(f"{prefix} timers out-delay {timers['out_delay_seconds']}")
    if "withdraw_unprog_delay_seconds" in timers:
        commands.append(
            f"{prefix} timers withdraw-unprog-delay {timers['withdraw_unprog_delay_seconds']}"
        )
    if "graceful_restart_seconds" in timers:
        commands.append(
            f"{prefix} graceful-restart restart-time {timers['graceful_restart_seconds']}"
        )
||||||| a86baef3b7
    if timers.get("hold_time_seconds"):
        commands.append(
            f"config protocol bgp peer {peer_addr} hold-time {escape_shell_arg(str(timers['hold_time_seconds']))}"
        )
    if timers.get("keep_alive_seconds"):
        commands.append(
            f"config protocol bgp peer {peer_addr} timers keepalive {escape_shell_arg(str(timers['keep_alive_seconds']))}"
        )
    if "out_delay_seconds" in timers:
        commands.append(
            f"config protocol bgp peer {peer_addr} timers out-delay {escape_shell_arg(str(timers['out_delay_seconds']))}"
        )
    if "withdraw_unprog_delay_seconds" in timers:
        commands.append(
            f"config protocol bgp peer {peer_addr} timers withdraw-unprog-delay {escape_shell_arg(str(timers['withdraw_unprog_delay_seconds']))}"
        )
=======
    if value & 1:
        commands.append(f"{prefix} add-path receive true")
    if value & 2:
        commands.append(f"{prefix} add-path send true")
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    return commands


<<<<<<< HEAD
def _generate_neighbor_route_limit_commands(
    peer: dict[str, Any], prefix: str
) -> list[str]:
||||||| a86baef3b7
def _generate_peer_prefilter_commands(
    pre_filter: Dict[str, Any], peer_addr: str
) -> List[str]:
    """Generate pre_filter commands for peer."""
=======
def _generate_timer_commands(timers: dict[str, Any], prefix: str) -> list[str]:
    """Generate timer and graceful-restart commands for a neighbor or peer group."""
    return _generate_scalar_commands(timers, prefix, _TIMER_FIELDS)


def _generate_route_limit_commands(obj: dict[str, Any], prefix: str) -> list[str]:
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    """Generate max-route commands from pre_filter/post_filter."""
    commands = []
<<<<<<< HEAD
    pre_filter = peer.get("pre_filter", {})
    if "max_routes" in pre_filter:
        commands.append(f"{prefix} max-route pre-filter {pre_filter['max_routes']}")
    if "warning_limit" in pre_filter:
        commands.append(
            f"{prefix} max-route pre-warning-threshold {pre_filter['warning_limit']}"
        )
    if "warning_only" in pre_filter:
        commands.append(
            f"{prefix} max-route pre-warning-only {str(pre_filter['warning_only']).lower()}"
        )
    post_filter = peer.get("post_filter", {})
    if "max_routes" in post_filter:
        commands.append(f"{prefix} max-route post-filter {post_filter['max_routes']}")
    if "warning_limit" in post_filter:
        commands.append(
            f"{prefix} max-route post-warning-threshold {post_filter['warning_limit']}"
        )
    if "warning_only" in post_filter:
        commands.append(
            f"{prefix} max-route post-warning-only {str(post_filter['warning_only']).lower()}"
        )
||||||| a86baef3b7
    if pre_filter.get("max_routes"):
        commands.append(
            f"config protocol bgp peer {peer_addr} max-routes {escape_shell_arg(str(pre_filter['max_routes']))}"
        )
    if "warning_limit" in pre_filter:
        commands.append(
            f"config protocol bgp peer {peer_addr} warning-limit {escape_shell_arg(str(pre_filter['warning_limit']))}"
        )
    if "warning_only" in pre_filter:
        commands.append(
            f"config protocol bgp peer {peer_addr} warning-only {str(pre_filter['warning_only']).lower()}"
        )
=======
    for struct, side in (("pre_filter", "pre"), ("post_filter", "post")):
        limit = obj.get(struct, {})
        for field, suffix, is_bool in _ROUTE_LIMIT_FIELDS:
            if field in limit:
                value = (
                    _shell_bool(limit[field])
                    if is_bool
                    else escape_shell_arg(limit[field])
                )
                commands.append(f"{prefix} max-route {side}-{suffix} {value}")
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    return commands


<<<<<<< HEAD
||||||| a86baef3b7
def _generate_peer_id_commands(peer: Dict[str, Any], peer_addr: str) -> List[str]:
    """Generate peer identification commands."""
    commands = []
    if "peer_id" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} peer-id {escape_shell_arg(peer['peer_id'])}"
        )
    if "type" in peer:
        commands.append(
            f"config protocol bgp peer {peer_addr} type {escape_shell_arg(peer['type'])}"
        )
    return commands


def generate_peer_commands(peer: Dict[str, Any]) -> List[str]:
    """Generate CLI commands for a peer."""
=======
def _generate_session_commands(obj: dict[str, Any], prefix: str) -> list[str]:
    """Generate the commands for every field BgpPeer and PeerGroup share."""
    commands = []
    if "is_passive" in obj:
        commands.append(f"{prefix} passive {_shell_bool(obj['is_passive'])}")
    commands.extend(_generate_bool_commands(obj, prefix))
    commands.extend(_generate_scalar_commands(obj, prefix, _INT_FIELDS))
    commands.extend(_generate_link_bandwidth_commands(obj, prefix))
    commands.extend(_generate_add_path_commands(obj, prefix))
    commands.extend(_generate_timer_commands(obj.get("bgp_peer_timers", {}), prefix))
    commands.extend(_generate_route_limit_commands(obj, prefix))
    return commands


def _unconverted_field_warnings(
    obj: dict[str, Any], handled: set[str], subject: str
) -> list[str]:
    """One `# WARNING` comment line per JSON field no generator converts.

    The dispatchers only expose the fields bgpd reads at that level, so a
    field left here is either dead in the daemon or per-peer-only; either
    way the operator must see it was not carried over.
    """
    warnings = []

    def warn(field: str) -> None:
        warnings.append(
            f"# WARNING: {subject}: field {_printable(field)} has no CLI "
            "equivalent, not converted"
        )

    for field in obj:
        if field not in handled:
            warn(field)
    for field in obj.get("bgp_peer_timers", {}):
        if field not in _TIMER_HANDLED_FIELDS:
            warn(f"bgp_peer_timers.{field}")
    for struct in ("pre_filter", "post_filter"):
        for field in obj.get(struct, {}):
            if field not in _ROUTE_LIMIT_HANDLED_FIELDS:
                warn(f"{struct}.{field}")
    return warnings


# (json field, CLI attribute) — BgpPeer-only fields whose value maps 1:1 onto
# a neighbor attribute token. The deprecated i32 ASNs are converted to the
# 4-byte attribute: bgpd reads either representation and the CLI stores the
# 4-byte field.
_NEIGHBOR_SCALAR_FIELDS = [
    ("remote_as_4_byte", "remote-asn"),
    ("remote_as", "remote-asn"),
    ("local_as_4_byte", "local-asn"),
    ("local_as", "local-asn"),
    ("peer_group_name", "peer-group"),
    ("description", "description"),
    ("peer_tag", "peer-tag"),
    ("local_addr", "bind-addr address"),
    ("ingress_policy_name", "ingress-policy"),
    ("egress_policy_name", "egress-policy"),
    ("next_hop4", "next-hop4"),
    ("next_hop6", "next-hop6"),
    ("peer_id", "peer-id"),
    ("type", "type"),
]

_NEIGHBOR_HANDLED_FIELDS = (
    {"peer_addr"}
    | {field for field, _ in _NEIGHBOR_SCALAR_FIELDS}
    | _SHARED_HANDLED_FIELDS
)


>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
def generate_peer_commands(peer: dict[str, Any]) -> list[str]:
    """Generate `config protocol bgp neighbor` CLI commands for a peer."""
    peer_addr = peer.get("peer_addr", "")
    if not peer_addr:
        return []

    prefix = f"config protocol bgp neighbor {escape_shell_arg(peer_addr)}"
<<<<<<< HEAD
    commands = []
    commands.extend(_generate_neighbor_basic_commands(peer, prefix))
    commands.extend(_generate_neighbor_bool_commands(peer, prefix))
    commands.extend(_generate_neighbor_add_path_commands(peer, prefix))
    commands.extend(
        _generate_neighbor_timer_commands(peer.get("bgp_peer_timers", {}), prefix)
||||||| a86baef3b7
    escaped_peer_addr = escape_shell_arg(peer_addr)
    commands = []
    commands.extend(_generate_peer_basic_commands(peer, escaped_peer_addr))
    commands.extend(_generate_peer_bool_commands(peer, escaped_peer_addr))
    commands.extend(_generate_peer_nexthop_commands(peer, escaped_peer_addr))
    commands.extend(
        _generate_peer_timer_commands(
            peer.get("bgp_peer_timers", {}), escaped_peer_addr
        )
=======
    commands = _unconverted_field_warnings(
        peer, _NEIGHBOR_HANDLED_FIELDS, f"neighbor {_printable(peer_addr)}"
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    )
<<<<<<< HEAD
    commands.extend(_generate_neighbor_route_limit_commands(peer, prefix))
||||||| a86baef3b7
    commands.extend(
        _generate_peer_prefilter_commands(peer.get("pre_filter", {}), escaped_peer_addr)
    )
    commands.extend(_generate_peer_id_commands(peer, escaped_peer_addr))
=======
    commands.extend(_generate_scalar_commands(peer, prefix, _NEIGHBOR_SCALAR_FIELDS))
    commands.extend(_generate_session_commands(peer, prefix))
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    return commands


def generate_exec_commands(commands: list[str], binary: str = "fboss2") -> list[str]:
    """Generate executable commands with custom binary."""
    exec_commands = [
        "#!/bin/bash",
        "# BGP configuration script generated by j2c",
        "# This script runs in normal mode (writes to ~/.fboss2/bgp_config.json)",
        "",
        "set -e  # Exit on first error",
        "",
    ]
    for cmd in commands:
        exec_commands.append(cmd if cmd.startswith("#") else f"{binary} {cmd}")

    exec_commands.extend(
        [
            "",
            "echo ''",
            "echo 'BGP configuration complete!'",
            "echo 'Config saved to: ~/.fboss2/bgp_config.json'",
        ]
    )
    return exec_commands


<<<<<<< HEAD
def json_to_cli(config: dict[str, Any], binary: str = "fboss2") -> list[str]:
    """Convert BGP++ JSON config to CLI commands."""
||||||| a86baef3b7
def json_to_cli(
    config: Dict[str, Any], stub: bool = False, binary: str = "fboss2"
) -> List[str]:
    """Convert BGP++ JSON config to CLI commands."""
=======
def generate_commands(config: dict[str, Any]) -> list[str]:
    """Convert BGP++ JSON config to raw CLI commands (plus `#` warning lines
    for fields that have no CLI equivalent)."""
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
    commands = []
    commands.extend(generate_global_commands(config))
    for peer_group in config.get("peer_groups", []):
        commands.extend(generate_peer_group_commands(peer_group))
    for peer in config.get("peers", []):
        commands.extend(generate_peer_commands(peer))
    return commands

<<<<<<< HEAD
    return generate_exec_commands(commands, binary)
||||||| a86baef3b7
    if stub:
        return generate_stub_commands(commands, binary)

    return generate_exec_commands(commands, binary)
=======

def json_to_cli(config: dict[str, Any], binary: str = "fboss2") -> list[str]:
    """Convert BGP++ JSON config to an executable CLI script."""
    return generate_exec_commands(generate_commands(config), binary)
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert BGP++ JSON configuration to fboss2 CLI commands"
    )
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument(
        "--output", "-o", help="Output file (default: stdout)", default=None
    )
    parser.add_argument(
        "--binary",
        "-b",
        default="fboss2",
        help="Binary name or path (default: fboss2). Use full path for buck run output.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw CLI commands only (no shell script wrapper)",
    )
    args = parser.parse_args()

    try:
        with open(args.input) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input}': {e}", file=sys.stderr)
        return 1

<<<<<<< HEAD
    if args.raw:
        # Generate raw CLI commands only (no shell wrapper)
        commands = []
        commands.extend(generate_global_commands(config))
        for peer_group in config.get("peer_groups", []):
            commands.extend(generate_peer_group_commands(peer_group))
        for peer in config.get("peers", []):
            commands.extend(generate_peer_commands(peer))
        output = "\n".join(commands)
    else:
        commands = json_to_cli(config, binary=args.binary)
        output = "\n".join(commands)
||||||| a86baef3b7
    if args.raw:
        # Generate raw CLI commands only (no shell wrapper)
        commands = []
        commands.extend(generate_global_commands(config))
        for peer_group in config.get("peer_groups", []):
            commands.extend(generate_peer_group_commands(peer_group))
        for peer in config.get("peers", []):
            commands.extend(generate_peer_commands(peer))
        output = "\n".join(commands)
    else:
        commands = json_to_cli(config, stub=args.stub, binary=args.binary)
        output = "\n".join(commands)
=======
    commands = generate_commands(config)
    # Fields with no CLI equivalent are flagged in the script AND on stderr,
    # so a scripted conversion cannot lose them silently.
    for line in commands:
        if line.startswith("# WARNING"):
            print(line[2:], file=sys.stderr)
    if not args.raw:
        commands = generate_exec_commands(commands, args.binary)
    output = "\n".join(commands)
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177

    if args.output:
        with open(args.output, "w") as f:
            f.write(output + "\n")
        print(f"Generated {len(commands)} commands to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
