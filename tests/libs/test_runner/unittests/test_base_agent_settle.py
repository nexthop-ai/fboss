"""BaseHwTestRunner._wait_for_agent_settled: the fboss_sw_agent readiness poll.

systemd reports the unit active as soon as it execs, so the loop treats
`fboss2 show product` as the readiness check and only returns early when the
unit is stopped outright.
"""

import itertools
from unittest.mock import patch

import pytest

from tests.libs.test_runner import QsfpTestRunner

from .helpers import make_runner


def _runner(replies):
    runner = make_runner(QsfpTestRunner, {"filters": ["*Foo*"]})
    runner.ssh_client.run_cmd.side_effect = replies
    return runner


class TestAgentSettleWait:
    @pytest.mark.parametrize("output", ["inactive\n", "failed\n", "deactivating\n"])
    def test_returns_on_first_poll_when_unit_not_active(self, output):
        runner = _runner([(3, output)])
        with patch("tests.libs.test_runner.base.time.sleep") as sleep:
            runner._wait_for_agent_settled()
        assert runner.ssh_client.run_cmd.call_count == 1
        assert "systemctl is-active fboss_sw_agent" in runner.ssh_client.run_cmd.call_args[0][0]
        sleep.assert_not_called()

    @pytest.mark.parametrize("reply", [
        (1, "Timed out waiting for SSH connection"),
        (-1, ""),
        (3, "activating\n"),
        (0, "stderr: sudo: unable to resolve host x\n"),
    ])
    def test_unknown_or_starting_state_keeps_polling(self, reply):
        runner = _runner([reply, (3, "inactive\n")])
        with patch("tests.libs.test_runner.base.time.sleep") as sleep:
            runner._wait_for_agent_settled()
        assert runner.ssh_client.run_cmd.call_count == 2
        assert all(
            "systemctl is-active" in c[0][0] for c in runner.ssh_client.run_cmd.call_args_list
        )
        assert sleep.call_count == 1

    @pytest.mark.parametrize("reply, polls", [
        ((0, "active\n"), 6),
        ((1, "Timed out waiting for SSH connection"), 3),
    ])
    def test_gives_up_after_timeout_without_raising(self, reply, polls):
        runner = _runner([reply, (1, "initializing")] * 50)
        clock = itertools.count(0, 100)
        with patch("tests.libs.test_runner.base.time.sleep") as sleep, \
             patch("tests.libs.test_runner.base.time.monotonic", side_effect=clock):
            runner._wait_for_agent_settled(timeout_s=240)
        # Polls at t=100 and t=200 sleep; the t=300 poll is past the deadline.
        assert sleep.call_count == 2
        assert runner.ssh_client.run_cmd.call_count == polls

    def test_returns_when_active_and_cli_answers(self):
        runner = _runner([(0, "active\n"), (0, "Product: NH-4215-F")])
        with patch("tests.libs.test_runner.base.time.sleep") as sleep:
            runner._wait_for_agent_settled()
        assert runner.ssh_client.run_cmd.call_count == 2
        assert "fboss2 show product" in runner.ssh_client.run_cmd.call_args[0][0]
        sleep.assert_not_called()

    def test_stderr_noise_on_active_does_not_end_the_wait(self):
        # run_cmd interleaves stderr into the output; the first stdout line decides.
        runner = _runner([
            (0, "active\nstderr: sudo: unable to resolve host x\n"),
            (1, "switch is still initializing"),
            (0, "active\n"), (0, "Product: NH-4215-F"),
        ])
        with patch("tests.libs.test_runner.base.time.sleep") as sleep:
            runner._wait_for_agent_settled()
        assert runner.ssh_client.run_cmd.call_count == 4
        assert sleep.call_count == 1

    def test_polls_while_initializing_then_returns(self):
        runner = _runner([
            (0, "active\n"), (1, "switch is still initializing"),
            (0, "active\n"), (1, "switch is still initializing"),
            (0, "active\n"), (0, "Product: NH-4215-F"),
        ])
        with patch("tests.libs.test_runner.base.time.sleep") as sleep:
            runner._wait_for_agent_settled(poll_s=7)
        assert runner.ssh_client.run_cmd.call_count == 6
        assert sleep.call_count == 2
        sleep.assert_called_with(7)

    def test_plain_run_waits_before_the_test_binary(self):
        runner = make_runner(QsfpTestRunner, {"filters": ["*Foo*"]})
        runner.tc["model"] = "m4062nhp"
        with patch.object(runner, "set_filters", return_value=True), \
             patch.object(runner, "pre_test"), \
             patch.object(runner, "post_test"), \
             patch.object(runner, "_wait_for_agent_settled") as wait, \
             patch.object(runner, "_execute_test_binary", return_value=True):
            assert runner._run_test_impl({}, skip_tr_xml=True) is True
        wait.assert_called_once()
