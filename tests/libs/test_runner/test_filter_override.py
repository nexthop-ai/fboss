"""Unit tests for the TESTFILTER override on BaseHwTestRunner.

TESTFILTER (set by nhtests-run's --test-filter via TestInstanceFboss in the
nh monorepo) is loaded into tc["gtest_filter"] by getenvvars() -- the same
env-var-into-tc seam used for dut/username/password/model/filepath -- and
overrides what set_filters() writes into the filter file: the file's single
line becomes the override expression instead of the per-test-file default
"filters" list. build_test_cmd() is untouched -- it always references
--filter_file={self.filter_filepath}; run_test.py never has to choose between
--filter and --filter_file.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from tests.libs.test_runner.runner import (
    BenchmarkTestRunner,
    BspTestRunner,
    Fboss2IntegrationTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
    SmokeTestRunner,
)

_FILTER_FAMILY = (
    SaiTestRunner,
    SaiAgentTestRunner,
    QsfpTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    Fboss2IntegrationTestRunner,
)


def _make_runner(runner_cls, tc, extra_env=None):
    """Build a runner with tc populated the way setup() does, and scp mocked."""
    runner = runner_cls()
    runner.tc = dict(tc)
    with patch.dict(os.environ, extra_env or {}, clear=True):
        runner.getenvvars()
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")
    return runner


class TestSetFiltersOverride:
    @pytest.mark.parametrize("runner_cls", _FILTER_FAMILY)
    def test_default_writes_tc_filters_list(self, runner_cls, tmp_path):
        runner = _make_runner(runner_cls, {"filters": ["*AgentRoute*", "*PortAdminState*"]})
        src = tmp_path / "tests.conf"

        assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
        assert src.read_text().splitlines() == ["*AgentRoute*", "*PortAdminState*"]

    @pytest.mark.parametrize("runner_cls", _FILTER_FAMILY)
    def test_nh_gtest_filter_env_overrides_filters_list(self, runner_cls, tmp_path):
        runner = _make_runner(
            runner_cls,
            {"filters": ["*AgentRoute*", "*PortAdminState*"]},
            extra_env={"TESTFILTER": "*Vlan*:*Port*:-*Mac*"},
        )
        src = tmp_path / "tests.conf"

        assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
        assert src.read_text().splitlines() == ["*Vlan*:*Port*:-*Mac*"]


_PORTS_INFO = {
    "eth1/1/1": {"is_copper": True},
    "eth1/2/1": {"is_copper": False},
}


class TestSplitGtestFilter:
    """_split_gtest_filter() classifies a single --gtest_filter expression's
    colon-separated positive patterns the same way _split_filters() classifies
    tc["filters"], so a mixed TESTFILTER can still run as two cabling-aware
    passes (see TestCablingAwareGtestFilterSplit below) instead of collapsing
    into one pass with the wrong (or an empty) port set."""

    def test_pure_copper_safe_stays_one_expression(self):
        copper, optics = LinkTestRunner._split_gtest_filter("*PortStatus*:*Vlan*")
        assert copper == "*PortStatus*:*Vlan*"
        assert optics == ""

    def test_pure_optics_only(self):
        copper, optics = LinkTestRunner._split_gtest_filter("*verifyTxRxLatches*")
        assert copper == ""
        assert optics == "*verifyTxRxLatches*"

    def test_mixed_splits_and_shares_negative_suffix(self):
        copper, optics = LinkTestRunner._split_gtest_filter(
            "*PortStatus*:*verifyTxRxLatches*-*Foo*:*Bar*"
        )
        assert copper == "*PortStatus*-*Foo*:*Bar*"
        assert optics == "*verifyTxRxLatches*-*Foo*:*Bar*"

    def test_negative_only_implies_wildcard_positive(self):
        # gtest treats a bare "-pattern" as "everything except pattern"; an
        # empty positive side here must not be read as "no tests selected".
        copper, optics = LinkTestRunner._split_gtest_filter("-*verifyTxRxLatches*")
        assert copper == "*-*verifyTxRxLatches*"
        assert optics == ""

    def test_qsfp_runner_uses_its_own_optics_only_substrings(self):
        copper, optics = QsfpTestRunner._split_gtest_filter("*PortStatus*:*i2cStressWrite*")
        assert copper == "*PortStatus*"
        assert optics == "*i2cStressWrite*"


def _make_cabling_runner(runner_cls, tmp_path, gtest_filter, ports_info=None):
    runner = runner_cls()
    runner.tc = {"model": "m4062nhp", "gtest_filter": gtest_filter, "filters": []}
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")
    runner.ssh_client = MagicMock()
    cabling_path = tmp_path / "ports_info.json"
    cabling_path.write_text(json.dumps(ports_info if ports_info is not None else _PORTS_INFO))
    return runner, str(cabling_path)


_MIXED_FILTER_CASES = (
    (QsfpTestRunner, "*PortStatus*:*i2cStressWrite*-*Foo*",
     "*PortStatus*-*Foo*", "*i2cStressWrite*-*Foo*"),
    (LinkTestRunner, "*PortStatus*:*verifyTxRxLatches*-*Foo*",
     "*PortStatus*-*Foo*", "*verifyTxRxLatches*-*Foo*"),
)


class TestCablingAwareGtestFilterSplit:
    """_run_cabling_aware() with a TESTFILTER override set: verifies the fix
    for the bug where a gtest_filter override used to skip cabling entirely
    (QsfpTestRunner got zero cabled ports; LinkTestRunner got every port
    unfiltered) instead of running the matching split against real ports."""

    @pytest.mark.parametrize(
        "runner_cls, gtest_filter, expected_copper, expected_optics", _MIXED_FILTER_CASES
    )
    def test_mixed_filter_runs_two_passes_against_matching_ports(
        self, runner_cls, gtest_filter, expected_copper, expected_optics, tmp_path
    ):
        runner, cabling_path = _make_cabling_runner(runner_cls, tmp_path, gtest_filter)
        prepare_calls = []
        execute_calls = []

        def fake_prepare_pass(model, ports):
            prepare_calls.append((model, list(ports)))

        def fake_execute(model, log_local, xml_local, skip_tr_xml):  # noqa: ARG001
            execute_calls.append(runner.tc["gtest_filter"])
            return True

        with patch.object(runner, "_prepare_pass", side_effect=fake_prepare_pass), \
             patch.object(runner, "pre_test"), \
             patch.object(runner, "post_test"), \
             patch.object(runner, "_execute_test_binary", side_effect=fake_execute):
            result = runner._run_cabling_aware(cabling_path, {}, skip_tr_xml=True)

        assert result is True
        assert prepare_calls == [
            ("m4062nhp", ["eth1/1/1", "eth1/2/1"]),
            ("m4062nhp", ["eth1/2/1"]),
        ]
        assert execute_calls == [expected_copper, expected_optics]
        # The override key is restored to the original mixed expression afterwards.
        assert runner.tc["gtest_filter"] == gtest_filter

    @pytest.mark.parametrize(
        "runner_cls, optics_only_filter",
        [(QsfpTestRunner, "*i2cStressWrite*"), (LinkTestRunner, "*verifyTxRxLatches*")],
    )
    def test_optics_only_filter_skips_cleanly_when_dut_has_no_optics(
        self, runner_cls, optics_only_filter, tmp_path
    ):
        runner, cabling_path = _make_cabling_runner(
            runner_cls, tmp_path, optics_only_filter,
            ports_info={"eth1/1/1": {"is_copper": True}},
        )

        with patch.object(runner, "_prepare_pass") as prepare, \
             patch.object(runner, "pre_test"), \
             patch.object(runner, "post_test"), \
             patch.object(runner, "_execute_test_binary") as execute, \
             patch.object(runner, "_merge_junit_results") as merge, \
             patch.object(runner, "normalize_test_results_file"):
            result = runner._run_cabling_aware(cabling_path, {}, skip_tr_xml=False)

        assert result is True
        prepare.assert_not_called()
        execute.assert_not_called()
        _, kwargs = merge.call_args
        assert kwargs["skipped"] == [
            (optics_only_filter, "no optical/active transceivers cabled on this DUT")
        ]

    def test_earlier_pass_failure_records_whole_expression_as_skipped(self, tmp_path):
        runner, cabling_path = _make_cabling_runner(
            LinkTestRunner, tmp_path, "*PortStatus*:*verifyTxRxLatches*"
        )

        with patch.object(runner, "_prepare_pass"), \
             patch.object(runner, "pre_test"), \
             patch.object(runner, "post_test"), \
             patch.object(runner, "_execute_test_binary", return_value=False) as execute, \
             patch.object(runner, "_merge_junit_results") as merge, \
             patch.object(runner, "normalize_test_results_file"):
            result = runner._run_cabling_aware(cabling_path, {}, skip_tr_xml=False)

        assert result is False
        execute.assert_called_once()  # aborted before the optics pass ran
        _, kwargs = merge.call_args
        # Bug this guards against: iterating a bare gtest_filter *string*
        # (instead of wrapping it in a list first) would spell it out char by char.
        assert kwargs["skipped"] == [
            ("*verifyTxRxLatches*", "earlier pass failed; run aborted")
        ]
