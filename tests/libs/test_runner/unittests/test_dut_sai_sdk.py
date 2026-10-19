"""Tests for skip-list keys that follow the SAI version on the DUT.

The runner reads the DUT's sai-runtime RPM version and puts it into the
model's SAI_KNOWN_BAD_KEY entry, so a TH6 image on SAI 14.2 or 15.4 gets
the matching skip lists. This applies only to Broadcom XGS GA models.
Leaba, EA and DNX models, and any DUT whose version can't be read, keep
the fixed key.
"""

from unittest.mock import MagicMock

import pytest

from tests.libs.test_runner import (
    BenchmarkTestRunner,
    Fboss2IntegrationTestRunner,
    SaiAgentTestRunner,
    SaiTestRunner,
)
from tests.libs.test_runner.platform_configs import (
    benchmark_skip_known_bad,
    fboss2_skip_known_bad,
    SAI_KNOWN_BAD_KEY,
    sai_known_bad_key,
    sai_skip_known_bad,
    sdk_version_for_model,
)

_KEY_HELPERS = (
    sai_known_bad_key,
    sai_skip_known_bad,
    benchmark_skip_known_bad,
    fboss2_skip_known_bad,
    sdk_version_for_model,
)


# ---------------------------------------------------------------------------
# platform_configs helpers
# ---------------------------------------------------------------------------

_TH6_MODELS = ("nh4215f", "nh4220f", "nhf424064r")


def _static_sai_runtime(model: str) -> str:
    """The model's static SDK in sai-runtime form, e.g. "14.2.0" for 14.2.0.0_odp.

    Keys that aren't Broadcom GA (Leaba, EA, DNX) come back as their SDK
    segment unchanged.
    """
    return SAI_KNOWN_BAD_KEY[model].split("/")[1].removesuffix(".0_odp")


@pytest.mark.parametrize("model", sorted(SAI_KNOWN_BAD_KEY))
@pytest.mark.parametrize("helper", _KEY_HELPERS)
def test_dut_on_static_sdk_changes_nothing(model, helper):
    # Given any model, on a DUT that reports the SDK already in the table
    version = _static_sai_runtime(model)
    # When a key helper runs with that version
    result = helper(model, version)
    # Then it returns exactly what it returns with no version
    assert result == helper(model)


@pytest.mark.parametrize("model", _TH6_MODELS)
def test_static_th6_sdk_is_14_2(model):
    # Given a TH6 model
    # When its static SDK is turned back into an RPM version
    version = _static_sai_runtime(model)
    # Then it is 14.2.0
    assert version == "14.2.0"


@pytest.mark.parametrize(
    ("model", "sai", "bench", "fboss2"),
    [
        (
            "nh4220f",
            "brcm/15.4.0.0_odp/15.4.0.0_odp/tomahawk6",
            "brcm/15.4.0.0_odp/tomahawk6/nh4220f",
            "nh4220f/brcm-15.4.0.0_odp",
        ),
        (
            "nh4215f",
            "brcm/15.4.0.0_odp/15.4.0.0_odp/tomahawk6",
            "brcm/15.4.0.0_odp/tomahawk6/m4062nhp",
            "m4062nhp/brcm-15.4.0.0_odp",
        ),
        (
            "nhf424064r",
            "brcm/15.4.0.0_odp/15.4.0.0_odp/tomahawk6",
            "brcm/15.4.0.0_odp/tomahawk6/m4061nhp",
            "m4061nhp/brcm-15.4.0.0_odp",
        ),
    ],
)
def test_th6_on_15_4_image(model, sai, bench, fboss2):
    # Given a TH6 model on a DUT reporting SAI 15.4
    version = "15.4.0"
    # When each key helper runs with that version
    sai_key = sai_known_bad_key(model, version)
    sai_arg = sai_skip_known_bad(model, version)
    bench_arg = benchmark_skip_known_bad(model, version)
    fboss2_arg = fboss2_skip_known_bad(model, version)
    sdk = sdk_version_for_model(model, version)
    # Then every key and the SDK version use 15.4.0.0_odp
    assert sai_key == sai
    assert sai_arg == f" --skip-known-bad-tests {sai}"
    assert bench_arg == f" --skip-known-bad-tests {bench}"
    assert fboss2_arg == f" --skip-known-bad-tests {fboss2}"
    assert sdk == "15.4.0.0_odp"


@pytest.mark.parametrize(
    "version",
    [
        None,
        "",
        "15.4",
        "15.4.0.0",
        "15.4.0~rc1",
        "package sai-runtime is not installed",
    ],
)
@pytest.mark.parametrize("helper", _KEY_HELPERS)
def test_missing_or_unparseable_version_falls_back(version, helper):
    # Given a TH6 model with a missing or malformed version
    model = "nh4220f"
    # When a key helper runs with that version
    result = helper(model, version)
    # Then it returns the static result
    assert result == helper(model)


_LEABA_MODELS = ("wedge800cact", "nhcw800f")


@pytest.mark.parametrize("model", _LEABA_MODELS)
@pytest.mark.parametrize("version", ["25.11.4210.7", "26.2.4210", "15.4.0"])
@pytest.mark.parametrize("helper", _KEY_HELPERS)
def test_leaba_keeps_static_key(model, version, helper):
    # Given a Cisco (Leaba) model's static result
    static = helper(model)
    # When a key helper runs with any version, Broadcom-looking or not
    result = helper(model, version)
    # Then it returns the static result
    assert result == static


def test_unknown_model_has_no_key():
    # Given a real model with no key and a made-up one
    keyless, made_up = "wedge800bnhp", "no-such-model"
    # When the helpers run with a version
    key = sai_known_bad_key(keyless, "15.4.0")
    arg = sai_skip_known_bad(keyless, "15.4.0")
    sdk = sdk_version_for_model(made_up, "15.4.0")
    # Then there is no key, no skip argument and no SDK version
    assert key is None
    assert arg == ""
    assert sdk is None


# ---------------------------------------------------------------------------
# BaseHwTestRunner._sai_runtime_version
# ---------------------------------------------------------------------------


def _connected(runner_cls, sai_runtime_reply):
    """runner_cls with ssh/scp mocked as if connected.

    sai_runtime_reply is run_cmd's (rc, output) for the sai-runtime query;
    every other command (variant-flags cat, ...) finds nothing.
    """
    runner = runner_cls()
    runner.ssh_client = MagicMock()

    def run_cmd(cmd, *args, **kwargs):  # noqa: ARG001
        return sai_runtime_reply if "sai-runtime" in cmd else (1, "")

    runner.ssh_client.run_cmd.side_effect = run_cmd
    runner.scp_client = MagicMock()
    runner.scp_client.get_file.return_value = (1, "no such file")
    return runner


def _sai_runtime_queries(runner):
    return [
        c
        for c in runner.ssh_client.run_cmd.call_args_list
        if "sai-runtime" in c.args[0]
    ]


def test_sai_runtime_version_read_once():
    # Given a connected DUT whose RPM reports 15.4.0
    runner = _connected(SaiAgentTestRunner, (0, "15.4.0\n"))
    # When the version is asked for twice
    first = runner._sai_runtime_version()
    second = runner._sai_runtime_version()
    # Then both calls return 15.4.0 from a single rpm -q
    assert first == second == "15.4.0"
    queries = _sai_runtime_queries(runner)
    assert len(queries) == 1
    assert "rpm -q" in queries[0].args[0]


@pytest.mark.parametrize(
    "reply",
    [
        (1, "package sai-runtime is not installed\n"),
        (0, ""),
        (0, "14.2.0\n15.4.0\n"),
        (255, "ssh: connect to host dut port 22: Connection refused"),
    ],
)
def test_sai_runtime_version_unreadable_is_none_and_cached(reply):
    # Given a DUT whose rpm -q fails, prints nothing or prints two versions
    runner = _connected(SaiAgentTestRunner, reply)
    # When the version is asked for twice
    first = runner._sai_runtime_version()
    second = runner._sai_runtime_version()
    # Then both calls return None from a single query
    assert first is None
    assert second is None
    assert len(_sai_runtime_queries(runner)) == 1


@pytest.mark.parametrize("version", ["25.11.4210.7", "15.4", "15.4.0~rc1"])
def test_sai_runtime_version_not_xyz_is_none_and_cached(version):
    # Given a DUT whose RPM version isn't X.Y.Z (e.g. Cisco's)
    runner = _connected(SaiAgentTestRunner, (0, f"{version}\n"))
    # When the version is asked for twice
    first = runner._sai_runtime_version()
    second = runner._sai_runtime_version()
    # Then both calls return None from a single query
    assert first is None
    assert second is None
    assert len(_sai_runtime_queries(runner)) == 1


def test_sai_runtime_version_ssh_error_is_none():
    # Given an SSH client that raises mid-command
    runner = SaiAgentTestRunner()
    runner.ssh_client = MagicMock()
    runner.ssh_client.run_cmd.side_effect = OSError("socket closed")
    # When the version is asked for
    version = runner._sai_runtime_version()
    # Then it returns None instead of raising
    assert version is None


def test_sai_runtime_version_ignores_stderr_lines():
    # Given rpm output with a stderr line before the version
    runner = _connected(SaiAgentTestRunner, (0, "stderr: warning: rpmdb\n15.4.0\n"))
    # When the version is read
    version = runner._sai_runtime_version()
    # Then only the version line counts
    assert version == "15.4.0"


def test_sai_runtime_version_none_when_not_connected():
    # Given a runner with no SSH client
    runner = SaiAgentTestRunner()
    # When the version is asked for
    version = runner._sai_runtime_version()
    # Then it returns None
    assert version is None


# ---------------------------------------------------------------------------
# Runners end to end
# ---------------------------------------------------------------------------

_RUNNER_KEYS = [
    (SaiTestRunner, "brcm/15.4.0.0_odp/15.4.0.0_odp/tomahawk6"),
    (SaiAgentTestRunner, "brcm/15.4.0.0_odp/15.4.0.0_odp/tomahawk6"),
    (BenchmarkTestRunner, "brcm/15.4.0.0_odp/tomahawk6/nh4220f"),
    (Fboss2IntegrationTestRunner, "nh4220f/brcm-15.4.0.0_odp"),
]


@pytest.mark.parametrize(("runner_cls", "key"), _RUNNER_KEYS)
def test_runner_keys_a_15_4_dut_on_15_4(runner_cls, key):
    # Given nh4220f on a DUT reporting 15.4.0
    runner = _connected(runner_cls, (0, "15.4.0\n"))
    # When the runner builds its test arguments
    args = runner.test_args("nh4220f")
    # Then they carry the 15.4 key and no 14.2 key
    assert f"--skip-known-bad-tests {key}" in args
    assert "14.2.0.0_odp" not in args


@pytest.mark.parametrize("runner_cls", [cls for cls, _ in _RUNNER_KEYS])
@pytest.mark.parametrize(
    "reply", [(0, "14.2.0\n"), (1, "package sai-runtime is not installed\n")]
)
def test_runner_args_unchanged_on_14_2_dut_or_unreadable_version(runner_cls, reply):
    # Given nh4220f on a 14.2 DUT, or one whose version can't be read, and the
    # args an unconnected runner builds from the static table
    runner = _connected(runner_cls, reply)
    expected = runner_cls().test_args("nh4220f")
    # When the connected runner builds its test arguments
    args = runner.test_args("nh4220f")
    # Then they match the static ones, which use 14.2
    assert args == expected
    assert "14.2.0.0_odp" in expected


@pytest.mark.parametrize("runner_cls", [cls for cls, _ in _RUNNER_KEYS])
def test_runner_leaba_dut_keeps_static_key(runner_cls):
    # Given a Cisco DUT reporting 25.11.4210.7, and the args an unconnected
    # runner builds from the static table
    runner = _connected(runner_cls, (0, "25.11.4210.7\n"))
    expected = runner_cls().test_args("wedge800cact")
    # When the connected runner builds its test arguments
    args = runner.test_args("wedge800cact")
    # Then they match the static Leaba ones
    assert args == expected
