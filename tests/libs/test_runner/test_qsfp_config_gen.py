"""Unit tests for QsfpTestRunner._build_cabled_config, max and variant paths."""

from tests.libs.test_runner import platform_mapping, QsfpTestRunner, variants
from tests.libs.test_runner.platform_mapping import PortInfo
from tests.libs.test_runner.variants import (
    cage_of,
    CageInfo,
    derive_variant_chain,
    parse_variant,
    resolve_cage,
    resolve_pairs,
    SubportInfo,
)

_PROFILES = {
    39: (800000, 8),
    38: (400000, 4),
    25: (200000, 2),
    23: (100000, 1),
    # Copper: 800G_8, 400G_4 and 200G_2 by their switch_config.thrift ids.
    50: (800000, 8),
    45: (400000, 4),
    54: (200000, 2),
}
FULL = {1: [39, 38, 25, 23], 2: [23], 3: [25, 23], 4: [23], 5: [38, 25, 23], 6: [23], 7: [25, 23], 8: [23]}
PIPE_LIMITED = {1: [39, 38], 5: [38]}
COPPER = {1: [50, 45, 54], 3: [54], 5: [45, 54], 7: [54]}
_MEDIUM_BY_ID = {39: "optical", 38: "optical", 25: "optical", 50: "copper", 45: "copper", 54: "copper"}


def _cage(subports, lanes=8, base_id=100):
    return CageInfo(
        controlling="unused/1",
        lanes=lanes,
        subports={
            sub: SubportInfo(base_id + sub, {pid: _PROFILES[pid] for pid in pids})
            for sub, pids in subports.items()
        },
    )

BASE_CONFIG = {"qsfpTestConfig": {"cabledPortPairs": []}}
PORTS = ["eth1/1/1", "eth1/2/1", "eth1/3/1"]
PAIRS = {"eth1/1/1": "eth1/2/1", "eth1/2/1": "eth1/1/1"}
PORT_MAP = {
    p: PortInfo(logical_id=i, profile_id=39, speed=800000, profiles={39: 800000})
    for i, p in enumerate(PORTS)
}


def _runner():
    runner = QsfpTestRunner()
    runner._is_copper_by_port = dict.fromkeys(PORTS)
    return runner


def _entries(config):
    return config["qsfpTestConfig"]["cabledPortPairs"]


class TestBuildCabledConfig:
    def test_max_output_unchanged_by_variant_plumbing(self):
        runner = _runner()
        out = runner._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS)
        explicit = runner._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution=None)
        assert out == explicit
        entries = _entries(out)
        # One self-pair per port, then the neighbor pair, in order.
        assert entries[:3] == [
            {"aPortName": p, "zPortName": p, "profileID": 39} for p in PORTS
        ]
        assert entries[3] == {"aPortName": "eth1/1/1", "zPortName": "eth1/2/1", "profileID": 39}

    def _resolution(self, variant_name, cages):
        chain = derive_variant_chain({"eth1/1": _cage(FULL)})
        return resolve_pairs(PAIRS, parse_variant(variant_name, chain), cages, {}, {})

    def test_variant_expands_neighbor_entries(self):
        cages = {f"eth1/{i}": _cage(FULL, base_id=i * 100) for i in (1, 2, 3)}
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution)
        entries = _entries(out)
        # Self-pairs unchanged, before the neighbor entries.
        assert entries[:3] == [
            {"aPortName": p, "zPortName": p, "profileID": 39} for p in PORTS
        ]
        neighbors = entries[3:]
        assert [(e["aPortName"], e["zPortName"]) for e in neighbors] == [
            ("eth1/1/1", "eth1/2/1"),
            ("eth1/1/3", "eth1/2/3"),
            ("eth1/1/5", "eth1/2/5"),
            ("eth1/1/7", "eth1/2/7"),
        ]
        assert all(e["profileID"] == 25 for e in neighbors)

    def test_variant_excluded_pair_keeps_self_pairs_and_max_neighbor(self):
        # The pair stays cabled at its max profile: the hw test's duplicate-serial
        # check needs a DAC's two ends to name each other.
        cages = {
            "eth1/1": _cage(FULL, base_id=100),
            "eth1/2": _cage(PIPE_LIMITED, base_id=200),
            "eth1/3": _cage(FULL, base_id=300),
        }
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution)
        assert _entries(out) == [
            *({"aPortName": p, "zPortName": p, "profileID": 39} for p in PORTS),
            {"aPortName": "eth1/1/1", "zPortName": "eth1/2/1", "profileID": 39},
        ]

    def test_variant_excluded_pair_cages_stay_at_max(self):
        # eth1/1 alone could run 4x200G, but its cable partner cannot: both
        # cages keep max self-pairs so the max neighbor entry agrees with them,
        # while the unpaired eth1/3 still takes the variant.
        cages = {
            "eth1/1": _cage(FULL, base_id=100),
            "eth1/2": _cage(PIPE_LIMITED, base_id=200),
            "eth1/3": _cage(FULL, base_id=300),
        }
        resolution = self._resolution("4x200G", cages)
        entries = _entries(
            _runner()._build_cabled_config(
                BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution,
                self._variant_cages("4x200G", cages),
            )
        )
        assert entries == [
            {"aPortName": "eth1/1/1", "zPortName": "eth1/1/1", "profileID": 39},
            {"aPortName": "eth1/2/1", "zPortName": "eth1/2/1", "profileID": 39},
            *(
                {"aPortName": f"eth1/3/{s}", "zPortName": f"eth1/3/{s}", "profileID": 25}
                for s in (1, 3, 5, 7)
            ),
            {"aPortName": "eth1/1/1", "zPortName": "eth1/2/1", "profileID": 39},
        ]

    def test_variant_excluded_pair_outside_pass_gets_no_neighbor(self):
        cages = {
            "eth1/1": _cage(FULL, base_id=100),
            "eth1/2": _cage(PIPE_LIMITED, base_id=200),
            "eth1/3": _cage(FULL, base_id=300),
        }
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(
            BASE_CONFIG, ["eth1/1/1", "eth1/3/1"], PORT_MAP, PAIRS, resolution
        )
        assert all(e["aPortName"] == e["zPortName"] for e in _entries(out))

    def _variant_cages(self, variant_name, cages, ports=PORTS):
        """What _prepare_pass builds: one resolution per cage in the pass."""
        variant = parse_variant(variant_name, derive_variant_chain({"eth1/1": _cage(FULL)}))
        return {cage_of(p): resolve_cage(p, variant, cages, {}, {}) for p in ports}

    def test_self_pairs_take_the_variant_per_cage(self):
        # eth1/2 cannot pair with eth1/1, but its module is still worth
        # exercising at the variant: the qsfp tests are per transceiver.
        cages = {
            "eth1/1": _cage(FULL, base_id=100),
            "eth1/2": _cage(FULL, base_id=200),
            "eth1/3": _cage(PIPE_LIMITED, base_id=300),
        }
        resolution = self._resolution("4x200G", cages)
        entries = _entries(
            _runner()._build_cabled_config(
                BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution,
                self._variant_cages("4x200G", cages),
            )
        )
        selfies = [e for e in entries if e["aPortName"] == e["zPortName"]]
        assert [(e["aPortName"], e["profileID"]) for e in selfies] == [
            ("eth1/1/1", 25), ("eth1/1/3", 25), ("eth1/1/5", 25), ("eth1/1/7", 25),
            ("eth1/2/1", 25), ("eth1/2/3", 25), ("eth1/2/5", 25), ("eth1/2/7", 25),
            ("eth1/3/1", 39),
        ]
        # Every self-pair still precedes every neighbor entry.
        assert entries[: len(selfies)] == selfies

    def test_self_pairs_are_not_repeated_per_subport(self):
        # A pass may list several ports of one cage; the cage block is emitted once.
        cages = {"eth1/1": _cage(FULL, base_id=100)}
        ports = ["eth1/1/1", "eth1/1/5"]
        variant = parse_variant("4x200G", derive_variant_chain(cages))
        entries = _entries(
            _runner()._build_cabled_config(
                BASE_CONFIG, ports, PORT_MAP, {}, resolve_pairs({}, variant, cages, {}, {}),
                self._variant_cages("4x200G", cages, ports),
            )
        )
        assert [e["aPortName"] for e in entries] == [
            "eth1/1/1", "eth1/1/3", "eth1/1/5", "eth1/1/7"
        ]

    def test_variant_pass_port_filter(self):
        cages = {f"eth1/{i}": _cage(FULL, base_id=i * 100) for i in (1, 2, 3)}
        resolution = self._resolution("2x400G", cages)
        out = _runner()._build_cabled_config(
            BASE_CONFIG, ["eth1/1/1", "eth1/3/1"], PORT_MAP, PAIRS, resolution
        )
        # Peer cage eth1/2 is outside this pass's ports: no neighbor entries.
        assert all(e["aPortName"] == e["zPortName"] for e in _entries(out))


class TestStrictEligibility:
    """_strict_eligible_ports() on a variant run: a passive DAC whose variant
    profile the qsfp hw test cannot lane-map leaves the media-strict pass."""

    PORTS = ["eth1/1/1", "eth1/2/1"]
    CAGES = {"eth1/1": _cage(COPPER, base_id=100), "eth1/2": _cage(FULL, base_id=200)}
    PORT_MAP = {
        "eth1/1/1": PortInfo(
            logical_id=1, profile_id=50, speed=800000, profiles={50: 800000, 45: 400000, 54: 200000}
        ),
        "eth1/2/1": PortInfo(logical_id=2, profile_id=39, speed=800000, profiles={39: 800000}),
    }

    def _runner(self, monkeypatch, variant):
        monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: _MEDIUM_BY_ID)
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: _MEDIUM_BY_ID)
        runner = QsfpTestRunner()
        runner.tc = {"variant": variant, "model": "NH-BW800-F"}
        monkeypatch.setattr(runner, "_full_platform_mapping", lambda config_name: self.CAGES)
        monkeypatch.setattr(
            runner, "_load_base_config_and_port_map", lambda base_dir, config_name: (BASE_CONFIG, self.PORT_MAP)
        )
        runner._media_tech_by_port = {"eth1/1/1": "PASSIVE_CU", "eth1/2/1": "OPTICAL_SMF"}
        runner._media_by_port = {"eth1/1/1": "CR8_800G", "eth1/2/1": None}
        runner._transmitter_tech_by_port = {"eth1/1/1": "COPPER", "eth1/2/1": "OPTICAL"}
        runner._is_copper_by_port = {"eth1/1/1": True, "eth1/2/1": False}
        return runner

    def test_copper_at_unverifiable_variant_profile_is_excluded(self, monkeypatch, caplog):
        runner = self._runner(monkeypatch, "4x200G")
        with caplog.at_level("WARNING", logger="test_runner"):
            eligible = runner._strict_eligible_ports("nhbw800f", self.PORTS)
        assert eligible == ["eth1/2/1"]
        assert "no lane-map rule for copper profile 54" in caplog.text

    def test_copper_in_excluded_pair_stays_verifiable(self, monkeypatch):
        # Its peer is pipe-limited, so _build_cabled_config keeps this cage at
        # max (profile 50), which the hw test can lane-map.
        runner = self._runner(monkeypatch, "4x200G")
        cages = dict(self.CAGES, **{"eth1/3": _cage(PIPE_LIMITED, base_id=300)})
        monkeypatch.setattr(runner, "_full_platform_mapping", lambda config_name: cages)
        monkeypatch.setattr(
            runner, "_load_snake_pairs", lambda: {"eth1/1/1": "eth1/3/1", "eth1/3/1": "eth1/1/1"}
        )
        ports = [*self.PORTS, "eth1/3/1"]
        runner._media_tech_by_port["eth1/3/1"] = "OPTICAL_SMF"
        runner._transmitter_tech_by_port["eth1/3/1"] = "OPTICAL"
        runner._is_copper_by_port["eth1/3/1"] = False
        port_map = dict(
            self.PORT_MAP,
            **{"eth1/3/1": PortInfo(logical_id=3, profile_id=39, speed=800000, profiles={39: 800000})},
        )
        monkeypatch.setattr(
            runner, "_load_base_config_and_port_map", lambda base_dir, config_name: (BASE_CONFIG, port_map)
        )
        assert runner._strict_eligible_ports("nhbw800f", ports) == ports

    def test_other_copper_media_is_not_gated(self, monkeypatch):
        # Only the CR8_800G branch of the hw test's lane-map switch throws.
        runner = self._runner(monkeypatch, "4x200G")
        runner._media_by_port["eth1/1/1"] = "CR4_400G"
        assert runner._strict_eligible_ports("nhbw800f", self.PORTS) == self.PORTS

    def test_copper_at_verifiable_variant_profile_is_kept(self, monkeypatch):
        runner = self._runner(monkeypatch, "2x400G")
        assert runner._strict_eligible_ports("nhbw800f", self.PORTS) == self.PORTS

    def test_max_run_keeps_copper(self, monkeypatch):
        runner = self._runner(monkeypatch, "max")
        assert runner._strict_eligible_ports("nhbw800f", self.PORTS) == self.PORTS


class TestHostAppTieBreak:
    """profile_for_medium() on a CMIS optic reset into DR1_200G: of the 200G
    optical profiles, only the one at the advertised host lane count programs."""

    INFO = PortInfo(logical_id=1, profile_id=63, speed=1600000, profiles={63: 1600000, 25: 200000, 53: 200000})
    LANES = {63: 8, 25: 4, 53: 1}
    MEDIUM = {63: "optical", 25: "optical", 53: "optical"}
    DR8_APPS = [(200000, 1), (400000, 2), (800000, 4), (1600000, 8)]

    def _patch(self, monkeypatch):
        monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: self.MEDIUM)
        monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: self.LANES)

    def test_picks_advertised_lane_count(self, monkeypatch):
        self._patch(monkeypatch)
        assert self.INFO.profile_for_medium(False, 200000, None, self.DR8_APPS) == 53

    def test_without_host_apps_keeps_first_speed_match(self, monkeypatch):
        self._patch(monkeypatch)
        assert self.INFO.profile_for_medium(False, 200000) == 25
        assert self.INFO.profile_for_medium(False, 200000, None, []) == 25

    def test_no_advertised_match_keeps_speed_matches(self, monkeypatch):
        self._patch(monkeypatch)
        assert self.INFO.profile_for_medium(False, 200000, None, [(1600000, 8)]) == 25

    def test_runner_passes_host_apps(self, monkeypatch):
        self._patch(monkeypatch)
        runner = QsfpTestRunner()
        runner._media_tech_by_port = {"eth1/1/1": "OPTICAL_SMF"}
        runner._media_by_port = {"eth1/1/1": "DR1_200G"}
        runner._is_copper_by_port = {"eth1/1/1": False}
        runner._host_apps_by_port = {"eth1/1/1": self.DR8_APPS}
        assert runner._port_profile_id("eth1/1/1", {"eth1/1/1": self.INFO}) == 53
