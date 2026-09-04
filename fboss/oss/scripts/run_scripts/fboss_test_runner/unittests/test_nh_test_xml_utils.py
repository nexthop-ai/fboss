#!/usr/bin/env python3
# @noautodeps
# Copyright Meta Platforms, Inc. and affiliates.

"""Unit tests for nh_test_xml_utils, the gtest-XML enrichment helpers used by
run_test.py's TestRunner to produce a rich tr.xml: <system-out>/<system-err>
stream injection, the bounded-memory StreamTee, and the subprocess exit
classifier.

These cover Nexthop-specific behavior that has no upstream equivalent. They
live in their own module (importing nh_test_xml_utils directly) so they are
decoupled from the benchmark/run_test test imports.
"""

import json
import os
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import nh_test_xml_utils as _xml_mod
import pytest
from nh_test_xml_utils import (
    exit_info,
    find_core_dumps_since,
    find_unclean_unit_exits,
    inject_failure_into_xml,
    inject_streams_into_xml,
    StreamTee,
)

_GTEST_XML_FIXTURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="1" failures="0" errors="0" time="0.1">
  <testsuite name="HwVlanTest" tests="1" failures="0">
    <testcase name="VlanAdd" classname="HwVlanTest" time="0.1" status="run"/>
  </testsuite>
</testsuites>
"""


def _write_xml_fixture(tmp_path, content: bytes) -> str:
    p = tmp_path / "tr_current_run.xml"
    p.write_bytes(content)
    return str(p)


def test_inject_streams_idempotent(tmp_path):
    """Calling twice does not duplicate <system-out>/<system-err>."""
    xml_path = _write_xml_fixture(tmp_path, _GTEST_XML_FIXTURE)
    inject_streams_into_xml(xml_path, b"first", b"errfirst")
    inject_streams_into_xml(xml_path, b"second", b"errsecond")
    tree = ET.parse(xml_path)
    testcase = next(tree.getroot().iter("testcase"))
    assert len(testcase.findall("system-out")) == 1
    assert len(testcase.findall("system-err")) == 1
    assert testcase.find("system-out").text == "second"
    assert testcase.find("system-err").text == "errsecond"


def test_inject_streams_scrubs_control_chars(tmp_path):
    """ANSI escapes (\\x1b) and NUL bytes from SAI/SDK output must be scrubbed
    so the resulting XML stays parseable downstream."""
    xml_path = _write_xml_fixture(tmp_path, _GTEST_XML_FIXTURE)
    inject_streams_into_xml(xml_path, b"", b"ANSI: \x1b[31mred\x1b[0m NUL\x00 byte")
    reparsed = ET.parse(xml_path)
    text = next(reparsed.getroot().iter("testcase")).find("system-err").text
    assert "\x1b" not in text
    assert "\x00" not in text
    assert "red" in text


def test_inject_streams_returns_false_on_malformed_xml(tmp_path):
    """Garbage in the gtest XML must not crash _run_test; return False so the
    caller can fall through to the synthetic-failure path."""
    p = tmp_path / "bad.xml"
    p.write_bytes(b"this is not <xml")
    assert inject_streams_into_xml(str(p), b"stdout", b"stderr") is False
    assert p.read_bytes() == b"this is not <xml"


def test_inject_streams_is_atomic(tmp_path, monkeypatch):
    """A failed write must leave the original XML intact AND clean up the
    .tmp sibling (tmp + os.replace)."""
    xml_path = _write_xml_fixture(tmp_path, _GTEST_XML_FIXTURE)
    original = (tmp_path / "tr_current_run.xml").read_bytes()

    def angry_replace(*_a, **_kw):
        raise OSError("simulated disk-full at replace time")

    monkeypatch.setattr("nh_test_xml_utils.os.replace", angry_replace)
    with pytest.raises(OSError, match="simulated disk-full"):
        inject_streams_into_xml(xml_path, b"some out", b"some err")
    assert (tmp_path / "tr_current_run.xml").read_bytes() == original
    assert not (tmp_path / "tr_current_run.xml.tmp").exists()


def test_stream_tee_bounded_memory_under_large_input():
    """Feed 10 MB through a tee with small head/tail windows; the snapshot
    must stay bounded by head + tail + a small marker, regardless of input
    size, and total bytes-written must equal bytes-consumed (no drop)."""
    written = bytearray()
    head, tail = 4096, 65536
    tee = StreamTee(written.extend, head_bytes=head, tail_bytes=tail)
    chunk = b"X" * (64 * 1024)
    total = 10 * 1024 * 1024
    for _ in range(total // len(chunk)):
        tee.consume(chunk)
    snap = tee.snapshot()
    # Snapshot is bounded: head + tail + a single-line truncation marker.
    assert len(snap) <= head + tail + 256
    # Real-time tee path forwarded every byte regardless of snapshot trim.
    assert len(written) == total


def test_exit_info_branches():
    # OK
    assert exit_info(returncode=0, timed_out=False) == {
        "kind": "OK",
        "signal": None,
        "code": 0,
    }
    # FAIL
    assert exit_info(returncode=1, timed_out=False) == {
        "kind": "FAIL",
        "signal": None,
        "code": 1,
    }
    # CRASH (signal-killed; returncode is -signum)
    assert exit_info(returncode=-11, timed_out=False) == {
        "kind": "CRASH",
        "signal": "SIGSEGV",
        "code": -11,
    }
    # TIMEOUT overrides returncode
    assert exit_info(returncode=-9, timed_out=True) == {
        "kind": "TIMEOUT",
        "signal": None,
        "code": None,
    }


def test_inject_streams_multi_testcase_attaches_to_failures_only(tmp_path):
    # TYPED_TEST/parametric XMLs must attach streams only to the failing
    # testcase(s), not stamp them onto passers.
    multi = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="2" failures="1" errors="0">
  <testsuite name="HwVlanTest" tests="2" failures="1">
    <testcase name="VlanAdd/0" classname="HwVlanTest" time="0.1" status="run"/>
    <testcase name="VlanAdd/1" classname="HwVlanTest" time="0.1" status="run">
      <failure message="boom" type="">boom</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
    p = tmp_path / "multi.xml"
    p.write_bytes(multi)
    assert inject_streams_into_xml(str(p), b"stdout-data", b"stderr-data") is True
    tree = ET.parse(str(p))
    cases = {tc.get("name"): tc for tc in tree.getroot().iter("testcase")}
    assert cases["VlanAdd/0"].find("system-out") is None
    assert cases["VlanAdd/0"].find("system-err") is None
    assert cases["VlanAdd/1"].find("system-out").text == "stdout-data"
    assert cases["VlanAdd/1"].find("system-err").text == "stderr-data"


def test_inject_streams_multi_testcase_no_failures_returns_false(tmp_path):
    """If a multi-testcase XML has no <failure> children, we have no signal
    to attribute streams; leave the file alone."""
    multi = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="2" failures="0" errors="0">
  <testsuite name="HwVlanTest" tests="2" failures="0">
    <testcase name="VlanAdd/0" classname="HwVlanTest" time="0.1" status="run"/>
    <testcase name="VlanAdd/1" classname="HwVlanTest" time="0.1" status="run"/>
  </testsuite>
</testsuites>
"""
    p = tmp_path / "multi.xml"
    p.write_bytes(multi)
    original = p.read_bytes()
    assert inject_streams_into_xml(str(p), b"stdout", b"stderr") is False
    assert p.read_bytes() == original


# ---------------------------------------------------------------------------
# inject_failure_into_xml / find_core_dumps_since (agent-crash downgrade)
# ---------------------------------------------------------------------------

_PASSING_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="1" failures="0" disabled="0" errors="0" time="1.0" name="AllTests">
  <testsuite name="ConfigFooTest" tests="1" failures="0" disabled="0" errors="0" time="1.0">
    <testcase name="Bar" status="run" result="completed" time="1.0" classname="ConfigFooTest"/>
  </testsuite>
</testsuites>
"""

_FAILED_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="1" failures="1" disabled="0" errors="0" time="1.0" name="AllTests">
  <testsuite name="ConfigFooTest" tests="1" failures="1" disabled="0" errors="0" time="1.0">
    <testcase name="Bar" status="run" result="completed" time="1.0" classname="ConfigFooTest">
      <failure message="original">original</failure>
    </testcase>
  </testsuite>
</testsuites>
"""


def test_inject_failure_marks_passing_testcase(tmp_path):
    """A passing testcase gets a <failure> carrying the crash reason, so the
    aggregated XML counts it as failed."""
    xml_path = _write_xml_fixture(tmp_path, _PASSING_XML)
    assert inject_failure_into_xml(
        xml_path, "Agent crashed: hw NRestarts 0 -> 1", "detail"
    )
    testcase = next(ET.parse(xml_path).getroot().iter("testcase"))
    failures = testcase.findall("failure")
    assert len(failures) == 1
    assert failures[0].get("message") == "Agent crashed: hw NRestarts 0 -> 1"
    assert failures[0].text == "detail"


def test_inject_failure_leaves_existing_failure_alone(tmp_path):
    """An already-failed testcase must not get a second <failure> (gtest's own
    verdict stays the primary record)."""
    xml_path = _write_xml_fixture(tmp_path, _FAILED_XML)
    assert inject_failure_into_xml(xml_path, "Agent crashed", "")
    testcase = next(ET.parse(xml_path).getroot().iter("testcase"))
    failures = testcase.findall("failure")
    assert len(failures) == 1
    assert failures[0].get("message") == "original"


def test_inject_failure_returns_false_on_malformed_xml(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_bytes(b"<testsuites><testcase")
    assert inject_failure_into_xml(str(p), "x") is False
    assert p.read_bytes() == b"<testsuites><testcase"


def test_inject_failure_scrubs_control_chars(tmp_path):
    xml_path = _write_xml_fixture(tmp_path, _PASSING_XML)
    inject_failure_into_xml(xml_path, "msg\x1b[31m", "body\x00nul")
    testcase = next(ET.parse(xml_path).getroot().iter("testcase"))
    failure = testcase.find("failure")
    assert "\x1b" not in failure.get("message")
    assert "\x00" not in failure.text


def test_find_core_dumps_since_filters_by_time(tmp_path, monkeypatch):
    core_dir = tmp_path / "coredump"
    core_dir.mkdir()
    monkeypatch.setattr(_xml_mod, "_CORE_DUMP_DIRS", [str(core_dir)])
    monkeypatch.setattr(_xml_mod, "_CORE_DUMP_MTIME_SLACK_SEC", 0.0)

    old_agent = core_dir / "core.fboss_hw_agent-.0.abc.100.1000.zst"
    new_agent = core_dir / "core.fboss_hw_agent-.0.abc.200.2000.zst"
    new_sw = core_dir / "core.fboss_sw_agent.0.abc.300.3000.zst"
    new_other = core_dir / "core.some_other_bin.0.abc.400.4000.zst"
    for p in (old_agent, new_agent, new_sw, new_other):
        p.write_bytes(b"x")
    os.utime(old_agent, (1_000, 1_000))
    os.utime(new_agent, (5_000, 5_000))
    os.utime(new_sw, (6_000, 6_000))
    os.utime(new_other, (7_000, 7_000))

    # newest first, nothing older than the window; any process counts (a
    # non-agent core during a test window is a red signal too)
    assert find_core_dumps_since(2_000) == [str(new_other), str(new_sw), str(new_agent)]
    # empty window
    assert find_core_dumps_since(10_000) == []


def test_find_core_dumps_since_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(_xml_mod, "_CORE_DUMP_DIRS", [str(tmp_path / "does-not-exist")])
    assert find_core_dumps_since(0) == []


# ---------------------------------------------------------------------------
# find_unclean_unit_exits (journal scan for unit crashes during a test window)
# ---------------------------------------------------------------------------


def _journal(*messages: str) -> str:
    """journalctl -o json output: one record per line, PID 1 style."""
    return "\n".join(
        json.dumps({"_PID": "1", "UNIT": m.split(":", 1)[0], "MESSAGE": m})
        for m in messages
    )


def _patched_journalctl(stdout: str, returncode: int = 0):
    return patch.object(
        _xml_mod.subprocess,
        "run",
        return_value=MagicMock(stdout=stdout, returncode=returncode),
    )


def test_unclean_exits_reports_crashes_not_clean_stops():
    """Cores, kills by anything but the stop signal, OOM kills and non-zero
    exits are crashes. A clean exit, a SIGTERM death and the 128+15 status a
    wrapper relays on SIGTERM are what `systemctl stop/restart` produces and
    must not fail a test (the fboss2 CLI restarts the agents on every
    commit; a console logout bounces serial-getty with exit 0)."""
    out = _journal(
        "fboss_hw_agent@0.service: Main process exited, code=dumped, status=6/ABRT",
        "fboss_sw_agent.service: Main process exited, code=exited, status=0/SUCCESS",
        "serial-getty@ttyS0.service: Main process exited, code=exited, status=0/SUCCESS",
        "qsfp_service.service: Main process exited, code=killed, status=15/TERM",
        "hostcfgd.service: Main process exited, code=exited, status=143/n/a",
        "sensor_service.service: Main process exited, code=killed, status=11/SEGV",
        "fan_service.service: Main process exited, code=exited, status=1/FAILURE",
        "platform_manager.service: A process of this unit has been killed by the OOM killer.",
        "fboss_hw_agent@0.service: Scheduled restart job, restart counter is at 1.",
        "Started FBOSS hw agent.",
    )
    with _patched_journalctl(out) as run:
        reasons = find_unclean_unit_exits(1_000.0)
    assert reasons == [
        "fboss_hw_agent@0.service main process dumped core (status=6/ABRT)",
        "sensor_service.service main process was killed (status=11/SEGV)",
        "fan_service.service main process exited (status=1/FAILURE)",
        "platform_manager.service killed by the OOM killer",
    ]
    # one journalctl call, PID 1 only, window starts at start_time minus slack
    cmd = run.call_args[0][0]
    assert cmd[0] == "journalctl"
    assert "_PID=1" in cmd
    assert f"--since=@{int(1_000.0 - _xml_mod._CORE_DUMP_MTIME_SLACK_SEC)}" in cmd


def test_unclean_exits_ignores_unparseable_lines():
    out = (
        "not json\n"
        + json.dumps({"MESSAGE": ["array", "not", "str"]})
        + "\n"
        + _journal("x.service: Main process exited, code=dumped, status=11/SEGV")
    )
    with _patched_journalctl(out):
        assert find_unclean_unit_exits(0.0) == [
            "x.service main process dumped core (status=11/SEGV)"
        ]


def test_unclean_exits_empty_when_journalctl_unavailable():
    with _patched_journalctl("", returncode=1):
        assert find_unclean_unit_exits(0.0) == []
    with patch.object(_xml_mod.subprocess, "run", side_effect=FileNotFoundError):
        assert find_unclean_unit_exits(0.0) == []
