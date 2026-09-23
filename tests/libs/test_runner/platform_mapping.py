"""Platform-mapping and port-profile helpers shared by the hardware test runners."""

import functools
import json
import logging
import re
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger("test_runner")

ProfileId = int

_PLATFORM_CONFIGS_DIR = Path("fboss/configs/platforms")

# Upper bound on the profiles the link/QSFP hw test binaries will drive.
_MAX_PROFILE_SPEED_MBPS = 1_600_000

_SWITCH_CONFIG_THRIFT = Path("fboss/agent/switch_config.thrift")


def repo_dir(relative: Path) -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / relative).is_dir():
            return parent / relative
    raise FileNotFoundError(f"could not locate {relative} above {__file__}")


def _read_switch_config_thrift() -> str:
    path = repo_dir(_SWITCH_CONFIG_THRIFT.parent) / _SWITCH_CONFIG_THRIFT.name
    try:
        text = path.read_text()
    except OSError as e:
        raise RuntimeError(f"Failed to read {path}: {e}") from e

    return text


@functools.lru_cache(maxsize=1)
def _profile_lanes_by_id() -> dict[ProfileId, int]:
    """PortProfileID value -> lane count, from the thrift enum names.

    Names are PROFILE_<speed>_<lanes>_<modulation>_<fec>_<medium>, so the lane
    count is the third underscore-separated field (PROFILE_800G_8_... -> 8).
    """
    text = _read_switch_config_thrift()
    lanes = {}
    for name, value in re.findall(r"(PROFILE_\w+)\s*=\s*(\d+)", text):
        parts = name.split("_")
        if len(parts) > 2 and parts[2].isdigit():
            lanes[int(value)] = int(parts[2])
    if not lanes:
        logger.warning(f"Failed to parse lane speeds from switch config thrift path {_SWITCH_CONFIG_THRIFT}")
    return lanes


@functools.lru_cache(maxsize=1)
def _profile_medium_by_id() -> dict[ProfileId, str]:
    """PortProfileID value -> "copper" | "optical", from the thrift enum names."""
    text = _read_switch_config_thrift()
    media = {}
    for name, value in re.findall(r"(PROFILE_\w+)\s*=\s*(\d+)", text):
        if "_COPPER" in name:
            media[int(value)] = "copper"
        elif "_OPTICAL" in name:
            media[int(value)] = "optical"
    if not media:
        raise RuntimeError(f"No PortProfileID entries parsed from {_SWITCH_CONFIG_THRIFT}")
    return media


def media_speed_mbps(media_interface: str | None) -> int | None:
    """Per-leg speed from a media code name; profiles are per-port, so
    FR4_2x400G -> 400000, not 800000."""
    m = re.search(r"_(?:\d+x)?(\d+)G$", media_interface or "")
    return int(m.group(1)) * 1000 if m else None


class PortInfo(NamedTuple):
    logical_id: int
    profile_id: ProfileId
    speed: int
    # Supported profiles, {id: speed in Mbps}.
    profiles: dict[ProfileId, int]

    def profile_for_medium(
        self,
        is_copper: bool | None,
        media_speed: int | None,
        max_lane_speed: int | None = None,
    ) -> ProfileId | None:
        """Best profile for the cabled medium: prefer the module's media speed,
        else max speed. None medium keeps the default pick; copper with no
        copper profile returns None. Excludes profiles with serdes rates greater than
        max_lane_speed."""
        if is_copper is None:
            return self.profile_id
        want = "copper" if is_copper else "optical"
        medium = _profile_medium_by_id()
        matching = [pid for pid in self.profiles if medium.get(pid) == want]
        lanes = _profile_lanes_by_id() if max_lane_speed is not None else {}
        if lanes:
            matching = [
                pid
                for pid in matching
                if lanes.get(pid) and self.profiles[pid] / lanes[pid] <= max_lane_speed
            ]
        if matching:
            speed_matching = [pid for pid in matching if self.profiles[pid] == media_speed]
            return max(speed_matching or matching, key=lambda pid: self.profiles[pid])
        return None if is_copper else self.profile_id


def _platform_mapping_path(config_name: str) -> Path:
    """Locate a config's platform_mapping.json.

    Mappings are generated beside their inputs under
    configs/platforms/<vendor>/<config_name>/platform_mapping/generated/, the
    same tree PlatformDescriptorRegistry (fboss/lib/platforms/PlatformDescriptor.h)
    scans on the switch. A hardware-revision variant lives one level deeper,
    under <vendor>/<base_platform>/variants/<config_name>/.
    """
    base = repo_dir(_PLATFORM_CONFIGS_DIR)
    patterns = (
        f"*/{config_name}/platform_mapping/generated/platform_mapping.json",
        f"*/*/variants/{config_name}/platform_mapping/generated/platform_mapping.json",
    )
    for pattern in patterns:
        found = sorted(base.glob(pattern))
        if found:
            return found[0]
    raise FileNotFoundError(
        f"no platform mapping for {config_name!r}: looked for "
        + " and ".join(f"{base}/{p}" for p in patterns)
    )


def load_platform_mapping(config_name: str) -> dict[str, PortInfo]:
    path = _platform_mapping_path(config_name)
    with open(path, encoding="utf-8") as f:
        mapping = json.load(f)
    prof: dict[ProfileId, int] = {
        int(p["factor"]["profileID"]): p["profile"]["speed"]
        for p in mapping["platformSupportedProfiles"]
        if p["profile"]["speed"] <= _MAX_PROFILE_SPEED_MBPS
    }
    index = {}
    for entry in mapping["ports"].values():
        name = entry["mapping"]["name"]
        supported = [int(pid) for pid in entry["supportedProfiles"] if int(pid) in prof]
        if not supported:
            continue
        gmax = max(supported, key=lambda pid: prof[pid])
        index[name] = PortInfo(
            entry["mapping"]["id"], gmax, prof[gmax], {pid: prof[pid] for pid in supported}
        )
    return index
