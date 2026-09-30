"""Unit tests for the qsfp_service config LinkTestRunner stages on the DUT."""

import json
from unittest.mock import MagicMock

from tests.libs.test_runner import LinkTestRunner


def _stage(system_config, flagfile=None):
    """Run _stage_qsfp_config against a fake DUT; return the uploaded config."""
    runner = LinkTestRunner()
    runner.ssh_client = MagicMock()
    runner.ssh_client.run_cmd.return_value = (1, "") if flagfile is None else (0, flagfile)
    runner.scp_client = MagicMock()
    uploaded = {}

    def fake_get(remote, local):
        with open(local, "w", encoding="utf-8") as f:
            json.dump(system_config, f)
        return (0, "ok")

    def fake_put(local, remote):
        with open(local, encoding="utf-8") as f:
            uploaded[remote] = json.load(f)
        return (0, "ok")

    runner.scp_client.get_file.side_effect = fake_get
    runner.scp_client.put_file.side_effect = fake_put
    runner._stage_qsfp_config()
    assert runner.scp_client.get_file.call_args[0][0] == LinkTestRunner._SYSTEM_QSFP_CONFIG_PATH
    return uploaded[LinkTestRunner._REMOTE_QSFP_CONFIG_PATH]


class TestStageQsfpConfig:
    def test_disables_fsdb_subscription_and_remediation(self):
        staged = _stage({"defaultCommandLineArgs": {"mode": "wedge800cact"}})
        assert staged["defaultCommandLineArgs"] == {
            "mode": "wedge800cact",
            "subscribe_to_state_from_fsdb": "false",
            "remediation_enabled": "false",
        }

    def test_overrides_system_values(self):
        staged = _stage(
            {
                "defaultCommandLineArgs": {
                    "subscribe_to_state_from_fsdb": "true",
                    "remediation_enabled": "true",
                }
            }
        )
        assert staged["defaultCommandLineArgs"]["subscribe_to_state_from_fsdb"] == "false"
        assert staged["defaultCommandLineArgs"]["remediation_enabled"] == "false"

    def test_creates_args_when_system_config_has_none(self):
        staged = _stage({"transceiverConfigOverrides": []})
        assert staged["transceiverConfigOverrides"] == []
        assert staged["defaultCommandLineArgs"] == {
            "subscribe_to_state_from_fsdb": "false",
            "remediation_enabled": "false",
        }

    def test_keeps_variant_flags(self):
        staged = _stage({}, flagfile="--hwrev_state1_substate1_respin0=true\n")
        assert staged["defaultCommandLineArgs"]["hwrev_state1_substate1_respin0"] == "true"
        assert staged["defaultCommandLineArgs"]["remediation_enabled"] == "false"
