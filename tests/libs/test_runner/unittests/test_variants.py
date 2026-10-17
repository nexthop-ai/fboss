"""variants.py: speed/breakout variant vocabulary, the full platform-mapping
loader, and per-pair / per-cage resolution."""

import json

import pytest

from tests.libs.test_runner import variants
from tests.libs.test_runner.variants import (
    MAX_VARIANT,
    VariantError,
    derive_variant_chain,
    is_well_formed,
    load_full_platform_mapping,
    parse_variant,
    resolve_cage,
    resolve_pair,
    resolve_pairs,
)

from .helpers import FULL, PIPE_LIMITED, PROFILES, make_cage, symmetric_pairs

# m4062nhp shape: 4-way rows only, and no single-lane profile, so no 8x.
STELLER_LIKE = {1: [39, 38, 25, 24, 22], 3: [25], 5: [38, 25, 24, 22], 7: [25]}
# nh4220f shape: 1.6T at full width, breakout profiles only at 4 and 1 lanes.
BLACKKITE_LIKE = {
    1: [90, 39, 38, 24, 22, 23], 2: [23], 3: [23], 4: [23],
    5: [38, 24, 22, 23], 6: [23], 7: [23], 8: [23],
}

CAGES = {"eth1/1": make_cage(FULL, base_id=100), "eth1/2": make_cage(FULL, base_id=200)}
NO_CONSTRAINTS: dict = {}

CHAIN = derive_variant_chain(CAGES)
V2X400 = parse_variant("2x400G", CHAIN)
V4X200 = parse_variant("4x200G", CHAIN)
V8X100 = parse_variant("8x100G", CHAIN)


def _chain_names(subports):
    return [v.name for v in derive_variant_chain({"eth1/1": make_cage(subports)})]


class TestVocabulary:
    def test_chain_from_full_breakout_cage(self):
        assert [v.name for v in CHAIN] == ["max", "2x400G", "4x200G", "8x100G"]
        assert CHAIN[0].is_max

    def test_chain_steller_like_has_no_8x(self):
        assert _chain_names(STELLER_LIKE) == ["max", "2x400G", "2x200G", "2x100G", "4x200G"]

    def test_chain_blackkite_like_offers_what_it_can_program(self):
        # 1.6T platform: reachable only as max, since no 800G-over-4-lane or
        # 200G-over-2-lane profile exists. 2x400G and 8x100G do work.
        assert _chain_names(BLACKKITE_LIKE) == ["max", "2x400G", "2x200G", "2x100G", "8x100G"]

    def test_chain_unions_across_cages(self):
        # Each cage contributes a variant the other cannot do: only the
        # Steller-shaped cage offers 4x200G, only the Black-Kite-shaped one
        # offers 8x100G.
        steller, blackkite = make_cage(STELLER_LIKE), make_cage(BLACKKITE_LIKE, base_id=200)
        assert "8x100G" not in _chain_names(STELLER_LIKE)
        assert "4x200G" not in _chain_names(BLACKKITE_LIKE)
        both = [v.name for v in derive_variant_chain({"eth1/1": steller, "eth1/2": blackkite})]
        assert "4x200G" in both and "8x100G" in both

    def test_chain_empty_without_cages(self):
        assert [v.name for v in derive_variant_chain({})] == ["max"]

    def test_parse_case_insensitive(self):
        assert parse_variant("2X400g", CHAIN) == V2X400
        assert parse_variant("MAX", CHAIN) == MAX_VARIANT

    def test_parse_unsupported_lists_chain(self):
        with pytest.raises(VariantError, match="max, 2x400G, 4x200G, 8x100G"):
            parse_variant("3x300G", CHAIN)

    def test_off_chain_variant_is_still_well_formed(self):
        # Callers use this split to SKIP an unsupported variant but fail a typo.
        bk = derive_variant_chain({"eth1/1": make_cage(BLACKKITE_LIKE)})
        with pytest.raises(VariantError):
            parse_variant("4x200G", bk)
        assert is_well_formed("4x200G")

    def test_well_formed(self):
        assert is_well_formed("2x400G")
        assert is_well_formed("2x1T")
        assert is_well_formed("max")
        assert not is_well_formed("fast")
        assert not is_well_formed("400G")


class TestFullMappingLoader:
    def _write_mapping(self, tmp_path, monkeypatch):
        mapping = {
            "platformSupportedProfiles": [
                {"factor": {"profileID": pid}, "profile": {"speed": speed, "iphy": {"numLanes": lanes}}}
                for pid, (speed, lanes) in PROFILES.items()
            ],
            "ports": {},
        }
        next_id = 1
        for cage, subports in (("eth1/1", FULL), ("eth1/3", PIPE_LIMITED)):
            for sub, pids in subports.items():
                name = f"{cage}/{sub}"
                pins = [{"a": {"lane": i}} for i in range(8 if sub == 1 else 1)]
                if cage == "eth1/1":
                    for pin in pins:
                        pin["a"]["chip"] = "NPU-TH5_NIF-slot1/chip1/core7"
                mapping["ports"][str(next_id)] = {
                    "mapping": {"id": next_id, "name": name, "pins": pins},
                    "supportedProfiles": {str(pid): {} for pid in pids + ([90, 91] if sub == 1 else [])},
                }
                next_id += 1
        mapping["ports"]["999"] = {
            "mapping": {"id": 999, "name": "rcy1/1/529", "pins": [{}]},
            "supportedProfiles": {"23": {}},
        }
        base = tmp_path / "fboss/configs/platforms/nexthop/unitplat/platform_mapping/generated"
        base.mkdir(parents=True)
        (base / "platform_mapping.json").write_text(json.dumps(mapping))
        monkeypatch.setattr("tests.libs.test_runner.platform_mapping.repo_dir", lambda rel: tmp_path / rel)

    def test_loader_keeps_subports_and_lane_counts(self, tmp_path, monkeypatch):
        self._write_mapping(tmp_path, monkeypatch)
        cages = load_full_platform_mapping("unitplat")
        assert set(cages) == {"eth1/1", "eth1/3"}
        full = cages["eth1/1"]
        assert full.lanes == 8
        assert set(full.subports) == set(FULL)
        assert full.subports[1].profiles[39] == (800000, 8)
        # 1.6T is within the profile-speed ceiling and kept; 3.2T is above it.
        assert full.subports[1].profiles[90] == (1600000, 8)
        assert 91 not in full.subports[1].profiles
        # Pipe-limited cage retains only its mapped rows.
        assert set(cages["eth1/3"].subports) == {1, 5}
        # The core comes from the chip name; pins without one leave it unset.
        assert full.core == 7
        assert cages["eth1/3"].core is None

    def test_loader_rules_out_missing_subports(self, tmp_path, monkeypatch):
        self._write_mapping(tmp_path, monkeypatch)
        cages = load_full_platform_mapping("unitplat")
        pairs = {"eth1/1/1": "eth1/3/1", "eth1/3/1": "eth1/1/1"}
        two = resolve_pairs(pairs, V2X400, cages, NO_CONSTRAINTS, {})
        assert two.supported == 1
        four = resolve_pairs(pairs, V4X200, cages, NO_CONSTRAINTS, {})
        assert four.supported == 0 and four.excluded_by_reason == {"platform": 1}


class TestResolvePair:
    def test_happy_path_4x_slots(self):
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, NO_CONSTRAINTS, {})
        assert res.ok
        assert res.subport_pairs == [
            ("eth1/1/1", "eth1/2/1"),
            ("eth1/1/3", "eth1/2/3"),
            ("eth1/1/5", "eth1/2/5"),
            ("eth1/1/7", "eth1/2/7"),
        ]
        assert set(res.profile_by_port.values()) == {25}

    def test_happy_path_8x(self):
        res = resolve_pair("eth1/1/1", "eth1/2/1", V8X100, CAGES, NO_CONSTRAINTS, {})
        assert res.ok and len(res.subport_pairs) == 8

    def test_platform_missing_subport(self):
        cages = {"eth1/1": make_cage(FULL), "eth1/2": make_cage(PIPE_LIMITED)}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, cages, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "platform"

    def test_platform_missing_cage(self):
        res = resolve_pair("eth1/1/1", "eth1/9/1", V2X400, CAGES, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "platform"

    def test_module_explicit_list_excludes(self):
        host_speeds = {"eth1/2/1": [100000, 800000]}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, host_speeds, {})
        assert not res.ok and res.reason == "module"

    @pytest.mark.parametrize("value", [None, []])
    def test_module_none_or_empty_unconstrained(self, value):
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V4X200, CAGES, {"eth1/1/1": value, "eth1/2/1": value}, {}
        )
        assert res.ok

    def test_module_both_peers_checked_independently(self):
        host_speeds = {"eth1/1/1": [200000], "eth1/2/1": [100000]}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, host_speeds, {})
        assert not res.ok and res.reason == "module" and "eth1/2/1" in res.detail

    def test_module_host_apps_need_the_subport_lane_count(self):
        # 2x400G runs 400G over 4 host lanes; 400G over 2 (200G/lane) cannot carry it
        # even though host_speeds alone would accept it.
        a1t6 = [(200000, 1), (400000, 2), (800000, 4), (1600000, 8)]
        speeds = {"eth1/1/1": [200000, 400000, 800000, 1600000]}
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V2X400, CAGES, speeds, {}, host_apps={"eth1/1/1": a1t6}
        )
        assert not res.ok and res.reason == "module"
        assert res.detail == (
            "eth1/1/1 module advertises 200Gx1, 400Gx2, 800Gx4, 1600Gx8, not 400G over 4 lanes"
        )

    def test_module_host_apps_match_is_ok(self):
        host_apps = {"eth1/1/1": [(400000, 4), (800000, 8)], "eth1/2/1": [(400000, 4)]}
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V2X400, CAGES, NO_CONSTRAINTS, {}, host_apps=host_apps
        )
        assert res.ok

    def test_module_host_apps_take_precedence_over_host_speeds(self):
        # host_speeds alone would exclude this port; the lane-aware host_apps wins.
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V2X400, CAGES,
            {"eth1/1/1": [800000]}, {}, host_apps={"eth1/1/1": [(400000, 4)]},
        )
        assert res.ok

    @pytest.mark.parametrize("host_apps", [None, {}, {"eth1/2/1": None}, {"eth1/2/1": []}])
    def test_module_falls_back_to_host_speeds_without_host_apps(self, host_apps):
        speeds = {"eth1/2/1": [100000, 800000]}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, speeds, {}, host_apps=host_apps)
        assert not res.ok and res.reason == "module"

    def test_module_host_apps_both_peers_checked_independently(self):
        host_apps = {"eth1/1/1": [(100000, 1)], "eth1/2/1": [(200000, 1)]}
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V8X100, CAGES, NO_CONSTRAINTS, {}, host_apps=host_apps
        )
        assert not res.ok and res.reason == "module" and "eth1/2/1" in res.detail

    def test_passive_cu_lane_cap_applies_when_host_apps_match(self):
        # A passive DAC can advertise a lane rate it cannot carry; the cap still excludes it.
        host_apps = {"eth1/1/1": [(100000, 1)], "eth1/2/1": [(100000, 1)]}
        media_tech = {"eth1/1/1": "PASSIVE_CU", "eth1/2/1": "OPTICAL_SMF"}
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V8X100, CAGES, NO_CONSTRAINTS, {},
            host_apps=host_apps, media_tech=media_tech, max_passive_cu_lane_speed=50_000,
        )
        assert not res.ok and res.reason == "cable" and "eth1/1/1" in res.detail
        uncapped = resolve_pair(
            "eth1/1/1", "eth1/2/1", V8X100, CAGES, NO_CONSTRAINTS, {},
            host_apps=host_apps, media_tech=media_tech,
        )
        assert uncapped.ok

    def test_resolve_pairs_threads_host_apps(self):
        host_apps = {"eth1/1/1": [(100000, 2)]}
        res = resolve_pairs(
            {"eth1/1/1": "eth1/2/1", "eth1/2/1": "eth1/1/1"},
            V8X100, CAGES, NO_CONSTRAINTS, {}, host_apps=host_apps,
        )
        assert res.supported == 0 and res.excluded_by_reason == {"module": 1}

    def test_peer_profile_mismatch(self, monkeypatch):
        # Give the peer cage a second 200G/2-lane profile so its pick differs.
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {})
        peer_subports = {sub: pids + [26] if sub in (1, 3, 5, 7) else pids for sub, pids in FULL.items()}
        peer = make_cage(peer_subports, base_id=200, profiles={**PROFILES, 26: (200000, 2)})
        cages = {"eth1/1": make_cage(FULL), "eth1/2": peer}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, cages, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "peer"

    def test_copper_requires_copper_profile(self, monkeypatch):
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {25: "optical"})
        is_copper = {"eth1/1/1": True, "eth1/2/1": True}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, NO_CONSTRAINTS, is_copper)
        assert not res.ok and res.reason == "platform"

    def test_optical_cannot_use_copper_profile(self, monkeypatch):
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {25: "copper"})
        is_copper = {"eth1/1/1": False, "eth1/2/1": False}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, NO_CONSTRAINTS, is_copper)
        assert not res.ok and res.reason == "platform"

    def test_optical_can_use_unclassified_profile(self, monkeypatch):
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {})
        is_copper = {"eth1/1/1": False, "eth1/2/1": False}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, NO_CONSTRAINTS, is_copper)
        assert res.ok


class TestResolveCage:
    def test_resolves_without_a_peer(self):
        res = resolve_cage("eth1/1/1", V4X200, CAGES, NO_CONSTRAINTS, {})
        assert res.ok and res.subports == [1, 3, 5, 7] and res.profile_id == 25

    def test_platform_reason_without_the_cage(self):
        res = resolve_cage("eth1/9/1", V4X200, CAGES, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "platform" and not res.subports

    def test_ok_while_its_peer_is_not(self):
        # The case the qsfp self-pairs rely on: one end resolves alone even
        # though the pair does not.
        cages = {"eth1/1": make_cage(FULL), "eth1/2": make_cage(PIPE_LIMITED)}
        assert resolve_cage("eth1/1/1", V4X200, cages, NO_CONSTRAINTS, {}).ok
        assert not resolve_pair("eth1/1/1", "eth1/2/1", V4X200, cages, NO_CONSTRAINTS, {}).ok


class TestResolvePairs:
    PAIRS = {
        "eth1/1/1": "eth1/2/1",
        "eth1/2/1": "eth1/1/1",
        "eth1/3/1": "eth1/4/1",
        "eth1/4/1": "eth1/3/1",
    }
    CAGES4 = {
        "eth1/1": make_cage(FULL, base_id=100),
        "eth1/2": make_cage(FULL, base_id=200),
        "eth1/3": make_cage(PIPE_LIMITED, base_id=300),
        "eth1/4": make_cage(FULL, base_id=400),
    }

    def test_mixed_support_counts_and_expansion(self):
        res = resolve_pairs(self.PAIRS, V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        assert res.total == 2 and res.supported == 1
        assert res.excluded_by_reason == {"platform": 1}
        # Symmetric expanded map, 4 subport pairs = 8 entries.
        assert len(res.expanded_pairs) == 8
        assert res.expanded_pairs["eth1/1/3"] == "eth1/2/3"
        assert res.expanded_pairs["eth1/2/3"] == "eth1/1/3"
        assert res.profile_overrides["eth1/1/3"] == 25
        assert "4x200G" in res.summary("LINK TEST")
        assert "supported=1/2" in res.summary("LINK TEST")
        assert "platform=1" in res.summary("LINK TEST")

    def test_excluded_pairs_are_recorded_symmetrically(self):
        res = resolve_pairs(self.PAIRS, V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        assert res.excluded_pairs == {"eth1/3/1": "eth1/4/1", "eth1/4/1": "eth1/3/1"}
        assert not {"eth1/1/1", "eth1/2/1"} & set(res.excluded_pairs)

    def test_deterministic(self):
        a = resolve_pairs(self.PAIRS, V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        b = resolve_pairs(dict(reversed(list(self.PAIRS.items()))), V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        assert a.expanded_pairs == b.expanded_pairs
        assert a.profile_overrides == b.profile_overrides


class TestDatapathBudget:
    """Two cages share a SerDes datapath and the ASIC allocates it 10 logical
    ports. Breaking both out 8 ways needs 16, so one pair has to stay at max."""

    PAIRS = symmetric_pairs(("eth1/1/1", "eth1/3/1"), ("eth1/2/1", "eth1/4/1"))
    # Cages 1 and 2 share datapath 0 (cores 0 and 1); 3 and 4 share datapath 1.
    CAGES = {
        "eth1/1": make_cage(FULL, base_id=100, core=0),
        "eth1/2": make_cage(FULL, base_id=200, core=1),
        "eth1/3": make_cage(FULL, base_id=300, core=2),
        "eth1/4": make_cage(FULL, base_id=400, core=3),
    }

    def _resolve(self, variant, budget, cages=None, pairs=None):
        return resolve_pairs(
            pairs or self.PAIRS, variant, cages or self.CAGES, NO_CONSTRAINTS, {},
            logical_ports_per_datapath=budget,
        )

    def test_overfull_datapath_drops_the_latest_cable(self):
        res = self._resolve(V8X100, 10)
        assert res.total == 2 and res.supported == 1
        assert res.excluded_by_reason == {"datapath": 1}
        assert res.excluded_pairs == symmetric_pairs(("eth1/2/1", "eth1/4/1"))
        assert set(res.expanded_pairs) == {f"eth1/{c}/{s}" for c in (1, 3) for s in range(1, 9)}
        assert set(res.profile_overrides) == set(res.expanded_pairs)
        assert "datapath=1" in res.summary("LINK TEST")

    def test_dropping_a_cable_frees_both_ends(self):
        # Each pair sits inside one datapath, so dropping a cable frees both
        # of its cages and nothing else has to go.
        pairs = symmetric_pairs(("eth1/1/1", "eth1/2/1"), ("eth1/3/1", "eth1/4/1"))
        res = self._resolve(V8X100, 10, pairs=pairs)
        assert res.supported == 0
        assert res.excluded_by_reason == {"datapath": 2}

    def test_within_budget_keeps_every_pair(self):
        assert self._resolve(V4X200, 10).excluded_by_reason == {}
        assert self._resolve(V8X100, 16).excluded_by_reason == {}

    def test_one_cage_per_datapath_fits_beside_a_filler(self):
        cages = {
            "eth1/1": make_cage(FULL, base_id=100, core=0),
            "eth1/2": make_cage(PIPE_LIMITED, base_id=200, core=1),
            "eth1/3": make_cage(FULL, base_id=300, core=2),
            "eth1/4": make_cage(PIPE_LIMITED, base_id=400, core=3),
        }
        res = self._resolve(V8X100, 10, cages=cages)
        assert res.supported == 1 and res.excluded_by_reason == {"platform": 1}

    def test_excluded_pair_keeps_the_cabled_port_names(self):
        pairs = symmetric_pairs(("eth1/1/5", "eth1/3/5"), ("eth1/2/5", "eth1/4/5"))
        res = self._resolve(V8X100, 10, pairs=pairs)
        assert res.excluded_pairs == symmetric_pairs(("eth1/2/5", "eth1/4/5"))

    def test_fillers_alone_over_budget_is_an_error(self):
        cages = {f"eth1/{i}": make_cage(FULL, base_id=100 * i, core=0) for i in range(1, 13)}
        with pytest.raises(ValueError, match="no breakout left to drop"):
            self._resolve(V8X100, 10, cages=cages, pairs=symmetric_pairs(("eth1/1/1", "eth1/2/1")))

    def test_no_budget_or_no_core_leaves_resolution_alone(self):
        assert self._resolve(V8X100, None).supported == 2
        coreless = {name: make_cage(FULL, base_id=100 * i) for i, name in enumerate(self.CAGES, 1)}
        assert self._resolve(V8X100, 10, cages=coreless).supported == 2

    def test_deterministic(self):
        a = self._resolve(V8X100, 10)
        b = self._resolve(V8X100, 10, pairs=dict(reversed(list(self.PAIRS.items()))))
        assert a.expanded_pairs == b.expanded_pairs
        assert a.excluded_pairs == b.excluded_pairs
