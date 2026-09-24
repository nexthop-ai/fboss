"""Unit tests for QsfpTestRunner._build_cabled_config, max and variant paths."""

from tests.libs.test_runner import QsfpTestRunner
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

_PROFILES = {39: (800000, 8), 38: (400000, 4), 25: (200000, 2), 23: (100000, 1)}
FULL = {1: [39, 38, 25, 23], 2: [23], 3: [25, 23], 4: [23], 5: [38, 25, 23], 6: [23], 7: [25, 23], 8: [23]}
PIPE_LIMITED = {1: [39, 38], 5: [38]}


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

    def test_variant_excluded_pair_keeps_only_self_pairs(self):
        cages = {
            "eth1/1": _cage(FULL, base_id=100),
            "eth1/2": _cage(PIPE_LIMITED, base_id=200),
            "eth1/3": _cage(FULL, base_id=300),
        }
        resolution = self._resolution("4x200G", cages)
        out = _runner()._build_cabled_config(BASE_CONFIG, PORTS, PORT_MAP, PAIRS, resolution)
        assert _entries(out) == [
            {"aPortName": p, "zPortName": p, "profileID": 39} for p in PORTS
        ]

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
        entries = _entries(
            _runner()._build_cabled_config(
                BASE_CONFIG, ports, PORT_MAP, {}, self._resolution("4x200G", cages),
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
