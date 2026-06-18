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

import xml.etree.ElementTree as ET

import pytest
from nh_test_xml_utils import exit_info, inject_streams_into_xml, StreamTee

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
