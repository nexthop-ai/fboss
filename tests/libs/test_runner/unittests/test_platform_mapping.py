"""platform_mapping.py: locating and loading a config's platform_mapping.json,
the thrift-derived profile tables, and PortInfo.profile_for_medium."""

import json

import pytest

from tests.libs.test_runner import platform_mapping
from tests.libs.test_runner.platform_mapping import (
    PortInfo,
    load_platform_mapping,
    media_speed_mbps,
)

from .helpers import make_port

_THRIFT = """
enum PortProfileID {
  PROFILE_DEFAULT = 0,
  PROFILE_100G_4_NRZ_RS528_OPTICAL = 22,
  PROFILE_200G_2_PAM4_RS544X2N_OPTICAL = 25,
  PROFILE_800G_8_PAM4_RS544X2N_OPTICAL = 39,
  PROFILE_800G_8_PAM4_RS544X2N_COPPER = 50,
  PROFILE_400G_4_PAM4_RS544X2N_COPPER = 45,
}
"""


class TestThriftTables:
    def test_lanes_and_medium_parsed_from_enum_names(self, monkeypatch):
        monkeypatch.setattr(platform_mapping, "_read_switch_config_thrift", lambda: _THRIFT)
        assert platform_mapping._profile_lanes_by_id() == {22: 4, 25: 2, 39: 8, 50: 8, 45: 4}
        assert platform_mapping._profile_medium_by_id() == {
            22: "optical", 25: "optical", 39: "optical", 50: "copper", 45: "copper"
        }

    def test_no_profiles_is_an_error(self, monkeypatch):
        monkeypatch.setattr(platform_mapping, "_read_switch_config_thrift", lambda: "enum Other { A = 1 }")
        assert platform_mapping._profile_lanes_by_id() == {}
        with pytest.raises(RuntimeError, match="No PortProfileID entries"):
            platform_mapping._profile_medium_by_id()


class TestMediaSpeed:
    @pytest.mark.parametrize("media, expected", [
        ("FR8_800G", 800000),
        ("FR4_400G", 400000),
        # Per-leg speed: a 2x400G breakout part runs 400G per port.
        ("FR4_2x400G", 400000),
        ("CR8_800G", 800000),
        ("DR1_200G", 200000),
        ("UNKNOWN", None),
        ("", None),
        (None, None),
    ])
    def test_per_leg_speed_from_media_code(self, media, expected):
        assert media_speed_mbps(media) == expected


class TestProfileForMedium:
    INFO = make_port(1, 39, 25, 50, 45)

    @pytest.fixture(autouse=True)
    def _tables(self, monkeypatch):
        monkeypatch.setattr(
            platform_mapping, "_profile_medium_by_id",
            lambda: {39: "optical", 25: "optical", 50: "copper", 45: "copper"},
        )
        monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: {39: 8, 25: 2, 50: 8, 45: 4})

    def test_unknown_medium_keeps_the_default(self):
        assert self.INFO.profile_for_medium(None, 400000) == 39

    def test_prefers_media_speed_then_max(self):
        assert self.INFO.profile_for_medium(False, 200000) == 25
        assert self.INFO.profile_for_medium(False, 100000) == 39
        assert self.INFO.profile_for_medium(True, 400000) == 45
        assert self.INFO.profile_for_medium(True, None) == 50

    def test_copper_without_copper_profile_is_none_but_optical_falls_back(self):
        optical_only = make_port(1, 39)
        assert optical_only.profile_for_medium(True, 800000) is None
        copper_only = make_port(1, 50)
        assert copper_only.profile_for_medium(False, 800000) == 50

    def test_lane_speed_cap_excludes_fast_serdes(self):
        # 800G over 8 lanes is 100G/lane; 200G over 2 lanes is also 100G/lane;
        # a 106.25G cap keeps both, a 50G cap keeps nothing copper.
        assert self.INFO.profile_for_medium(True, 800000, max_lane_speed=106_250) == 50
        assert self.INFO.profile_for_medium(True, 800000, max_lane_speed=50_000) is None

    def test_host_apps_break_same_speed_ties(self, monkeypatch):
        """A CMIS optic reset into DR1_200G matches several 200G optical
        profiles; only the one at the advertised host lane count programs."""
        info = PortInfo(logical_id=1, profile_id=63, speed=1600000, profiles={63: 1600000, 25: 200000, 53: 200000})
        monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: {63: "optical", 25: "optical", 53: "optical"})
        monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: {63: 8, 25: 4, 53: 1})
        dr8_apps = [(200000, 1), (400000, 2), (800000, 4), (1600000, 8)]
        assert info.profile_for_medium(False, 200000, None, dr8_apps) == 53
        assert info.profile_for_medium(False, 200000) == 25
        assert info.profile_for_medium(False, 200000, None, []) == 25
        # No advertised match leaves the speed matches alone.
        assert info.profile_for_medium(False, 200000, None, [(1600000, 8)]) == 25


class TestPlatformMappingPath:
    """_platform_mapping_path resolves the colocated
    <vendor>/<config>/platform_mapping/generated/ layout, and the variants
    layout one level deeper."""

    def _configs_dir(self, tmp_path, monkeypatch):
        d = tmp_path / "fboss" / "configs" / "platforms"
        d.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(platform_mapping, "repo_dir", lambda rel: d)
        return d

    def test_vendor_layout(self, tmp_path, monkeypatch):
        configs = self._configs_dir(tmp_path, monkeypatch)
        nested = configs / "accton" / "wedge800bact" / "platform_mapping" / "generated" / "platform_mapping.json"
        nested.parent.mkdir(parents=True)
        nested.write_text("{}")
        assert platform_mapping._platform_mapping_path("wedge800bact") == nested

    def test_variant_layout(self, tmp_path, monkeypatch):
        configs = self._configs_dir(tmp_path, monkeypatch)
        nested = (
            configs / "nexthop" / "m4062nhp" / "variants" / "m4062nhp_p1"
            / "platform_mapping" / "generated" / "platform_mapping.json"
        )
        nested.parent.mkdir(parents=True)
        nested.write_text("{}")
        assert platform_mapping._platform_mapping_path("m4062nhp_p1") == nested

    def test_missing_raises(self, tmp_path, monkeypatch):
        self._configs_dir(tmp_path, monkeypatch)
        with pytest.raises(FileNotFoundError):
            platform_mapping._platform_mapping_path("does_not_exist")


class TestLoadPlatformMapping:
    def test_indexes_ports_by_name_with_supported_profiles(self, tmp_path, monkeypatch):
        mapping = {
            "platformSupportedProfiles": [
                {"factor": {"profileID": 39}, "profile": {"speed": 800000}},
                {"factor": {"profileID": 25}, "profile": {"speed": 200000}},
                # Above the ceiling the hw tests drive: dropped from every port.
                {"factor": {"profileID": 91}, "profile": {"speed": 3200000}},
            ],
            "ports": {
                "1": {"mapping": {"id": 1, "name": "eth1/1/1"}, "supportedProfiles": {"39": {}, "25": {}, "91": {}}},
                "2": {"mapping": {"id": 2, "name": "eth1/1/3"}, "supportedProfiles": {"25": {}}},
                # Only unsupported profiles: not a usable port.
                "3": {"mapping": {"id": 3, "name": "eth1/2/1"}, "supportedProfiles": {"91": {}}},
            },
        }
        path = tmp_path / "platform_mapping.json"
        path.write_text(json.dumps(mapping))
        monkeypatch.setattr(platform_mapping, "_platform_mapping_path", lambda config_name: path)

        index = load_platform_mapping("unitplat")

        assert index == {
            "eth1/1/1": PortInfo(logical_id=1, profile_id=39, speed=800000, profiles={39: 800000, 25: 200000}),
            "eth1/1/3": PortInfo(logical_id=2, profile_id=25, speed=200000, profiles={25: 200000}),
        }
