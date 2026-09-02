"""Platform-mapping and port-profile helpers shared by the hardware test runners."""

import functools
import json
import re
from pathlib import Path
from typing import NamedTuple

_PLATFORM_MAPPING_DIR = Path(
    "fboss/lib/platform_mapping_v2/generated_platform_mappings"
)

# Link and QSFP hw test binaries have no support for profiles above 800G just yet.
_MAX_PROFILE_SPEED_MBPS = 800_000

_SWITCH_CONFIG_THRIFT = Path("fboss/agent/switch_config.thrift")


def repo_dir(relative: Path) -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / relative).is_dir():
            return parent / relative
    raise FileNotFoundError(f"could not locate {relative} above {__file__}")


@functools.lru_cache(maxsize=1)
def _profile_medium_by_id() -> dict[int, str]:
    """PortProfileID value -> "copper" | "optical", from the thrift enum names."""
    path = repo_dir(_SWITCH_CONFIG_THRIFT.parent) / _SWITCH_CONFIG_THRIFT.name
    try:
        text = path.read_text()
    except OSError as e:
        raise RuntimeError(f"Failed to read {path}: {e}") from e
    media = {}
    for name, value in re.findall(r"(PROFILE_\w+)\s*=\s*(\d+)", text):
        if "_COPPER" in name:
            media[int(value)] = "copper"
        elif "_OPTICAL" in name:
            media[int(value)] = "optical"
    if not media:
        raise RuntimeError(f"No PortProfileID entries parsed from {path}")
    return media


def media_speed_mbps(media_interface: str | None) -> int | None:
    """Per-leg speed from a media code name; profiles are per-port, so
    FR4_2x400G -> 400000, not 800000."""
    m = re.search(r"_(?:\d+x)?(\d+)G$", media_interface or "")
    return int(m.group(1)) * 1000 if m else None


class PortInfo(NamedTuple):
    logical_id: int
    profile_id: int
    speed: int
    # Supported profiles, {profileID: speed}.
    profiles: dict[int, int]

    def profile_for_medium(self, is_copper: bool | None, media_speed: int | None) -> int | None:
        """Best profile for the cabled medium: prefer the module's media speed,
        else max speed. None medium keeps the default pick; copper with no
        copper profile returns None."""
        if is_copper is None:
            return self.profile_id
        want = "copper" if is_copper else "optical"
        medium = _profile_medium_by_id()
        matching = [pid for pid in self.profiles if medium.get(pid) == want]
        if matching:
            speed_matching = [pid for pid in matching if self.profiles[pid] == media_speed]
            return max(speed_matching or matching, key=lambda pid: self.profiles[pid])
        return None if is_copper else self.profile_id


def _platform_mapping_path(config_name: str) -> Path:
    """Locate a config's platform_mapping.json across both on-disk layouts.

    Descriptor-backed platforms (e.g. wedge800bact/wedge800cact) are generated
    into <vendor>/<config_name>/platform_mapping.json, while the rest keep the
    legacy flat <config_name>_platform_mapping.json. Prefer the flat file for
    backwards compat, then fall back to a vendor-directory scan mirroring
    PlatformDescriptorRegistry (fboss/lib/platforms/PlatformDescriptor.h).
    """
    base = repo_dir(_PLATFORM_MAPPING_DIR)
    flat = base / f"{config_name}_platform_mapping.json"
    if flat.is_file():
        return flat
    nested = sorted(base.glob(f"*/{config_name}/platform_mapping.json"))
    if nested:
        return nested[0]
    raise FileNotFoundError(
        f"no platform mapping for {config_name!r}: looked for {flat} and "
        f"{base}/*/{config_name}/platform_mapping.json"
    )


def load_platform_mapping(config_name: str) -> dict[str, PortInfo]:
    path = _platform_mapping_path(config_name)
    with open(path, encoding="utf-8") as f:
        mapping = json.load(f)
    prof = {
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
