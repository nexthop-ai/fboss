"""Unit tests for speed/breakout variant parsing and per-pair resolution."""

import json
from pathlib import Path

import pytest

from tests.libs.test_runner import QsfpTestRunner, variants
from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.filter_utils import load_test_context
from tests.libs.test_runner.platform_configs import LINK_QSFP_TEST_CONFIG_NAME
from tests.libs.test_runner.platform_mapping import repo_dir
from tests.libs.test_runner.variants import (
    derive_variant_chain,
    is_well_formed,
    load_full_platform_mapping,
    MAX_VARIANT,
    parse_variant,
    resolve_cage,
    resolve_pair,
    resolve_pairs,
    VariantError,
)

# Profile table shared by the fixtures: pid -> (speed, iphy lanes).
_PROFILES = {
    91: (3200000, 8),
    90: (1600000, 8),
    39: (800000, 8),
    38: (400000, 4),
    25: (200000, 2),
    24: (200000, 4),
    23: (100000, 1),
    22: (100000, 4),
}


def _cage(subports, lanes=8, base_id=100):
    return variants.CageInfo(
        controlling="unused/1",
        lanes=lanes,
        subports={
            sub: variants.SubportInfo(base_id + sub, {pid: _PROFILES[pid] for pid in pids})
            for sub, pids in subports.items()
        },
    )


# Full-breakout cage: every subport, profiles matching lane arithmetic.
FULL = {1: [39, 38, 25, 23], 2: [23], 3: [25, 23], 4: [23], 5: [38, 25, 23], 6: [23], 7: [25, 23], 8: [23]}
# Pipe-limited cage: only /1 and /5 rows exist.
PIPE_LIMITED = {1: [39, 38], 5: [38]}
# m4062nhp shape: 4-way rows only, and no single-lane profile, so no 8x.
STELLER_LIKE = {1: [39, 38, 25, 24, 22], 3: [25], 5: [38, 25, 24, 22], 7: [25]}
# nh4220f shape: 1.6T at full width, breakout profiles only at 4 and 1 lanes.
BLACKKITE_LIKE = {
    1: [90, 39, 38, 24, 22, 23], 2: [23], 3: [23], 4: [23],
    5: [38, 24, 22, 23], 6: [23], 7: [23], 8: [23],
}

CAGES = {"eth1/1": _cage(FULL, base_id=100), "eth1/2": _cage(FULL, base_id=200)}
NO_CONSTRAINTS: dict = {}

CHAIN = derive_variant_chain(CAGES)
V2X400 = parse_variant("2x400G", CHAIN)
V4X200 = parse_variant("4x200G", CHAIN)
V8X100 = parse_variant("8x100G", CHAIN)


# Config names the fleet runs: the explicit overrides plus the models that fall
# through _config_name's identity path.
_FLEET_CONFIG_NAMES = sorted(
    set(LINK_QSFP_TEST_CONFIG_NAME.values())
    | {"nh4220f", "nh4010f", "wedge800bnhp", "wedge800cnhp"}
)


def _chain_names(subports):
    return [v.name for v in derive_variant_chain({"eth1/1": _cage(subports)})]


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
        steller, blackkite = _cage(STELLER_LIKE), _cage(BLACKKITE_LIKE, base_id=200)
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
        bk = derive_variant_chain({"eth1/1": _cage(BLACKKITE_LIKE)})
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
                for pid, (speed, lanes) in _PROFILES.items()
            ],
            "ports": {},
        }
        next_id = 1
        for cage, subports in (("eth1/1", FULL), ("eth1/3", PIPE_LIMITED)):
            for sub, pids in subports.items():
                name = f"{cage}/{sub}"
                mapping["ports"][str(next_id)] = {
                    "mapping": {
                        "id": next_id,
                        "name": name,
                        "pins": [{"a": {"lane": i}} for i in range(8 if sub == 1 else 1)],
                    },
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

    def test_loader_rules_out_missing_subports(self, tmp_path, monkeypatch):
        self._write_mapping(tmp_path, monkeypatch)
        cages = load_full_platform_mapping("unitplat")
        pairs = {"eth1/1/1": "eth1/3/1", "eth1/3/1": "eth1/1/1"}
        two = resolve_pairs(pairs, V2X400, cages, NO_CONSTRAINTS, {})
        assert two.supported == 1
        four = resolve_pairs(pairs, V4X200, cages, NO_CONSTRAINTS, {})
        assert four.supported == 0 and four.excluded_by_reason == {"platform": 1}


class TestShippedWrappers:
    """Every variant wrapper file must name a variant a real platform can run.

    Checked against the shipped mappings, not fixtures: the failure this guards
    against is chain derivation drifting away from what platforms actually
    offer, which turns every wrapper into a silent SKIP.
    """

    @staticmethod
    def _wrapper_variants():
        return {
            path.name: load_test_context(str(path)).get("variant")
            for directory in ("tests/link", "tests/qsfp")
            for path in sorted(repo_dir(Path(directory)).glob("*_hw_tests_*.py"))
        }

    def test_every_wrapper_variant_is_offered_by_a_shipped_platform(self):
        offered = set()
        for config_name in _FLEET_CONFIG_NAMES:
            offered.update(
                v.name for v in derive_variant_chain(load_full_platform_mapping(config_name))
            )
        assert offered, "no platform mappings readable; check the test's runfiles"
        wrappers = {n: v for n, v in self._wrapper_variants().items() if v}
        assert wrappers, "no variant wrapper files found"
        unrunnable = {name: v for name, v in wrappers.items() if v not in offered}
        assert not unrunnable, f"wrappers no shipped platform can run: {unrunnable}"


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
        cages = {"eth1/1": _cage(FULL), "eth1/2": _cage(PIPE_LIMITED)}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, cages, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "platform"

    def test_platform_missing_cage(self):
        res = resolve_pair("eth1/1/1", "eth1/9/1", V2X400, CAGES, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "platform"

    def test_module_explicit_list_excludes(self):
        host_speeds = {"eth1/2/1": [100000, 800000]}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, CAGES, host_speeds, {})
        assert not res.ok and res.reason == "module"

    def test_module_none_or_empty_unconstrained(self):
        for value in (None, []):
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

    def test_module_falls_back_to_host_speeds_without_host_apps(self):
        speeds = {"eth1/2/1": [100000, 800000]}
        for host_apps in (None, {}, {"eth1/2/1": None}, {"eth1/2/1": []}):
            res = resolve_pair(
                "eth1/1/1", "eth1/2/1", V4X200, CAGES, speeds, {}, host_apps=host_apps
            )
            assert not res.ok and res.reason == "module", host_apps

    def test_module_host_apps_both_peers_checked_independently(self):
        host_apps = {"eth1/1/1": [(100000, 1)], "eth1/2/1": [(200000, 1)]}
        res = resolve_pair(
            "eth1/1/1", "eth1/2/1", V8X100, CAGES, NO_CONSTRAINTS, {}, host_apps=host_apps
        )
        assert not res.ok and res.reason == "module" and "eth1/2/1" in res.detail

    def test_resolve_pairs_threads_host_apps(self):
        host_apps = {"eth1/1/1": [(100000, 2)]}
        res = resolve_pairs(
            {"eth1/1/1": "eth1/2/1", "eth1/2/1": "eth1/1/1"},
            V8X100, CAGES, NO_CONSTRAINTS, {}, host_apps=host_apps,
        )
        assert res.supported == 0 and res.excluded_by_reason == {"module": 1}

    def test_peer_profile_mismatch(self, monkeypatch):
        # Give the peer cage a second 200G/2-lane profile so its pick differs.
        alt = dict(_PROFILES)
        alt[26] = (200000, 2)
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {})
        peer_subports = {sub: list(pids) for sub, pids in FULL.items()}
        for sub in (1, 3, 5, 7):
            peer_subports[sub] = peer_subports[sub] + [26]
        peer = variants.CageInfo(
            controlling="eth1/2/1",
            lanes=8,
            subports={
                sub: variants.SubportInfo(200 + sub, {pid: alt[pid] for pid in pids})
                for sub, pids in peer_subports.items()
            },
        )
        cages = {"eth1/1": _cage(FULL), "eth1/2": peer}
        res = resolve_pair("eth1/1/1", "eth1/2/1", V4X200, cages, NO_CONSTRAINTS, {})
        assert not res.ok and res.reason == "peer"

    def test_copper_requires_copper_profile(self, monkeypatch):
        monkeypatch.setattr(variants, "_profile_medium_by_id", lambda: {25: "optical"})
        is_copper = {"eth1/1/1": True, "eth1/2/1": True}
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
        cages = {"eth1/1": _cage(FULL), "eth1/2": _cage(PIPE_LIMITED)}
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
        "eth1/1": _cage(FULL, base_id=100),
        "eth1/2": _cage(FULL, base_id=200),
        "eth1/3": _cage(PIPE_LIMITED, base_id=300),
        "eth1/4": _cage(FULL, base_id=400),
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

    def test_deterministic(self):
        a = resolve_pairs(self.PAIRS, V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        b = resolve_pairs(dict(reversed(list(self.PAIRS.items()))), V4X200, self.CAGES4, NO_CONSTRAINTS, {})
        assert a.expanded_pairs == b.expanded_pairs
        assert a.profile_overrides == b.profile_overrides


class TestVariantSkipReporting:
    """A variant this DUT cannot run reports as skipped, not as an infra error.

    A bare pytest skip leaves no tr.xml and the executor turns that into
    FILE_ERR, which would brand every platform that lacks a variant as broken.
    """

    def _runner(self, monkeypatch, variant):
        runner = QsfpTestRunner()
        runner.tc = {"variant": variant, "model": "unused"}
        recorded = {}
        monkeypatch.setattr(
            runner,
            "_merge_junit_results",
            lambda passes, skipped=(): recorded.update(passes=list(passes), skipped=list(skipped)),
        )
        monkeypatch.setattr(
            runner, "normalize_test_results_file", lambda: recorded.update(normalized=True)
        )
        monkeypatch.delenv("TEST_PORTS_INFO", raising=False)
        return runner, recorded

    def test_unsupported_variant_writes_skipped_junit(self, monkeypatch):
        runner, recorded = self._runner(monkeypatch, "2x400G")
        assert runner._run_test_impl({}, skip_tr_xml=False) is True
        assert recorded["passes"] == []
        assert recorded["skipped"] == [
            ("2x400G", "variant runs require TEST_PORTS_INFO cabling data")
        ]
        assert recorded["normalized"]

    def test_skip_writes_no_junit_when_caller_owns_the_xml(self, monkeypatch):
        runner, recorded = self._runner(monkeypatch, "2x400G")
        assert runner._run_test_impl({}, skip_tr_xml=True) is True
        assert not recorded

    def test_malformed_variant_is_a_hard_error(self, monkeypatch):
        # A typo must not masquerade as missing coverage, so it has to escape
        # the skip path even though an unsupported-but-valid name does not.
        runner, _ = self._runner(monkeypatch, "fast")
        monkeypatch.setenv("TEST_PORTS_INFO", "ports.json")
        monkeypatch.setattr(runner, "_load_cabling", lambda path: ([], [], {}))
        monkeypatch.setattr(
            runner, "_full_platform_mapping", lambda config_name: {"eth1/1": _cage(FULL)}
        )
        runner.tc["model"] = "NH-BW800-F"
        with pytest.raises(VariantError):
            runner._run_test_impl({}, skip_tr_xml=False)

    def test_explicit_max_matches_an_absent_key(self, monkeypatch):
        explicit, _ = self._runner(monkeypatch, "max")
        absent, _ = self._runner(monkeypatch, None)
        assert explicit._is_variant_run() is absent._is_variant_run() is False

    def test_max_run_never_loads_the_platform_mapping(self, monkeypatch):
        # A model whose mapping is missing still has to run at max.
        runner, _ = self._runner(monkeypatch, None)
        monkeypatch.setenv("TEST_PORTS_INFO", "ports.json")
        monkeypatch.setattr(runner, "_load_cabling", lambda path: ([], [], {}))
        def _boom(config_name):
            raise AssertionError("max path must not load the platform mapping")
        monkeypatch.setattr(runner, "_full_platform_mapping", _boom)
        runner.tc["model"] = "NH-BW800-F"
        assert runner._requested_variant("wedge800bact").is_max

    def test_unusable_mapping_is_an_error_not_a_skip(self, monkeypatch):
        # A mapping that parses to nothing means schema drift, which must not
        # look like "this platform does not offer the variant".
        runner, _ = self._runner(monkeypatch, "2x400G")
        monkeypatch.setattr(runner, "_full_platform_mapping", lambda config_name: {})
        with pytest.raises(RuntimeError, match="yielded no cages"):
            runner._requested_variant("wedge800bact")

    def test_max_run_is_untouched(self, monkeypatch):
        runner, recorded = self._runner(monkeypatch, None)
        monkeypatch.setattr(
            BaseHwTestRunner, "_run_test_impl", lambda self, tc, skip_tr_xml=False: "ran"
        )
        assert runner._run_test_impl({}, skip_tr_xml=False) == "ran"
        assert not recorded


class TestLoadCablingHostApps:
    def test_host_apps_load_as_tuples_and_missing_is_unknown(self, tmp_path):
        ports_info = tmp_path / "ports_info.json"
        ports_info.write_text(json.dumps({
            "eth1/1/1": {"media_technology": "PASSIVE_CU", "host_apps": [[400000, 2], [800000, 4]]},
            "eth1/2/1": {"media_technology": "PASSIVE_CU", "host_apps": None},
            "eth1/3/1": {"media_technology": "PASSIVE_CU", "host_apps": []},
            "eth1/4/1": {"media_technology": "PASSIVE_CU"},
        }))
        runner = QsfpTestRunner()
        runner._load_cabling(str(ports_info))
        assert runner._host_apps_by_port == {
            "eth1/1/1": [(400000, 2), (800000, 4)],
            "eth1/2/1": None,
            "eth1/3/1": None,
            "eth1/4/1": None,
        }
