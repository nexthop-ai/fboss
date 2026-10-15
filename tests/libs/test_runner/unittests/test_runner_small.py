"""The runners with little logic of their own: smoke (drives agent_smoke.py
directly), platform and BSP (platform stack, BSP runs with no filter file),
and fboss2 integration."""

from unittest.mock import MagicMock

from tests.libs.test_runner import (
    BspTestRunner,
    Fboss2IntegrationTestRunner,
    PlatformTestRunner,
    SmokeTestRunner,
)
from tests.libs.test_runner.base import remote_fboss_cmd
from tests.libs.test_runner.deploy import STACK_FORWARDING, STACK_PLATFORM

from .helpers import make_runner


class TestSmokeTestRunner:
    def test_remote_cmd_minimal(self):
        runner = SmokeTestRunner()
        runner.tc = {}
        assert runner._build_remote_cmd() == (
            f"python3 {SmokeTestRunner.AGENT_SMOKE_PATH} --results-xml {runner.testresult_filepath}"
        )

    def test_remote_cmd_forwards_test_context_knobs_and_quotes(self):
        runner = SmokeTestRunner()
        runner.tc = {
            "stability_window": 30,
            "startup_timeout": 600,
            "expected_hw_agents": 2,
            "services": "fboss_sw_agent fboss_hw_agent",
            "unrelated": "x",
        }
        cmd = runner._build_remote_cmd()
        assert cmd.endswith(
            "--stability-window 30 --startup-timeout 600 --expected-hw-agents 2 "
            "--services 'fboss_sw_agent fboss_hw_agent'"
        )

    def test_remote_cmd_skips_empty_values(self):
        runner = SmokeTestRunner()
        runner.tc = {"stability_window": "", "startup_timeout": None, "expected_hw_agents": 0}
        assert runner._build_remote_cmd().endswith("--expected-hw-agents 0")

    def test_run_executes_script_and_fetches_results(self):
        runner = make_runner(SmokeTestRunner)
        runner.tc = {}
        runner.scp_client.get_file.return_value = (0, "ok")

        assert runner._run_test_impl({}) is True

        cmds = [c.args[0] for c in runner.ssh_client.run_cmd.call_args_list]
        assert cmds[0] == f"sudo rm -f {runner.testlog_filepath} {runner.testresult_filepath}"
        assert cmds[1].startswith(f"sudo python3 {SmokeTestRunner.AGENT_SMOKE_PATH}")
        assert cmds[1].endswith(f"> {runner.testlog_filepath} 2>&1")
        fetched = [c.args for c in runner.scp_client.get_file.call_args_list]
        assert fetched == [
            (runner.testlog_filepath, "/tmp/test.log"),
            (runner.testresult_filepath, "/tmp/tr.xml"),
        ]

    def test_script_failure_is_reported_after_fetching(self):
        runner = make_runner(SmokeTestRunner)
        runner.tc = {}
        runner.scp_client.get_file.return_value = (0, "ok")

        def ssh(cmd, *args, **kwargs):
            return (2, "smoke failed") if "agent_smoke.py" in cmd else (0, "ok")

        runner.ssh_client.run_cmd.side_effect = ssh
        assert runner._run_test_impl({}) is False
        assert runner.scp_client.get_file.call_count == 2

    def test_fetch_failure_is_fatal(self):
        runner = make_runner(SmokeTestRunner)
        runner.tc = {}
        runner.scp_client.get_file.return_value = (1, "no such file")
        assert runner._run_test_impl({}) is False

    def test_manifest(self):
        assert SmokeTestRunner.STACK == STACK_FORWARDING
        assert SmokeTestRunner.REQUIRED_PATHS == (
            "bin/python_tests/agent_smoke.py",
            "bin/python_tests/junit.py",
        )
        assert SmokeTestRunner().test_args("nhbw800f") == ""


class TestPlatformTestRunner:
    def test_test_type_selects_the_binary(self):
        assert PlatformTestRunner().test_args("nhbw800f") == "platform --type platform_hw_test"
        assert PlatformTestRunner("fan_service_hw_test").test_args("nhbw800f") == "platform --type fan_service_hw_test"

    def test_ships_platform_binaries_only(self):
        assert PlatformTestRunner.STACK == STACK_PLATFORM
        assert "bin/platform_hw_test" in PlatformTestRunner.REQUIRED_PATHS
        assert not any(p.startswith("share/") for p in PlatformTestRunner.REQUIRED_PATHS)


class TestBspTestRunner:
    def test_set_filters_is_a_noop(self, tmp_path):
        runner = BspTestRunner()
        runner.tc = {"filters": ["*Foo*"]}
        runner.scp_client = MagicMock()
        src = tmp_path / "tests.conf"
        assert runner.set_filters(str(src), "/home/netops/tests.conf") is True
        assert not src.exists()
        runner.scp_client.put_file.assert_not_called()

    def test_build_test_cmd_runs_everything_with_the_fboss_env(self):
        runner = BspTestRunner()
        cmd = runner.build_test_cmd("nhbw800f")
        assert "--filter_file" not in cmd
        # The same wrapper the other runners get from remote_fboss_cmd.
        assert cmd == f"{remote_fboss_cmd(' ./bin/run_test.py bsp ')} > {runner.testlog_filepath} 2>&1"

    def test_manifest(self):
        assert BspTestRunner.STACK == STACK_PLATFORM
        assert BspTestRunner.REQUIRED_PATHS == ("bin/bsp_tests",)
        assert BspTestRunner().test_args("nhbw800f") == "bsp"


class TestFboss2IntegrationTestRunner:
    def test_test_args_carry_known_bad_for_mapped_models(self):
        assert Fboss2IntegrationTestRunner().test_args("nh4215f") == (
            "fboss2_integration --skip-known-bad-tests m4062nhp/brcm-14.2.0.0_odp"
        )
        assert Fboss2IntegrationTestRunner().test_args("no-such-model") == "fboss2_integration"

    def test_pre_test_leaves_the_dut_alone(self):
        # run_test.py fboss2_integration owns the agent lifecycle; the base
        # class warm-boot wipe would race its prod-agent detection.
        runner = make_runner(Fboss2IntegrationTestRunner)
        runner.pre_test()
        runner.ssh_client.run_cmd.assert_not_called()
