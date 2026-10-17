"""Builders shared across the test_runner unit tests.

Plain functions rather than fixtures so module-level helpers and parametrize
tables can call them too. Fixtures live in conftest.py.
"""

import json
import os
import subprocess
import tarfile
from contextlib import ExitStack
from typing import NamedTuple
from unittest.mock import MagicMock, patch

from tests.libs.test_runner.platform_mapping import PortInfo
from tests.libs.test_runner.variants import CageInfo, SubportInfo

FORWARDING_URL = "http://example/forwarding.tar.zst"

# Nexis env for a forwarding runner: tarball URL + build_id (the cache key).
NEXIS_ENV = {
    "FBOSS_FORWARDING_TARBALL_URL": FORWARDING_URL,
    "FBOSS_BUILD_ID": "12345",
}

VARIANT_FLAGFILE = "--hwrev_state1_substate1_respin0=true\n"

# pid -> (speed, iphy lanes). Optical ids follow switch_config.thrift; 50/45/54
# are the copper 800G_8, 400G_4 and 200G_2 profiles.
PROFILES = {
    91: (3200000, 8),
    90: (1600000, 8),
    39: (800000, 8),
    38: (400000, 4),
    25: (200000, 2),
    24: (200000, 4),
    23: (100000, 1),
    22: (100000, 4),
    50: (800000, 8),
    45: (400000, 4),
    54: (200000, 2),
}
MEDIUM_BY_ID = {39: "optical", 38: "optical", 25: "optical", 50: "copper", 45: "copper", 54: "copper"}
LANES_BY_ID = {pid: lanes for pid, (_, lanes) in PROFILES.items()}

# Cage shapes: {subport: [profile ids]}.
FULL = {1: [39, 38, 25, 23], 2: [23], 3: [25, 23], 4: [23], 5: [38, 25, 23], 6: [23], 7: [25, 23], 8: [23]}
PIPE_LIMITED = {1: [39, 38], 5: [38]}
COPPER = {1: [50, 45, 54], 3: [54], 5: [45, 54], 7: [54]}


def make_cage(subports, lanes=8, base_id=100, profiles=PROFILES, core=None):
    return CageInfo(
        controlling="unused/1",
        lanes=lanes,
        subports={
            sub: SubportInfo(base_id + sub, {pid: profiles[pid] for pid in pids})
            for sub, pids in subports.items()
        },
        core=core,
    )


def make_port(logical_id, *profile_ids, speed=None):
    """A PortInfo at the first profile id, offering all of them at PROFILES speeds."""
    profile_ids = profile_ids or (39,)
    return PortInfo(
        logical_id=logical_id,
        profile_id=profile_ids[0],
        speed=PROFILES[profile_ids[0]][0] if speed is None else speed,
        profiles={pid: PROFILES[pid][0] for pid in profile_ids},
    )


def symmetric_pairs(*pairs):
    """{a: z, z: a, ...}: the shape TEST_SNAKE_PAIRS and the resolvers use."""
    out = {}
    for a, z in pairs:
        out[a], out[z] = z, a
    return out


def fake_ssh_handler(deployed_sha=None, flagfile=None):
    """Answer the probes the runner lifecycle issues: the DUT slice marker
    (``deployed_sha``, None meaning no marker), the variant flagfile
    (``flagfile``, None meaning none on the DUT), and ``systemctl is-active``
    as a stopped agent so _wait_for_agent_settled returns at once."""

    def handler(cmd, *args, **kwargs):
        if cmd.startswith("cat ") and ".sha" in cmd:
            return (0, deployed_sha + "\n") if deployed_sha is not None else (1, "")
        if cmd.startswith("cat ") and "variant_flags" in cmd:
            return (1, "") if flagfile is None else (0, flagfile)
        if "systemctl is-active" in cmd:
            return (3, "inactive\n")
        return (0, "ok")

    return handler


def make_runner(runner_cls, tc=None, env=None, deployed_sha=None, flagfile=None):
    """A runner with SSH/SCP mocked, optionally with tc populated the way
    setup() does (``tc`` plus ``env`` applied through getenvvars())."""
    runner = runner_cls()
    if tc is not None:
        runner.tc = dict(tc)
        with patch.dict(os.environ, env or {}, clear=True):
            runner.getenvvars()
    runner.ssh_client = MagicMock()
    runner.scp_client = MagicMock()
    runner.scp_client.put_file.return_value = (0, "ok")
    runner.scp_client.get_file.return_value = (1, "")
    runner.ssh_client.run_cmd.side_effect = fake_ssh_handler(deployed_sha, flagfile)
    return runner


def json_scp(runner, dut_json):
    """Make scp get_file hand back ``dut_json`` as the local file and put_file
    capture what is uploaded, keyed by remote path. Returns the uploads dict."""
    uploaded = {}

    def fake_get(remote, local):
        with open(local, "w", encoding="utf-8") as f:
            json.dump(dut_json, f)
        return (0, "ok")

    def fake_put(local, remote):
        with open(local, encoding="utf-8") as f:
            uploaded[remote] = json.load(f)
        return (0, "ok")

    runner.scp_client.get_file.side_effect = fake_get
    runner.scp_client.put_file.side_effect = fake_put
    return uploaded


def capture_tar_names(runner):
    """Make scp put_file record the member names of the tar it is handed. The
    slice is deleted right after upload, so it has to be read inside the mock."""
    names = []

    def capture_put(local, remote, *a, **k):
        with tarfile.open(local) as t:
            names.extend(t.getnames())
        return (0, "ok")

    runner.scp_client.put_file.side_effect = capture_put
    return names


def make_cabling_runner(
    runner_cls, tmp_path, ports_info, *, gtest_filter=None, filters=(), pairs=None, monkeypatch=None
):
    """A cabling-aware runner with TEST_PORTS_INFO written to tmp_path.

    Returns (runner, cabling_path). ``pairs`` (needs ``monkeypatch``) also
    writes a snake-pairs file and points TEST_SNAKE_PAIRS at it; None clears
    the variable so no stale pairing leaks in from the environment.
    """
    runner = make_runner(runner_cls)
    runner.tc = {"model": "m4062nhp", "gtest_filter": gtest_filter, "filters": list(filters)}
    cabling_path = tmp_path / "ports_info.json"
    cabling_path.write_text(json.dumps(ports_info))
    if monkeypatch is not None:
        if pairs is not None:
            pairs_path = tmp_path / "snake_pairs.json"
            pairs_path.write_text(json.dumps(pairs))
            monkeypatch.setenv("TEST_SNAKE_PAIRS", str(pairs_path))
        else:
            monkeypatch.delenv("TEST_SNAKE_PAIRS", raising=False)
    return runner, str(cabling_path)


class CablingRun(NamedTuple):
    result: bool
    prepare_calls: list
    execute_calls: list
    skipped: list | None
    settle_waits: int
    commands: list


def drive_cabling_aware(runner, cabling_path, *, skip_tr_xml=False, execute_result=True, capture_cmds=False):
    """Run _run_cabling_aware with the DUT-touching steps stubbed out.

    prepare_calls holds the (model, ports) of every _prepare_pass, execute_calls
    the filter each pass executed with, skipped what was reported to the JUnit
    merge (None when skip_tr_xml), settle_waits how often the agent-settle
    poll ran, and commands (when capture_cmds) the test command of each pass.
    """
    prepare_calls = []
    execute_calls = []
    commands = []

    def fake_prepare_pass(model, ports):
        prepare_calls.append((model, list(ports)))

    def fake_execute(model, log_local, xml_local, skip_tr_xml):  # noqa: ARG001
        gtest_filter = runner.tc.get("gtest_filter")
        execute_calls.append(gtest_filter if gtest_filter else list(runner.tc["filters"]))
        if capture_cmds:
            commands.append(runner.build_test_cmd(model))
        return execute_result

    with ExitStack() as stack:
        stack.enter_context(patch.object(runner, "_prepare_pass", side_effect=fake_prepare_pass))
        stack.enter_context(patch.object(runner, "pre_test"))
        stack.enter_context(patch.object(runner, "post_test"))
        wait = stack.enter_context(patch.object(runner, "_wait_for_agent_settled"))
        stack.enter_context(patch.object(runner, "_execute_test_binary", side_effect=fake_execute))
        merge = stack.enter_context(patch.object(runner, "_merge_junit_results"))
        stack.enter_context(patch.object(runner, "normalize_test_results_file"))
        result = runner._run_cabling_aware(cabling_path, {}, skip_tr_xml=skip_tr_xml)

    skipped = merge.call_args.kwargs["skipped"] if merge.call_args else None
    return CablingRun(result, prepare_calls, execute_calls, skipped, wait.call_count, commands)


def fake_run_factory(present_paths):
    """subprocess.run replacement for the Nexis deploy path: wget downloads an
    empty tarball, `tar -xf` materializes ``present_paths`` in the extract dir.
    The slice itself is packed with tarfile (no subprocess), so there is no -cf."""
    recorded = {"calls": []}

    def fake_run(cmd, **kwargs):
        recorded["calls"].append(cmd)
        if cmd[0] == "wget" and "-O" in cmd:
            dest_path = cmd[cmd.index("-O") + 1]
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(b"")
        elif cmd[0] == "tar" and "-xf" in cmd:
            extract_dir = cmd[2]
            for rel in present_paths:
                rel_clean = rel.rstrip("/")
                full = os.path.join(extract_dir, rel_clean)
                if rel.endswith("/"):
                    os.makedirs(full, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "w") as f:
                        f.write("x")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return fake_run, recorded


def production_features_fixture():
    """Minimal asic_production_features.materialized_JSON shape, modeled on
    the real SRv6 entries (feature 100 = SRV6_ENCAP, 104 = SRV6_MIDPOINT)."""
    return {
        "asicToFeatures": {"tomahawk6": [1, 100, 104], "tomahawk5": [1, 104]},
        "asicToFeatureNames": {
            "tomahawk6": ["L3_FORWARDING", "SRV6_ENCAP", "SRV6_MIDPOINT"],
            "tomahawk5": ["L3_FORWARDING", "SRV6_MIDPOINT"],
        },
        "featureSupportSpecs": [
            {
                "feature": 100,
                "supportedFrom": [
                    {
                        "asics": ["tomahawk5", "tomahawk6"],
                        "sdk": 1,
                        "minSdkVersion": "15.4_ea_odp",
                    }
                ],
            },
            {
                "feature": 104,
                "supportedFrom": [
                    {
                        "asics": ["tomahawk5", "tomahawk6"],
                        "sdk": 1,
                        "minSdkVersion": "15.4_ea_odp",
                    }
                ],
            },
        ],
    }
