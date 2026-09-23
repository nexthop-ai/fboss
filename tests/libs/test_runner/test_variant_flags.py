"""Hardware-revision variant-flag injection (base.py)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from tests.libs.test_runner.runners.sai import SaiTestRunner

FLAGFILE = "--hwrev_state1_substate1_respin0=true\n"


def _make_runner(flagfile_content=None):
    """Runner with ssh/scp stubbed; flagfile_content None = no flagfile on DUT."""
    runner = SaiTestRunner()
    runner.ssh_client = MagicMock()
    if flagfile_content is None:
        runner.ssh_client.run_cmd.return_value = (1, "")
    else:
        runner.ssh_client.run_cmd.return_value = (0, flagfile_content)
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")
    return runner


class TestVariantFlags:
    def test_no_ssh_client_returns_empty(self):
        runner = SaiTestRunner()
        assert runner._variant_flags() == {}

    def test_missing_flagfile_returns_empty_and_caches(self):
        runner = _make_runner(None)
        assert runner._variant_flags() == {}
        assert runner._variant_flags() == {}
        assert runner.ssh_client.run_cmd.call_count == 1

    def test_parses_flag_lines(self):
        runner = _make_runner("--hwrev_state1_substate1_respin0=true\n--other=7\n--bare\ngarbage\n")
        assert runner._variant_flags() == {
            "hwrev_state1_substate1_respin0": "true",
            "other": "7",
            "bare": "true",
        }

    def test_stderr_lines_ignored(self):
        runner = _make_runner("stderr: noise\n--hwrev_state1_substate1_respin0=true\n")
        assert runner._variant_flags() == {"hwrev_state1_substate1_respin0": "true"}


class TestInjectVariantFlags:
    def test_noop_without_flags(self):
        runner = _make_runner(None)
        config = {"sw": {}}
        runner._inject_variant_flags(config)
        assert "defaultCommandLineArgs" not in config

    def test_updates_existing_args(self):
        runner = _make_runner(FLAGFILE)
        config = {"defaultCommandLineArgs": {"foo": "1"}, "sw": {}}
        runner._inject_variant_flags(config)
        assert config["defaultCommandLineArgs"] == {"foo": "1", "hwrev_state1_substate1_respin0": "true"}


class TestVariantizedConfigArg:
    def test_passthrough_without_flags(self):
        runner = _make_runner(None)
        path = "./share/hw_test_configs/x.agent.materialized_JSON"
        assert runner._variantized_config_arg(path, "/home/netops/up.json") == path
        runner.scp_client.get_file.assert_not_called()

    def test_fetch_inject_upload_and_cache(self):
        runner = _make_runner(FLAGFILE)
        uploaded = {}

        def fake_get(remote, local):
            with open(local, "w", encoding="utf-8") as f:
                json.dump({"defaultCommandLineArgs": {"a": "1"}}, f)
            return (0, "ok")

        def fake_put(local, remote):
            with open(local, encoding="utf-8") as f:
                uploaded[remote] = json.load(f)
            return (0, "ok")

        runner.scp_client.get_file.side_effect = fake_get
        runner.scp_client.put_file.side_effect = fake_put

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


class TestBootScriptMatchesDescriptor:
    """fboss_init.sh composes the variant flag name and the P1 descriptor
    declares it. A divergence fails silently on hardware, since the box just
    takes the default mapping, so pin the two together here."""

    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _INIT_SCRIPT = (
        _REPO_ROOT
        / "fboss-image/image_builder/templates/centos-09.0/root_files"
        / "usr/local/bin/fboss_init.sh"
    )
    _PLATFORM_CONFIGS = _REPO_ROOT / "fboss/configs/platforms"
    _P1_DESCRIPTOR = (
        _PLATFORM_CONFIGS
        / "nexthop/m4062nhp/variants/m4062nhp_p1/platform_mapping/generated"
        / "platform_descriptor.json"
    )

    def _composed_flag(self, tmp_path, state, substate, respin) -> str:
        script = self._INIT_SCRIPT.read_text()
        start = script.index("get_eeprom_field() {")
        end = script.index("enable_hw_agents() {")
        functions = script[start:end]
        assert "set_variant_flags" in functions

        parsed = tmp_path / "CHASSIS_EEPROM_PARSED"
        parsed.write_text(
            f"Production State: {state}\n"
            f"Production Sub-State: {substate}\n"
            f"Re-Spin/Variant Indicator: {respin}\n"
        )
        flagfile = tmp_path / "variant_flags"
        subprocess.run(
            [
                "bash",
                "-c",
                f"log(){{ :; }}; error(){{ :; }}\n"
                f"CHASSIS_EEPROM_PARSED={parsed}\nVARIANT_FLAGFILE={flagfile}\n"
                f"{functions}\nset -e\nset_variant_flags",
            ],
            check=True,
        )
        return flagfile.read_text().strip() if flagfile.exists() else ""

    def _declared_attributes(self) -> set[str]:
        declared = set()
        for path in self._PLATFORM_CONFIGS.rglob("platform_descriptor.json"):
            declared |= set(json.loads(path.read_text()).get("variantAttributes", {}))
        return declared

    def test_p1_flag_is_what_the_p1_descriptor_declares(self, tmp_path):
        declared = json.loads(self._P1_DESCRIPTOR.read_text())["variantAttributes"]
        assert len(declared) == 1
        assert self._composed_flag(tmp_path, 1, 1, 0) == f"--{next(iter(declared))}=true"

    def test_p2_flag_is_claimed_by_no_descriptor(self, tmp_path):
        flag = self._composed_flag(tmp_path, 2, 2, 0)
        assert flag == "--hwrev_state2_substate2_respin0=true"
        assert flag.removeprefix("--").removesuffix("=true") not in self._declared_attributes()
