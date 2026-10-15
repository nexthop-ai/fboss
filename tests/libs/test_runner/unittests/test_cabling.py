"""CablingAwareRunnerMixin: ports-info parsing, gtest filter splitting and
bucketing, variant gating, and the multi-pass run _run_cabling_aware drives.

The runner-specific gates it calls into (LinkTestRunner's media and PTP gates,
QsfpTestRunner's strict eligibility) are tested with their runners; here they
are either the mixin's no-op defaults or stubbed.
"""

import json
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from tests.libs.test_runner import LinkTestRunner, QsfpTestRunner, cabling
from tests.libs.test_runner import base as base_module
from tests.libs.test_runner import junit
from tests.libs.test_runner.base import BaseHwTestRunner
from tests.libs.test_runner.cabling import neighbor_pairs
from tests.libs.test_runner.variants import VariantError

from .helpers import (
    FULL,
    drive_cabling_aware,
    make_cabling_runner,
    make_cage,
    make_port,
    make_runner,
    symmetric_pairs,
)

_PORTS_INFO = {
    "eth1/1/1": {"media_technology": "PASSIVE_CU"},
    "eth1/2/1": {"media_technology": "OPTICAL_SMF"},
}


class TestLoadJsonPairs:
    def test_missing_path_is_empty(self):
        assert cabling._load_json_pairs(None) == {}
        assert cabling._load_json_pairs("/does/not/exist.json") == {}

    def test_reads_pairs(self, tmp_path):
        path = tmp_path / "pairs.json"
        pairs = symmetric_pairs(("eth1/1/1", "eth1/2/1"))
        path.write_text(json.dumps(pairs))
        assert cabling._load_json_pairs(str(path)) == pairs


class TestNeighborPairs:
    def test_pairs_cabled_ports_once_each(self):
        pairs = symmetric_pairs(("eth1/1/1", "eth1/2/1"), ("eth1/3/1", "eth1/4/1"))
        assert neighbor_pairs(["eth1/1/1", "eth1/2/1", "eth1/3/1", "eth1/4/1"], pairs) == [
            ("eth1/1/1", "eth1/2/1"),
            ("eth1/3/1", "eth1/4/1"),
        ]

    def test_peer_outside_the_pass_is_not_paired(self):
        assert neighbor_pairs(["eth1/1/1"], symmetric_pairs(("eth1/1/1", "eth1/2/1"))) == []

    def test_no_pairs_data(self):
        assert neighbor_pairs(["eth1/1/1", "eth1/2/1"], {}) == []


class TestLoadCabling:
    def test_classifies_ports_and_infers_medium(self, tmp_path):
        ports_info = {
            "eth1/1/1": {"media_technology": "PASSIVE_CU", "transmitter_technology": "COPPER", "media_interface": "CR8_800G"},
            "eth1/2/1": {"media_technology": "OPTICAL_SMF", "transmitter_technology": "OPTICAL", "media_interface": "FR8_800G"},
            "eth1/3/1": {"media_technology": "ACTIVE_CU", "transmitter_technology": "BACKPLANE"},
            # UNKNOWN transmitter falls back to media_technology (loopback plugs).
            "eth1/4/1": {"media_technology": "PASSIVE_CU", "transmitter_technology": "UNKNOWN"},
            "eth1/5/1": {"media_technology": "OPTICAL_MMF", "transmitter_technology": "UNKNOWN"},
            "eth1/6/1": {},
        }
        path = tmp_path / "ports_info.json"
        path.write_text(json.dumps(ports_info))
        runner = QsfpTestRunner()

        all_ports, optics_ports, media_by_port = runner._load_cabling(str(path))

        assert all_ports == list(ports_info)
        assert optics_ports == ["eth1/2/1", "eth1/3/1", "eth1/5/1"]
        assert media_by_port == {
            "eth1/1/1": "CR8_800G", "eth1/2/1": "FR8_800G", "eth1/3/1": None,
            "eth1/4/1": None, "eth1/5/1": None, "eth1/6/1": None,
        }
        assert runner._is_copper_by_port == {
            "eth1/1/1": True, "eth1/2/1": False, "eth1/3/1": False,
            "eth1/4/1": True, "eth1/5/1": False, "eth1/6/1": None,
        }
        assert runner._media_tech_by_port["eth1/4/1"] == "PASSIVE_CU"
        assert runner._transmitter_tech_by_port["eth1/4/1"] == "UNKNOWN"

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

    def test_unreadable_file_raises(self, tmp_path):
        bad = tmp_path / "ports_info.json"
        bad.write_text("{not json")
        with pytest.raises(RuntimeError, match="Failed to load ports-info file"):
            QsfpTestRunner()._load_cabling(str(bad))
        with pytest.raises(RuntimeError, match="Failed to load ports-info file"):
            QsfpTestRunner()._load_cabling(str(tmp_path / "missing.json"))


class TestSplitFilters:
    def test_three_buckets_by_substring(self):
        copper, strict, optics = QsfpTestRunner._split_filters(
            ["*PortStatus*", "*CheckPortsProgrammed*", "*i2cStressWrite*", "*cmisPageChange*"]
        )
        assert copper == ["*PortStatus*"]
        assert strict == ["*CheckPortsProgrammed*"]
        assert optics == ["*i2cStressWrite*", "*cmisPageChange*"]

    def test_optics_only_wins_over_strict(self):
        _, strict, optics = QsfpTestRunner._split_filters(["*i2cStressWrite*CheckPortsProgrammed*"])
        assert strict == [] and optics == ["*i2cStressWrite*CheckPortsProgrammed*"]


class TestParseGtestFilter:
    @pytest.mark.parametrize("expr, patterns, suffix", [
        ("*A*:*B*", ["*A*", "*B*"], ""),
        ("*A*:*B*-*C*:*D*", ["*A*", "*B*"], "-*C*:*D*"),
        ("-*C*", ["*"], "-*C*"),
        ("*A*::*B*", ["*A*", "*B*"], ""),
        ("", [], ""),
    ])
    def test_positive_patterns_and_negative_suffix(self, expr, patterns, suffix):
        assert QsfpTestRunner._parse_gtest_filter(expr) == (patterns, suffix)

    def test_bucket_expressions_rejoin_with_shared_suffix(self):
        assert QsfpTestRunner._bucket_expressions(["*A*", "*i2cStressWrite*", "*B*"], "-*C*") == (
            "*A*:*B*-*C*", "", "*i2cStressWrite*-*C*"
        )
        assert QsfpTestRunner._bucket_expressions([], "-*C*") == ("", "", "")


class TestSplitGtestFilter:
    """_split_gtest_filter() classifies a single --gtest_filter expression's
    colon-separated positive patterns the same way _split_filters() classifies
    tc["filters"], so a mixed TESTFILTER can still run as two cabling-aware
    passes (see TestCablingAwareGtestFilterSplit below) instead of collapsing
    into one pass with the wrong (or an empty) port set."""

    def test_pure_copper_safe_stays_one_expression(self):
        copper, _, optics = LinkTestRunner._split_gtest_filter("*PortStatus*:*Vlan*")
        assert copper == "*PortStatus*:*Vlan*"
        assert optics == ""

    def test_pure_optics_only(self):
        copper, _, optics = LinkTestRunner._split_gtest_filter("*verifyTxRxLatches*")
        assert copper == ""
        assert optics == "*verifyTxRxLatches*"

    def test_mixed_splits_and_shares_negative_suffix(self):
        copper, _, optics = LinkTestRunner._split_gtest_filter(
            "*PortStatus*:*verifyTxRxLatches*-*Foo*:*Bar*"
        )
        assert copper == "*PortStatus*-*Foo*:*Bar*"
        assert optics == "*verifyTxRxLatches*-*Foo*:*Bar*"

    def test_negative_only_implies_wildcard_positive(self):
        # gtest treats a bare "-pattern" as "everything except pattern"; an
        # empty positive side here must not be read as "no tests selected".
        copper, _, optics = LinkTestRunner._split_gtest_filter("-*verifyTxRxLatches*")
        assert copper == "*-*verifyTxRxLatches*"
        assert optics == ""

    def test_qsfp_runner_uses_its_own_optics_only_substrings(self):
        copper, _, optics = QsfpTestRunner._split_gtest_filter("*PortStatus*:*i2cStressWrite*")
        assert copper == "*PortStatus*"
        assert optics == "*i2cStressWrite*"


class TestPassLocalPaths:
    def test_named_after_runner_and_label(self):
        assert QsfpTestRunner()._pass_local_paths("optics") == (
            "/tmp/qsfptestrunner_test_optics.log", "/tmp/qsfptestrunner_tr_optics.xml"
        )


_MIXED_FILTER_CASES = (
    (QsfpTestRunner, "*PortStatus*:*i2cStressWrite*-*Foo*",
     "*PortStatus*-*Foo*", "*i2cStressWrite*-*Foo*"),
    (LinkTestRunner, "*PortStatus*:*verifyTxRxLatches*-*Foo*",
     "*PortStatus*-*Foo*", "*verifyTxRxLatches*-*Foo*"),
)


class TestCablingAwareGtestFilterSplit:
    """_run_cabling_aware() with a TESTFILTER override set runs the matching
    split against the real cabled ports, like the filters-list mode does."""

    @pytest.mark.parametrize(
        "runner_cls, gtest_filter, expected_copper, expected_optics", _MIXED_FILTER_CASES
    )
    def test_mixed_filter_runs_two_passes_against_matching_ports(
        self, runner_cls, gtest_filter, expected_copper, expected_optics, tmp_path
    ):
        runner, cabling_path = make_cabling_runner(runner_cls, tmp_path, _PORTS_INFO, gtest_filter=gtest_filter)

        run = drive_cabling_aware(runner, cabling_path, skip_tr_xml=True)

        assert run.result is True
        assert run.prepare_calls == [
            ("m4062nhp", ["eth1/1/1", "eth1/2/1"]),
            ("m4062nhp", ["eth1/2/1"]),
        ]
        assert run.execute_calls == [expected_copper, expected_optics]
        # The override key is restored to the original mixed expression afterwards.
        assert runner.tc["gtest_filter"] == gtest_filter

    @pytest.mark.parametrize(
        "runner_cls, optics_only_filter",
        [(QsfpTestRunner, "*i2cStressWrite*"), (LinkTestRunner, "*verifyTxRxLatches*")],
    )
    def test_optics_only_filter_skips_cleanly_when_dut_has_no_optics(
        self, runner_cls, optics_only_filter, tmp_path
    ):
        runner, cabling_path = make_cabling_runner(
            runner_cls, tmp_path, {"eth1/1/1": {"media_technology": "PASSIVE_CU"}},
            gtest_filter=optics_only_filter,
        )

        run = drive_cabling_aware(runner, cabling_path)

        assert run.result is True
        assert run.prepare_calls == [] and run.execute_calls == []
        assert run.skipped == [(optics_only_filter, "no optical/active transceivers cabled on this DUT")]

    def test_earlier_pass_failure_records_whole_expression_as_skipped(self, tmp_path):
        runner, cabling_path = make_cabling_runner(
            LinkTestRunner, tmp_path, _PORTS_INFO, gtest_filter="*PortStatus*:*verifyTxRxLatches*"
        )

        run = drive_cabling_aware(runner, cabling_path, execute_result=False)

        assert run.result is False
        assert run.execute_calls == ["*PortStatus*"]
        # The whole remaining expression, not its characters, is what gets skipped.
        assert run.skipped == [("*verifyTxRxLatches*", "earlier pass failed; run aborted")]

    def test_nothing_to_run_returns_true(self, tmp_path):
        runner, cabling_path = make_cabling_runner(QsfpTestRunner, tmp_path, _PORTS_INFO, filters=[])
        run = drive_cabling_aware(runner, cabling_path)
        assert run.result is True
        assert run.prepare_calls == [] and run.execute_calls == [] and run.skipped is None


class TestGateFiltersDefault:
    def test_base_mixin_gate_is_noop(self):
        # QsfpTestRunner inherits _gate_filters from the mixin unmodified: media
        # data flowing through TEST_PORTS_INFO doesn't change QSFP behaviour.
        kept, skipped = QsfpTestRunner()._gate_filters(
            ["*Foo*", "*Prbs*FR4_400G*"], {"eth1/1/1": "FR4_400G"}, ["eth1/1/1"]
        )
        assert kept == ["*Foo*", "*Prbs*FR4_400G*"]
        assert skipped == []


_STRICT = "*CheckPortsProgrammed*"
_STRICT_PORT_MAP = {"eth1/1/1": make_port(1, 50), "eth1/2/1": make_port(2, 39)}


class TestStrictPass:
    """The media-strict bucket runs as its own pass against only the ports
    whose module self-reporting a profile can satisfy, and is reported skipped
    when there are none."""

    @pytest.fixture(autouse=True)
    def _tables(self, profile_tables):
        pass

    def _runner(self, tmp_path, monkeypatch, ports_info):
        runner, cabling_path = make_cabling_runner(
            QsfpTestRunner, tmp_path, ports_info, filters=["*PortStatus*", _STRICT], monkeypatch=monkeypatch
        )
        monkeypatch.setattr(
            runner, "_load_base_config_and_port_map", lambda base_dir, config_name: ({}, _STRICT_PORT_MAP)
        )
        return runner, cabling_path

    def test_strict_pass_runs_against_verifiable_ports_only(self, tmp_path, monkeypatch):
        ports_info = {
            "eth1/1/1": {"media_technology": "PASSIVE_CU", "transmitter_technology": "COPPER", "media_interface": "CR8_800G"},
            "eth1/2/1": {"media_technology": "OPTICAL_SMF", "transmitter_technology": "OPTICAL", "media_interface": "FR8_800G"},
            # Reports nothing usable, so the strict verifiers cannot pass on it.
            "eth1/3/1": {},
        }
        runner, cabling_path = self._runner(tmp_path, monkeypatch, ports_info)

        run = drive_cabling_aware(runner, cabling_path)

        assert run.result is True
        assert run.prepare_calls == [
            ("m4062nhp", ["eth1/1/1", "eth1/2/1", "eth1/3/1"]),
            ("m4062nhp", ["eth1/1/1", "eth1/2/1"]),
        ]
        assert run.execute_calls == [["*PortStatus*"], [_STRICT]]
        assert run.skipped == []

    def test_no_verifiable_port_skips_the_strict_bucket(self, tmp_path, monkeypatch):
        runner, cabling_path = self._runner(tmp_path, monkeypatch, {"eth1/3/1": {}})

        run = drive_cabling_aware(runner, cabling_path)

        assert run.result is True
        assert run.prepare_calls == [("m4062nhp", ["eth1/3/1"])]
        assert run.execute_calls == [["*PortStatus*"]]
        assert run.skipped == [(_STRICT, "no ports with a verifiable media profile on this DUT")]

    def test_gtest_filter_strict_bucket_is_skipped_whole(self, tmp_path, monkeypatch):
        runner, cabling_path = self._runner(tmp_path, monkeypatch, {"eth1/3/1": {}})
        runner.tc["gtest_filter"] = f"*PortStatus*:{_STRICT}-*Foo*"

        run = drive_cabling_aware(runner, cabling_path)

        assert run.execute_calls == ["*PortStatus*-*Foo*"]
        assert run.skipped == [(f"{_STRICT}-*Foo*", "no ports with a verifiable media profile on this DUT")]


class TestJunitEndToEnd:
    """One cabling-aware run with the real JUnit merge and normalization, not
    the mocks the other tests use, so the files the orchestrator reads are
    produced the way it will see them."""

    def test_all_skipped_run_writes_skipped_testcases(self, tmp_path, monkeypatch):
        log_path, xml_path = tmp_path / "test.log", tmp_path / "tr.xml"
        real_merge, real_normalize = junit.merge_junit_results, junit.normalize_test_results_file
        monkeypatch.setattr(
            base_module.junit, "merge_junit_results",
            lambda passes, skipped=(): real_merge(passes, skipped, str(log_path), str(xml_path)),
        )
        monkeypatch.setattr(
            base_module.junit, "normalize_test_results_file",
            lambda suite_name, _xml="/tmp/tr.xml": real_normalize(suite_name, str(xml_path)),
        )
        runner, cabling_path = make_cabling_runner(
            QsfpTestRunner, tmp_path, {"eth1/1/1": {"media_technology": "PASSIVE_CU"}},
            filters=["*i2cStressWrite*"],
        )
        runner.tc["filepath"] = "t0_qsfp_hw_tests"

        with patch.object(runner, "_prepare_pass"), patch.object(runner, "pre_test"), \
             patch.object(runner, "post_test"), patch.object(runner, "_execute_test_binary") as execute:
            assert runner._run_cabling_aware(cabling_path, {}, skip_tr_xml=False) is True

        execute.assert_not_called()
        suite = ET.parse(xml_path).getroot().find("testsuite")
        assert suite.get("name") == "t0_qsfp_hw_tests"
        assert (suite.get("tests"), suite.get("skipped")) == ("1", "1")
        assert suite.get("timestamp")
        [case] = suite.findall("testcase")
        assert case.get("name") == "Skipped.i2cStressWrite"
        assert case.find("skipped").get("message") == "no optical/active transceivers cabled on this DUT"
        assert "pass skipped" in log_path.read_text()


class TestRunTimeout:
    def test_scaled_timeout_floors_at_default_and_grows_with_ports(self):
        assert cabling._scaled_test_run_timeout(32) == 1200
        assert cabling._scaled_test_run_timeout(128) == 1920

    @pytest.mark.parametrize("runner_cls", [QsfpTestRunner, LinkTestRunner])
    def test_cabling_aware_run_scales_flag_by_cabled_ports(self, runner_cls, tmp_path):
        ports_info = {f"eth1/{i}/1": {"media_technology": "PASSIVE_CU"} for i in range(1, 129)}
        runner, cabling_path = make_cabling_runner(runner_cls, tmp_path, ports_info, gtest_filter="*PortStatus*")
        run = drive_cabling_aware(runner, cabling_path, skip_tr_xml=True, capture_cmds=True)
        assert run.result is True
        assert run.commands and all("--test-run-timeout 1920" in c for c in run.commands)


class TestAgentSettleAcrossPasses:
    def test_multi_pass_run_waits_before_every_pass(self, tmp_path):
        runner, cabling_path = make_cabling_runner(
            QsfpTestRunner, tmp_path, _PORTS_INFO,
            gtest_filter="*PortStatus*:*CheckPortsProgrammed*:*i2cStressWrite*",
        )
        run = drive_cabling_aware(runner, cabling_path, skip_tr_xml=True)
        assert run.result is True
        assert len(run.execute_calls) == 3
        assert run.settle_waits == 3

    def test_single_pass_cabling_run_waits_once(self, tmp_path):
        runner, cabling_path = make_cabling_runner(QsfpTestRunner, tmp_path, _PORTS_INFO, gtest_filter="*PortStatus*")
        run = drive_cabling_aware(runner, cabling_path, skip_tr_xml=True)
        assert run.result is True
        assert run.settle_waits == 1


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
            runner, "_full_platform_mapping", lambda config_name: {"eth1/1": make_cage(FULL)}
        )
        runner.tc["model"] = "NH-BW800-F"
        with pytest.raises(VariantError):
            runner._run_test_impl({}, skip_tr_xml=False)

    def _runner_with_mapping(self, monkeypatch, variant):
        runner, recorded = self._runner(monkeypatch, variant)
        monkeypatch.setenv("TEST_PORTS_INFO", "ports.json")
        monkeypatch.delenv("TEST_SNAKE_PAIRS", raising=False)
        monkeypatch.setattr(runner, "_load_cabling", lambda path: ([], [], {}))
        monkeypatch.setattr(
            runner, "_full_platform_mapping", lambda config_name: {"eth1/1": make_cage(FULL)}
        )
        runner.tc["model"] = "NH-BW800-F"
        return runner, recorded

    def test_denylisted_variant_writes_skipped_junit(self, monkeypatch):
        runner, recorded = self._runner_with_mapping(monkeypatch, "8x100G")
        assert runner._run_test_impl({}, skip_tr_xml=False) is True
        assert recorded["passes"] == []
        [(name, reason)] = recorded["skipped"]
        assert name == "8x100G"
        assert reason.startswith("variant 8x100G is disabled on wedge800bact: ")
        assert "SAI create_port" in reason

    def test_denylist_leaves_other_variants_alone(self, monkeypatch):
        runner, recorded = self._runner_with_mapping(monkeypatch, "2x400G")
        assert runner._run_test_impl({}, skip_tr_xml=False) is True
        # Past the denylist gate, stopped only by the missing cabling data.
        assert recorded["skipped"] == [
            ("2x400G", "variant runs require TEST_SNAKE_PAIRS cabling data")
        ]

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


class TestPlainRunUsesBase:
    def test_no_cabling_data_and_max_falls_through_to_base(self, monkeypatch):
        runner = make_runner(QsfpTestRunner, {"filters": ["*Foo*"]})
        monkeypatch.delenv("TEST_PORTS_INFO", raising=False)
        with patch.object(BaseHwTestRunner, "_run_test_impl", return_value="base") as base:
            assert runner._run_test_impl({}, skip_tr_xml=True) == "base"
        base.assert_called_once()
