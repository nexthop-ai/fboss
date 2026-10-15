"""QsfpTestRunner: per-port profile selection, media-strict eligibility, the
cabled config it generates at max and at a breakout variant, and LedTestRunner."""

import pytest

from tests.libs.test_runner import LedTestRunner, QsfpTestRunner, platform_mapping
from tests.libs.test_runner.deploy import STACK_FORWARDING
from tests.libs.test_runner.platform_mapping import PortInfo
from tests.libs.test_runner.variants import (
    cage_of,
    derive_variant_chain,
    parse_variant,
    resolve_cage,
    resolve_pairs,
)

from .helpers import COPPER, FULL, LANES_BY_ID, MEDIUM_BY_ID, PIPE_LIMITED, make_cage, make_port, symmetric_pairs

BASE_CONFIG = {"qsfpTestConfig": {"cabledPortPairs": []}}
PORTS = ["eth1/1/1", "eth1/2/1", "eth1/3/1"]
PAIRS = symmetric_pairs(("eth1/1/1", "eth1/2/1"))
PORT_MAP = {p: make_port(i) for i, p in enumerate(PORTS)}
# eth1/1 could take a variant, but its cable partner eth1/2 cannot.
PIPE_LIMITED_PEER_CAGES = {
    "eth1/1": make_cage(FULL, base_id=100),
    "eth1/2": make_cage(PIPE_LIMITED, base_id=200),
    "eth1/3": make_cage(FULL, base_id=300),
}


def _runner():
    runner = QsfpTestRunner()
    runner._is_copper_by_port = dict.fromkeys(PORTS)
    return runner


def _entries(config):
    return config["qsfpTestConfig"]["cabledPortPairs"]


def _port_runner(port, *, media_tech=None, transmitter=None, media=None, is_copper=None, host_apps=None):
    runner = QsfpTestRunner()
    runner._media_tech_by_port = {port: media_tech}
    runner._transmitter_tech_by_port = {port: transmitter}
    runner._media_by_port = {port: media}
    runner._is_copper_by_port = {port: is_copper}
    runner._host_apps_by_port = {port: host_apps}
    return runner


_COPPER_INFO = make_port(1, 50, 45, 54)
_OPTICAL_INFO = make_port(2, 39, 38)


class TestPortProfileId:
    def test_unmapped_port_falls_back(self):
        runner = _port_runner("eth1/9/1")
        assert runner._port_profile_id("eth1/9/1", {}) == QsfpTestRunner._FALLBACK_PROFILE_ID

    def test_unknown_medium_keeps_mapping_default(self, profile_tables):
        runner = _port_runner("eth1/1/1", is_copper=None)
        assert runner._port_profile_id("eth1/1/1", {"eth1/1/1": _COPPER_INFO}) == 50

    def test_copper_dac_picks_copper_profile_at_media_speed(self, profile_tables):
        runner = _port_runner("eth1/1/1", media_tech="PASSIVE_CU", media="CR4_400G", is_copper=True)
        assert runner._port_profile_id("eth1/1/1", {"eth1/1/1": _COPPER_INFO}) == 45

    def test_copper_without_copper_profile_falls_back_to_max(self, profile_tables):
        runner = _port_runner("eth1/2/1", media_tech="PASSIVE_CU", media="CR8_800G", is_copper=True)
        assert runner._port_profile_id("eth1/2/1", {"eth1/2/1": _OPTICAL_INFO}) == 39

    def test_passive_dac_is_capped_at_100g_lanes(self, profile_tables, monkeypatch):
        # 61: a 400G copper profile over 2 lanes (200G/lane), beyond what a passive DAC carries.
        monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: {**MEDIUM_BY_ID, 61: "copper"})
        monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: {**LANES_BY_ID, 61: 2})
        info = PortInfo(logical_id=1, profile_id=50, speed=800000, profiles={50: 800000, 61: 400000, 45: 400000})
        passive = _port_runner("eth1/1/1", media_tech="PASSIVE_CU", media="CR4_400G", is_copper=True)
        assert passive._port_profile_id("eth1/1/1", {"eth1/1/1": info}) == 45
        active = _port_runner("eth1/1/1", media_tech="ACTIVE_CU", media="CR4_400G", is_copper=True)
        assert active._port_profile_id("eth1/1/1", {"eth1/1/1": info}) in (45, 61)

    def test_runner_passes_host_apps(self, monkeypatch):
        """A CMIS optic reset into DR1_200G matches several 200G optical
        profiles; the one at the advertised host lane count programs."""
        info = PortInfo(logical_id=1, profile_id=63, speed=1600000, profiles={63: 1600000, 25: 200000, 53: 200000})
        monkeypatch.setattr(platform_mapping, "_profile_medium_by_id", lambda: {63: "optical", 25: "optical", 53: "optical"})
        monkeypatch.setattr(platform_mapping, "_profile_lanes_by_id", lambda: {63: 8, 25: 4, 53: 1})
        runner = _port_runner(
            "eth1/1/1", media_tech="OPTICAL_SMF", media="DR1_200G", is_copper=False,
            host_apps=[(200000, 1), (400000, 2), (800000, 4), (1600000, 8)],
        )
        assert runner._port_profile_id("eth1/1/1", {"eth1/1/1": info}) == 53


class TestPairProfileId:
    def test_missing_end_falls_back(self):
        runner = _runner()
        assert runner._pair_profile_id("eth1/1/1", "eth1/9/1", PORT_MAP) == QsfpTestRunner._FALLBACK_PROFILE_ID

    def test_narrower_end_decides(self):
        port_map = {"eth1/1/1": make_port(1, 39), "eth1/2/1": make_port(2, 38)}
        runner = _port_runner("eth1/1/1")
        runner._is_copper_by_port["eth1/2/1"] = None
        assert runner._pair_profile_id("eth1/1/1", "eth1/2/1", port_map) == 38
        assert runner._pair_profile_id("eth1/2/1", "eth1/1/1", port_map) == 38


_STRICT_REASON_CASES = [
    (dict(port="eth1/9/1"), "port is not in the platform mapping"),
    (dict(port="eth1/1/1", is_copper=None), "module reports no usable medium information"),
    (
        dict(port="eth1/2/1", media_tech="PASSIVE_CU", media="CR8_800G", is_copper=True),
        "copper cable but the platform mapping offers no copper profile",
    ),
    (
        dict(port="eth1/2/1", media_tech="OPTICAL_SMF", media="FR4_200G", is_copper=False),
        "module media FR4_200G (200000 Mbps) does not match selected profile 39 (800000 Mbps)",
    ),
    (
        dict(port="eth1/1/1", media_tech="PASSIVE_CU", transmitter="UNKNOWN", media="CR8_800G", is_copper=True),
        "copper profile selected but module reports UNKNOWN transmitter technology",
    ),
    (dict(port="eth1/1/1", media_tech="PASSIVE_CU", transmitter="COPPER", media="CR8_800G", is_copper=True), None),
    (dict(port="eth1/2/1", media_tech="OPTICAL_SMF", transmitter="OPTICAL", media="FR8_800G", is_copper=False), None),
]


class TestStrictUnverifiableReason:
    @pytest.mark.usefixtures("profile_tables")
    @pytest.mark.parametrize("port_kwargs, expected", _STRICT_REASON_CASES, ids=lambda c: str(c)[:40])
    def test_each_reason(self, port_kwargs, expected):
        port_map = {"eth1/1/1": _COPPER_INFO, "eth1/2/1": _OPTICAL_INFO}
        runner = _port_runner(**port_kwargs)
        assert runner._strict_unverifiable_reason(port_kwargs["port"], port_map) == expected


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

    def test_disables_firmware_upgrade_and_keeps_base_config_intact(self):
        base = {"qsfpTestConfig": {"cabledPortPairs": [{"aPortName": "stale", "zPortName": "stale", "profileID": 1}]}}
        out = _runner()._build_cabled_config(base, PORTS, PORT_MAP, PAIRS)
        assert out["defaultCommandLineArgs"] == {
            "firmware_upgrade_on_coldboot": "false",
            "firmware_upgrade_on_tcvr_insert": "false",
        }
        assert all(e["aPortName"] != "stale" for e in _entries(out))
        assert base["qsfpTestConfig"]["cabledPortPairs"][0]["aPortName"] == "stale"

    def _resolution(self, variant_name, cages):
        chain = derive_variant_chain({"eth1/1": make_cage(FULL)})
        return resolve_pairs(PAIRS, parse_variant(variant_name, chain), cages, {}, {})

    def test_variant_expands_neighbor_entries(self):
        cages = {f"eth1/{i}": make_cage(FULL, base_id=i * 100) for i in (1, 2, 3)}
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
        cages = PIPE_LIMITED_PEER_CAGES
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution)
        assert _entries(out) == [
            *({"aPortName": p, "zPortName": p, "profileID": 39} for p in PORTS),
            {"aPortName": "eth1/1/1", "zPortName": "eth1/2/1", "profileID": 39},
        ]

    def test_variant_excluded_pair_cages_stay_at_max(self):
        # Both cages keep max self-pairs so the max neighbor entry agrees with
        # them, while the unpaired eth1/3 still takes the variant.
        cages = PIPE_LIMITED_PEER_CAGES
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
        cages = PIPE_LIMITED_PEER_CAGES
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(
            BASE_CONFIG, ["eth1/1/1", "eth1/3/1"], PORT_MAP, PAIRS, resolution
        )
        assert all(e["aPortName"] == e["zPortName"] for e in _entries(out))

    def _variant_cages(self, variant_name, cages, ports=PORTS):
        """What _prepare_pass builds: one resolution per cage in the pass."""
        variant = parse_variant(variant_name, derive_variant_chain({"eth1/1": make_cage(FULL)}))
        return {cage_of(p): resolve_cage(p, variant, cages, {}, {}) for p in ports}

    def test_self_pairs_take_the_variant_per_cage(self):
        # eth1/2 cannot pair with eth1/1, but its module is still worth
        # exercising at the variant: the qsfp tests are per transceiver.
        cages = {
            "eth1/1": make_cage(FULL, base_id=100),
            "eth1/2": make_cage(FULL, base_id=200),
            "eth1/3": make_cage(PIPE_LIMITED, base_id=300),
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
        cages = {"eth1/1": make_cage(FULL, base_id=100)}
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
        cages = {f"eth1/{i}": make_cage(FULL, base_id=i * 100) for i in (1, 2, 3)}
        resolution = self._resolution("2x400G", cages)
        out = _runner()._build_cabled_config(
            BASE_CONFIG, ["eth1/1/1", "eth1/3/1"], PORT_MAP, PAIRS, resolution
        )
        # Peer cage eth1/2 is outside this pass's ports: no neighbor entries.
        assert all(e["aPortName"] == e["zPortName"] for e in _entries(out))


class TestSelfPairPorts:
    def test_cage_that_resolves_expands_to_active_subports(self):
        cages = {"eth1/1": make_cage(FULL)}
        variant = parse_variant("4x200G", derive_variant_chain(cages))
        resolved = {"eth1/1": resolve_cage("eth1/1/1", variant, cages, {}, {})}
        assert _runner()._self_pair_ports("eth1/1/1", PORT_MAP, resolved) == [
            ("eth1/1/1", 25), ("eth1/1/3", 25), ("eth1/1/5", 25), ("eth1/1/7", 25)
        ]

    def test_cage_without_resolution_keeps_the_port(self):
        assert _runner()._self_pair_ports("eth1/1/1", PORT_MAP, {}) == [("eth1/1/1", 39)]


class TestStrictEligibility:
    """_strict_eligible_ports() on a variant run: a passive DAC whose variant
    profile the qsfp hw test cannot lane-map leaves the media-strict pass."""

    PORTS = ["eth1/1/1", "eth1/2/1"]
    CAGES = {"eth1/1": make_cage(COPPER, base_id=100), "eth1/2": make_cage(FULL, base_id=200)}
    PORT_MAP = {"eth1/1/1": _COPPER_INFO, "eth1/2/1": make_port(2, 39)}

    @pytest.fixture(autouse=True)
    def _tables(self, profile_tables):
        pass

    def _runner(self, monkeypatch, variant):
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
        cages = dict(self.CAGES, **{"eth1/3": make_cage(PIPE_LIMITED, base_id=300)})
        monkeypatch.setattr(runner, "_full_platform_mapping", lambda config_name: cages)
        monkeypatch.setattr(runner, "_load_snake_pairs", lambda: symmetric_pairs(("eth1/1/1", "eth1/3/1")))
        ports = [*self.PORTS, "eth1/3/1"]
        runner._media_tech_by_port["eth1/3/1"] = "OPTICAL_SMF"
        runner._transmitter_tech_by_port["eth1/3/1"] = "OPTICAL"
        runner._is_copper_by_port["eth1/3/1"] = False
        port_map = {**self.PORT_MAP, "eth1/3/1": make_port(3, 39)}
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


class TestTestArgs:
    def test_generated_config_wins(self):
        runner = QsfpTestRunner()
        runner._use_generated_config = True
        assert runner.test_args("nhbw800f") == f"qsfp --qsfp-config {QsfpTestRunner._REMOTE_CONFIG_PATH}"

    def test_shipped_config_by_codename_without_variant_flags(self):
        runner = QsfpTestRunner()
        assert runner.test_args("nhbw800f") == "qsfp --qsfp-config ./share/qsfp_test_configs/wedge800bact.materialized_JSON"


class TestLedTestRunner:
    def test_manifest_and_args(self):
        assert LedTestRunner.STACK == STACK_FORWARDING
        assert LedTestRunner.REQUIRED_PATHS == ("bin/led_service_hw_test",)
        assert LedTestRunner().test_args("nhbw800f") == "led"
