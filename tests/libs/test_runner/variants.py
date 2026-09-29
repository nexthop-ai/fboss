"""Speed/breakout variant vocabulary and per-pair resolution for the link and
qsfp hardware tests.

A variant names one uniform front-panel configuration for a run: ``max`` is
today's single-subport maximum-speed configuration, ``2x400G``/``4x200G``/...
are electrical breakouts of the cage. The chain of valid variants is derived
from the platform's own mapping rather than hardcoded. Resolution is
per snake pair: a pair that cannot support the requested variant is excluded
from the generated configuration (never reconfigured to max) with a reason of
``platform``, ``module`` or ``peer``. ``module`` means the transceiver does not
advertise a CMIS application at the subport speed over the subport's host lanes.
A cage also resolves on its own, for the qsfp tests, where ``peer`` does not apply.
"""

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from tests.libs.test_runner.platform_mapping import (
    _MAX_PROFILE_SPEED_MBPS,
    _platform_mapping_path,
    _profile_medium_by_id,
)

logger = logging.getLogger("test_runner")

# Electrical breakout stops at 8-way regardless of platform maximum speed.
_BREAKOUT_FACTORS = (2, 4, 8)

_VARIANT_RE = re.compile(r"^(\d+)x(\d+)([GT])$", re.IGNORECASE)


class VariantError(ValueError):
    """A malformed or unsupported variant request."""


class VariantNotApplicable(Exception):
    """This DUT cannot run the requested variant.

    Raise only before the pass loop starts: once a pass has run, its results
    have to survive.
    """


@dataclass(frozen=True)
class Variant:
    name: str
    factor: int
    # None for max: each port keeps its own maximum-speed profile.
    speed_mbps: int | None

    @property
    def is_max(self) -> bool:
        return self.speed_mbps is None


MAX_VARIANT = Variant(name="max", factor=1, speed_mbps=None)

# One advertised CMIS application as the host sees it: (aggregate speed in Mbps,
# host lane count), from TEST_PORTS_INFO ``host_apps``.
HostApp = tuple[int, int]


def format_host_apps(apps: list[HostApp]) -> str:
    return ", ".join(f"{speed // 1000}Gx{lanes}" for speed, lanes in apps)


def parse_variant(value: str, chain: list[Variant]) -> Variant:
    """Parse a requested variant against the platform's derived chain.

    Anything outside the chain raises VariantError naming the supported
    variants; callers separate typo from unsupported via `is_well_formed`.
    """
    by_name = {v.name.lower(): v for v in chain}
    variant = by_name.get(value.strip().lower())
    if variant is None:
        supported = ", ".join(v.name for v in chain)
        raise VariantError(f"unsupported variant {value!r}; supported: {supported}")
    return variant


def is_well_formed(value: str) -> bool:
    """Whether the string is variant-shaped (max or NxMG/NxMT), regardless of
    platform support."""
    if value.strip().lower() == "max":
        return True
    return _VARIANT_RE.match(value.strip()) is not None


@dataclass(frozen=True)
class SubportInfo:
    logical_id: int
    # profile id -> (speed in Mbps, iphy lane count)
    profiles: dict[int, tuple[int, int]]


@dataclass(frozen=True)
class CageInfo:
    controlling: str  # controlling port name, e.g. "eth1/2/1"
    lanes: int  # iphy lanes in the cage
    subports: dict[int, SubportInfo]  # subport index (1-based) -> info


def load_full_platform_mapping(config_name: str) -> dict[str, CageInfo]:
    """Per-cage view of the platform mapping, keeping every subport row and
    each profile's speed and lane count (which variant resolution needs and
    load_platform_mapping drops). A missing subport row means unsupported.
    """
    path = _platform_mapping_path(config_name)
    with open(path, encoding="utf-8") as f:
        mapping = json.load(f)
    prof = {
        int(p["factor"]["profileID"]): (p["profile"]["speed"], p["profile"]["iphy"]["numLanes"])
        for p in mapping["platformSupportedProfiles"]
        if p["profile"]["speed"] <= _MAX_PROFILE_SPEED_MBPS
    }
    cages: dict[str, dict[int, SubportInfo]] = {}
    lanes: dict[str, int] = {}
    for entry in mapping["ports"].values():
        name = entry["mapping"]["name"]
        if not name.startswith("eth"):
            continue
        parts = name.split("/")
        if len(parts) != 3:
            continue
        cage, sub = "/".join(parts[:2]), int(parts[2])
        profiles = {int(pid): prof[int(pid)] for pid in entry["supportedProfiles"] if int(pid) in prof}
        if not profiles:
            continue
        cages.setdefault(cage, {})[sub] = SubportInfo(entry["mapping"]["id"], profiles)
        if sub == 1:
            lanes[cage] = len(entry["mapping"].get("pins", []))
    return {
        cage: CageInfo(controlling=f"{cage}/1", lanes=lanes.get(cage, 0), subports=subports)
        for cage, subports in cages.items()
        if 1 in subports and lanes.get(cage, 0) > 0
    }


@dataclass
class PairResolution:
    ok: bool
    reason: str | None = None  # "platform" | "module" | "peer"
    detail: str = ""
    # (subport on port's cage, subport at the same lane offset on peer's cage)
    subport_pairs: list[tuple[str, str]] = field(default_factory=list)
    profile_by_port: dict[str, int] = field(default_factory=dict)


def cage_of(port_name: str) -> str:
    """Transceiver cage a port name belongs to: eth1/25/5 -> eth1/25."""
    parts = port_name.split("/")
    return "/".join(parts[:2]) if len(parts) >= 3 else port_name


def _active_subports(cage: CageInfo, factor: int) -> list[int] | None:
    """1 + i*L/k for i in 0..k-1, or None when the cage's lane count cannot
    split k ways."""
    if factor > cage.lanes or cage.lanes % factor:
        return None
    step = cage.lanes // factor
    return [1 + i * step for i in range(factor)]


def derive_variant_chain(cages: Mapping[str, CageInfo]) -> list[Variant]:
    """max plus every breakout this platform's mapping can program.

    A variant is offered when some cage has, at every subport its factor
    activates, a profile at that speed over exactly lanes/factor lanes.
    """
    offered: set[tuple[int, int]] = set()
    for cage in cages.values():
        for factor in _BREAKOUT_FACTORS:
            subs = _active_subports(cage, factor)
            if subs is None or any(sub not in cage.subports for sub in subs):
                continue
            lanes = cage.lanes // factor
            per_subport = [
                {speed for speed, nlanes in cage.subports[sub].profiles.values() if nlanes == lanes}
                for sub in subs
            ]
            offered.update((factor, speed) for speed in set.intersection(*per_subport))
    return [MAX_VARIANT] + [
        Variant(name=f"{factor}x{speed // 1000}G", factor=factor, speed_mbps=speed)
        for factor, speed in sorted(offered, key=lambda fs: (fs[0], -fs[1]))
    ]


def _cage_profile(
    cage_name: str,
    cage: CageInfo,
    variant: Variant,
    is_copper: bool | None,
) -> tuple[int | None, list[int], str]:
    """The profile id every active subport of this cage would use plus the
    active subport indexes, or (None, [], why-not). All checks here classify
    as reason ``platform``."""
    subs = _active_subports(cage, variant.factor)
    if subs is None:
        return None, [], f"{cage_name}: {cage.lanes} lanes cannot split {variant.factor} ways"
    lanes_per_subport = cage.lanes // variant.factor
    want = None if is_copper is None else ("copper" if is_copper else "optical")
    medium = _profile_medium_by_id() if want is not None else {}
    chosen: int | None = None
    for sub in subs:
        info = cage.subports.get(sub)
        if info is None:
            return None, [], f"{cage_name}/{sub} is not in the platform mapping"
        candidates = [
            pid
            for pid, (speed, nlanes) in info.profiles.items()
            if speed == variant.speed_mbps and nlanes == lanes_per_subport
        ]
        if want is not None:
            matching = [pid for pid in candidates if medium.get(pid) == want]
            # A cabled optical module can still use a medium-unclassified
            # profile; copper cannot fall back to an optical one.
            candidates = matching if matching or want == "copper" else candidates
        if not candidates:
            return None, [], (
                f"{cage_name}/{sub} has no {want or 'any'}-medium profile at "
                f"{variant.speed_mbps} Mbps over {lanes_per_subport} lanes"
            )
        pid = max(candidates)
        if chosen is None:
            chosen = pid
        elif pid != chosen:
            return None, [], f"{cage_name} subports resolve to different profiles ({chosen} vs {pid})"
    return chosen, subs, ""


@dataclass
class CageResolution:
    ok: bool
    reason: str | None = None  # "platform" | "module"
    detail: str = ""
    profile_id: int | None = None
    subports: list[int] = field(default_factory=list)


def resolve_cage(
    port: str,
    variant: Variant,
    cages: Mapping[str, CageInfo],
    host_speeds: Mapping[str, list[int] | None],
    is_copper: Mapping[str, bool | None],
    host_apps: Mapping[str, list[HostApp] | None] | None = None,
) -> CageResolution:
    """Whether this cage alone can run the variant, ignoring its peer.

    The module check prefers ``host_apps`` (speed and host lanes) and falls back
    to the speed-only ``host_speeds`` for ports without it.
    """
    cage = cages.get(cage_of(port))
    if cage is None:
        return CageResolution(False, "platform", f"{port} cage is not in the platform mapping")
    pid, subs, why = _cage_profile(cage_of(port), cage, variant, is_copper.get(port))
    if pid is None:
        return CageResolution(False, "platform", why)
    # Advertisements constrain only when explicit; None or an empty advertisement
    # means unknown and is unconstrained.
    apps = (host_apps or {}).get(port)
    if apps:
        want = (variant.speed_mbps, cage.lanes // variant.factor)
        if want not in apps:
            return CageResolution(
                False,
                "module",
                f"{port} module advertises {format_host_apps(apps)}, "
                f"not {want[0] // 1000}G over {want[1]} lanes",
            )
        return CageResolution(True, profile_id=pid, subports=subs)
    advertised = host_speeds.get(port)
    if advertised and variant.speed_mbps not in advertised:
        return CageResolution(
            False,
            "module",
            f"{port} module advertises {sorted(advertised)} Mbps, not {variant.speed_mbps}",
        )
    return CageResolution(True, profile_id=pid, subports=subs)


def resolve_pair(
    port: str,
    peer: str,
    variant: Variant,
    cages: dict[str, CageInfo],
    host_speeds: Mapping[str, list[int] | None],
    is_copper: Mapping[str, bool | None],
    host_apps: Mapping[str, list[HostApp] | None] | None = None,
) -> PairResolution:
    """Resolve one snake pair (named by lane-1 ports) for a non-max variant."""
    profiles = {}
    subs_by_end = {}
    for end in (port, peer):
        cage_result = resolve_cage(end, variant, cages, host_speeds, is_copper, host_apps)
        if not cage_result.ok:
            return PairResolution(False, cage_result.reason, cage_result.detail)
        profiles[end] = cage_result.profile_id
        subs_by_end[end] = cage_result.subports
    if profiles[port] != profiles[peer]:
        return PairResolution(
            False, "peer", f"profile mismatch: {port}={profiles[port]} {peer}={profiles[peer]}"
        )
    a_subs, z_subs = subs_by_end[port], subs_by_end[peer]
    if a_subs != z_subs:
        return PairResolution(
            False, "peer", f"subport layout mismatch: {port}={a_subs} {peer}={z_subs}"
        )
    pid = profiles[port]
    pairs = [(f"{cage_of(port)}/{s}", f"{cage_of(peer)}/{s}") for s in a_subs]
    profile_by_port = {name: pid for ab in pairs for name in ab}
    return PairResolution(True, subport_pairs=pairs, profile_by_port=profile_by_port)


@dataclass
class VariantResolution:
    variant: Variant
    # Expanded symmetric {subport: peer_subport} map for supported pairs.
    expanded_pairs: dict[str, str] = field(default_factory=dict)
    profile_overrides: dict[str, int] = field(default_factory=dict)
    supported: int = 0
    total: int = 0
    excluded_by_reason: dict[str, int] = field(default_factory=dict)

    def summary(self, prefix: str) -> str:
        excluded = self.total - self.supported
        reasons = " ".join(
            f"{reason}={count}" for reason, count in sorted(self.excluded_by_reason.items())
        )
        return (
            f"{prefix} VARIANT SUMMARY: requested={self.variant.name} "
            f"supported={self.supported}/{self.total} excluded={excluded}"
            + (f" {reasons}" if reasons else "")
        )


def resolve_pairs(
    pairs: dict[str, str],
    variant: Variant,
    cages: dict[str, CageInfo],
    host_speeds: Mapping[str, list[int] | None],
    is_copper: Mapping[str, bool | None],
    host_apps: Mapping[str, list[HostApp] | None] | None = None,
) -> VariantResolution:
    """Resolve every snake pair for a non-max variant.

    ``pairs`` is the symmetric {port: peer} map from TEST_SNAKE_PAIRS; each
    cable is resolved once, in sorted order for determinism.
    """
    res = VariantResolution(variant=variant)
    seen: set[str] = set()
    for port in sorted(pairs):
        peer = pairs[port]
        if port in seen or peer in seen:
            continue
        seen.add(port)
        seen.add(peer)
        res.total += 1
        pr = resolve_pair(port, peer, variant, cages, host_speeds, is_copper, host_apps)
        if not pr.ok:
            reason = pr.reason or "platform"
            res.excluded_by_reason[reason] = res.excluded_by_reason.get(reason, 0) + 1
            logger.info(
                "variant=%s pair=%s<->%s excluded reason=%s: %s",
                variant.name, port, peer, pr.reason, pr.detail,
            )
            continue
        res.supported += 1
        for a, z in pr.subport_pairs:
            res.expanded_pairs[a] = z
            res.expanded_pairs[z] = a
        res.profile_overrides.update(pr.profile_by_port)
        logger.info(
            "variant=%s pair=%s<->%s resolved factor=%d profile=%d",
            variant.name, port, peer, variant.factor, next(iter(pr.profile_by_port.values())),
        )
    return res
