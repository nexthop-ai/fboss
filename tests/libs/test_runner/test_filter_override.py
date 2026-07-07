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
