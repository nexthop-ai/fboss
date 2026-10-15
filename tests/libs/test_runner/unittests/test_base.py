"""BaseHwTestRunner: filter upload, command assembly, the run_test template
and its deploy-only gate, the failure-duration floor, and variant-flag
injection. The agent-settle poll has its own module."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from tests.libs.test_runner import (
    BenchmarkTestRunner,
    Fboss2IntegrationTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    QsfpBenchmarkTestRunner,
    QsfpTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
    SmokeTestRunner,
)
from tests.libs.test_runner import base as base_module
from tests.libs.test_runner.base import (
    MIN_FAILURE_DURATION_SECS,
    _enforce_min_failure_duration,
    _first_stdout_line,
    normalize_model,
    remote_fboss_cmd,
)

from .helpers import NEXIS_ENV, VARIANT_FLAGFILE, fake_run_factory, fake_ssh_handler, json_scp, make_runner

# Every runner that writes a filter file. BspTestRunner is the one exception
# (see test_runner_small.py); SmokeTestRunner drives agent_smoke.py directly.
_FILTER_FAMILY = (
    SaiTestRunner,
    SaiAgentTestRunner,
    QsfpTestRunner,
    LinkTestRunner,
    PlatformTestRunner,
    Fboss2IntegrationTestRunner,
    BenchmarkTestRunner,
    QsfpBenchmarkTestRunner,
)


class TestPureHelpers:
    def test_normalize_model(self):
        assert normalize_model("NH-4010-F") == "nh4010f"
        assert normalize_model("nhbw800f") == "nhbw800f"

    def test_remote_fboss_cmd_wraps_as_root_with_env(self):
        assert remote_fboss_cmd("fboss2 show product") == (
            "sudo su -c 'cd /opt/fboss && source ./bin/setup_fboss_env && fboss2 show product'"
        )

    @pytest.mark.parametrize("output, expected", [
        ("active\n", "active"),
        ("stderr: sudo: unable to resolve host x\nactive\n", "active"),
        ("\n  \nfailed\n", "failed"),
        ("stderr: only noise\n", ""),
        ("", ""),
        (None, ""),
    ])
    def test_first_stdout_line_skips_stderr_and_blanks(self, output, expected):
        assert _first_stdout_line(output) == expected

    def test_binary_exit_is_fatal_on_nonzero(self):
        runner = SaiTestRunner()
        assert runner.binary_exit_is_fatal(0) is False
        assert runner.binary_exit_is_fatal(1) is True
        assert runner.binary_exit_is_fatal(-9) is True


class TestMinFailureDuration:
    """A failing run is padded to the floor so TE's back-to-back retries of
    an early-aborting binary do not hammer the DUT."""

    class _Runner:
        @_enforce_min_failure_duration
        def run_test(self, result):
            return result

    def _run(self, result, elapsed, env=None):
        with patch.dict(os.environ, env or {}, clear=True), \
             patch("tests.libs.test_runner.base.time.sleep") as sleep, \
             patch("tests.libs.test_runner.base.time.monotonic", side_effect=[0, elapsed]):
            assert self._Runner().run_test(result) is result
        return sleep

    def test_failure_is_padded_to_the_floor(self):
        sleep = self._run(False, elapsed=5)
        sleep.assert_called_once_with(MIN_FAILURE_DURATION_SECS - 5)

    def test_success_is_never_delayed(self):
        self._run(True, elapsed=5).assert_not_called()

    def test_slow_failure_is_not_padded_further(self):
        self._run(False, elapsed=MIN_FAILURE_DURATION_SECS + 1).assert_not_called()

    def test_deploy_only_is_exempt(self):
        self._run(False, elapsed=5, env={"FBOSS_DEPLOY_ONLY": "1"}).assert_not_called()


class TestSetFiltersOverride:
    """TESTFILTER (nhtests-run --test-filter) lands in tc["gtest_filter"] via
    getenvvars() and replaces the per-file "filters" list in the uploaded
    filter file; build_test_cmd always points at --filter_file."""

    @pytest.mark.parametrize("runner_cls", _FILTER_FAMILY)
    def test_default_writes_tc_filters_list(self, runner_cls, tmp_path):
        runner = make_runner(runner_cls, {"filters": ["*AgentRoute*", "*PortAdminState*"]})
        src = tmp_path / "tests.conf"

        assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
        assert src.read_text().splitlines() == ["*AgentRoute*", "*PortAdminState*"]

    @pytest.mark.parametrize("runner_cls", _FILTER_FAMILY)
    def test_nh_gtest_filter_env_overrides_filters_list(self, runner_cls, tmp_path):
        runner = make_runner(
            runner_cls,
            {"filters": ["*AgentRoute*", "*PortAdminState*"]},
            env={"TESTFILTER": "*Vlan*:*Port*:-*Mac*"},
        )
        src = tmp_path / "tests.conf"

        assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
        assert src.read_text().splitlines() == ["*Vlan*:*Port*:-*Mac*"]

    def test_failed_upload_returns_false(self, tmp_path):
        runner = make_runner(SaiTestRunner, {"filters": ["*Foo*"]})
        runner.scp_client.put_file.return_value = (1, "scp: permission denied")
        assert runner.set_filters(str(tmp_path / "tests.conf"), "/home/netops/tests.conf") is False


class TestBuildTestCmd:
    @pytest.mark.parametrize("runner_cls", _FILTER_FAMILY)
    def test_passes_filter_file(self, runner_cls):
        runner = make_runner(runner_cls, {"filters": ["*Stats*"]})
        runner.tc["model"] = "nhbw800f"
        cmd = runner.build_test_cmd("nhbw800f")
        assert f"--filter_file={runner.filter_filepath}" in cmd
        assert cmd.endswith(f"> {runner.testlog_filepath} 2>&1")

    def test_omits_timeout_flag_when_unset(self):
        runner = make_runner(QsfpTestRunner, {"filters": ["*Foo*"]})
        assert "--test-run-timeout" not in runner.build_test_cmd("m4062nhp")

    def test_test_context_timeout_is_honored_and_runner_budget_wins(self):
        runner = make_runner(BenchmarkTestRunner, {"filters": ["*SystemScale*"]})
        runner.tc["model"] = "nhbw800f"
        runner.tc["test_run_timeout"] = 2400
        assert "--test-run-timeout 2400" in runner.build_test_cmd("nhbw800f")
        # A runner-computed budget (cabling) still wins over the file's value.
        runner._test_run_timeout_secs = 1920
        assert "--test-run-timeout 1920" in runner.build_test_cmd("nhbw800f")

    def test_fboss_logging_flag(self):
        runner = make_runner(QsfpTestRunner, {"filters": ["*Foo*"]})
        assert "--fboss_logging" not in runner.build_test_cmd("m4062nhp")
        runner._fboss_logging = "DBG2"
        assert "--fboss_logging DBG2" in runner.build_test_cmd("m4062nhp")


class TestDeployOnly:
    """FBOSS_DEPLOY_ONLY (set by nhtests-run --mode deploy): run_test() deploys
    this runner's slice via setup() then returns without executing the test."""

    @staticmethod
    def _patch_clients(monkeypatch):
        """Make setup() build mock SSH/SCP clients instead of real ones.

        setup() reassigns self.ssh_client/scp_client to fresh Device*Clients,
        so the classes the runner module imported are patched, not the
        instance attributes. Any sleep in the run_test path fails the test
        outright: the agent-settle poll would otherwise spend its full
        deadline in real time if the systemctl reply ever stopped matching.
        """
        ssh = MagicMock()
        scp = MagicMock()
        scp.put_file.return_value = (0, "ok")
        ssh.run_cmd.side_effect = fake_ssh_handler()
        monkeypatch.setattr(base_module, "DeviceSSHClient", lambda *a, **k: ssh)
        monkeypatch.setattr(base_module, "DeviceSCPClient", lambda *a, **k: scp)
        monkeypatch.setattr(
            base_module.time, "sleep", lambda s: pytest.fail(f"run_test slept {s}s")
        )
        return ssh, scp

    @staticmethod
    def _deploy_only_env(**extra):
        return {**NEXIS_ENV, "FBOSS_DEPLOY_ONLY": "1", **extra}

    @pytest.mark.parametrize("runner_cls, script, extra_env", [
        (SaiTestRunner, "run_test.py", {}),
        # Customizes execution via _run_test_impl; the base gate must still apply.
        (SmokeTestRunner, "agent_smoke.py", {}),
        # Must not reach the CSV/tr.xml post-processing with nothing run.
        (BenchmarkTestRunner, "run_test.py", {}),
        # The gate must fire before the cabling-aware path reads this.
        (QsfpTestRunner, "run_test.py", {"TEST_PORTS_INFO": "/does/not/matter"}),
    ])
    def test_run_test_deploys_then_skips_execution(
        self, runner_cls, script, extra_env, monkeypatch, isolated_cache
    ):
        ssh, scp = self._patch_clients(monkeypatch)
        fake_run, _ = fake_run_factory(runner_cls.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, self._deploy_only_env(**extra_env), clear=True):
            result = runner_cls().run_test({})

        assert result is True
        scp.put_file.assert_called_once()
        assert scp.put_file.call_args.args[1] == f"/tmp/fboss-{runner_cls.__name__}-slice.tar"
        assert all(script not in c.args[0] for c in ssh.run_cmd.call_args_list)
        scp.get_file.assert_not_called()

    def test_run_test_deploy_failure_propagates(self, monkeypatch, isolated_cache):
        """A failed upload raises out of setup(), ahead of the deploy-only
        early return, so nhtests-run sees FAIL_ENV rather than a false PASS."""
        ssh, scp = self._patch_clients(monkeypatch)
        scp.put_file.return_value = (1, "scp: permission denied")
        fake_run, _ = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        with patch.dict(os.environ, self._deploy_only_env(), clear=True):
            with pytest.raises(RuntimeError, match="Failed to copy slice tar"):
                SaiTestRunner().run_test({})

        assert all("run_test.py" not in c.args[0] for c in ssh.run_cmd.call_args_list)

    def test_run_test_without_deploy_only_executes(self, monkeypatch, isolated_cache):
        ssh, scp = self._patch_clients(monkeypatch)
        scp.get_file.return_value = (0, "ok")
        fake_run, _ = fake_run_factory(SaiTestRunner.REQUIRED_PATHS)
        monkeypatch.setattr(subprocess, "run", fake_run)

        env = {**NEXIS_ENV, "DUT": "dut-1", "HWSKU": "minipack3"}
        with patch.dict(os.environ, env, clear=True):
            SaiTestRunner().run_test({"filters": []})

        assert any("run_test.py" in c.args[0] for c in ssh.run_cmd.call_args_list)


class TestVariantFlags:
    def test_no_ssh_client_returns_empty(self):
        runner = SaiTestRunner()
        assert runner._variant_flags() == {}

    def test_missing_flagfile_returns_empty_and_caches(self):
        runner = make_runner(SaiTestRunner, flagfile=None)
        assert runner._variant_flags() == {}
        assert runner._variant_flags() == {}
        assert runner.ssh_client.run_cmd.call_count == 1

    def test_parses_flag_lines(self):
        runner = make_runner(
            SaiTestRunner, flagfile="--hwrev_state1_substate1_respin0=true\n--other=7\n--bare\ngarbage\n"
        )
        assert runner._variant_flags() == {
            "hwrev_state1_substate1_respin0": "true",
            "other": "7",
            "bare": "true",
        }

    def test_stderr_lines_ignored(self):
        runner = make_runner(SaiTestRunner, flagfile="stderr: noise\n--hwrev_state1_substate1_respin0=true\n")
        assert runner._variant_flags() == {"hwrev_state1_substate1_respin0": "true"}


class TestInjectVariantFlags:
    def test_noop_without_flags(self):
        runner = make_runner(SaiTestRunner, flagfile=None)
        config = {"sw": {}}
        runner._inject_variant_flags(config)
        assert "defaultCommandLineArgs" not in config

    def test_updates_existing_args(self):
        runner = make_runner(SaiTestRunner, flagfile=VARIANT_FLAGFILE)
        config = {"defaultCommandLineArgs": {"foo": "1"}, "sw": {}}
        runner._inject_variant_flags(config)
        assert config["defaultCommandLineArgs"] == {"foo": "1", "hwrev_state1_substate1_respin0": "true"}


class TestVariantizedConfigArg:
    def test_passthrough_without_flags(self):
        runner = make_runner(SaiTestRunner, flagfile=None)
        path = "./share/hw_test_configs/x.agent.materialized_JSON"
        assert runner._variantized_config_arg(path, "/home/netops/up.json") == path
        runner.scp_client.get_file.assert_not_called()

    def test_fetch_inject_upload_and_cache(self):
        runner = make_runner(SaiTestRunner, flagfile=VARIANT_FLAGFILE)
        uploaded = json_scp(runner, {"defaultCommandLineArgs": {"a": "1"}})

        arg = runner._variantized_config_arg("./share/x.json", "/home/netops/up.json")
        assert arg == "/home/netops/up.json"
        # ./relative resolves under /opt/fboss on the DUT.
        assert runner.scp_client.get_file.call_args[0][0] == "/opt/fboss/share/x.json"
        assert uploaded["/home/netops/up.json"]["defaultCommandLineArgs"] == {
            "a": "1",
            "hwrev_state1_substate1_respin0": "true",
        }
        # Second call is served from the cache: no new fetch or upload.
        assert runner._variantized_config_arg("./share/x.json", "/home/netops/up.json") == arg
        assert runner.scp_client.get_file.call_count == 1
        assert runner.scp_client.put_file.call_count == 1

    def test_fetch_failure_raises(self):
        runner = make_runner(SaiTestRunner, flagfile=VARIANT_FLAGFILE)
        runner.scp_client.get_file.return_value = (1, "no such file")
        with pytest.raises(RuntimeError, match="for variant flags"):
            runner._variantized_config_arg("./share/x.json", "/home/netops/up.json")

    def test_unparseable_config_raises(self):
        runner = make_runner(SaiTestRunner, flagfile=VARIANT_FLAGFILE)

        def fake_get(remote, local):
            with open(local, "w", encoding="utf-8") as f:
                f.write("{not json")
            return (0, "ok")

        runner.scp_client.get_file.side_effect = fake_get
        with pytest.raises(RuntimeError, match="Unparseable JSON"):
            runner._variantized_config_arg("./share/x.json", "/home/netops/up.json")
