#!/usr/bin/env python3
# @noautodeps
# Copyright Meta Platforms, Inc. and affiliates.

"""Helpers for run_test.py that enrich gtest XML output.

Separated from run_test.py to keep the parent file close to upstream:
this module holds the test-infra-specific helpers (stream tee, exit-info
classifier, XML stream injection, synthetic-failure XML emitter, etc.).
"""

import os
import re
import signal
import time
import xml.etree.ElementTree as ET
from contextlib import suppress
from datetime import datetime, timezone

# XML 1.0 forbids most C0 controls; ANSI escape codes (CSI sequences with
# \x1b[…) and stray NULs from SAI/SDK trace output trigger ParseError
# downstream if embedded verbatim into <system-out>/<system-err>/<failure>.
_XML10_FORBIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f￾￿]")


def _scrub_for_xml(text: str) -> str:
    """Replace XML-1.0-illegal control characters with U+FFFD."""
    return _XML10_FORBIDDEN.sub("�", text)


def _atomic_write_bytes(path: str, data: bytes) -> None:
    """Write `data` to `path` via a sibling tmpfile + os.replace.

    The result is either the new content or the previous content, never a
    partial write — important for `inject_streams_into_xml` and the
    synthetic-XML emitter, both of which rewrite XML the gtest binary may
    have just successfully produced. The tmpfile is cleaned up on replace
    failure so a disk-full / EBUSY doesn't leave `.tmp` siblings behind.
    """
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(tmp_path, path)
    except OSError:
        with suppress(FileNotFoundError):
            os.unlink(tmp_path)
        raise


class StreamTee:
    """Streams chunks to a writer while retaining a head + tail byte window.

    Used to (a) re-echo a child process's stdout/stderr to the parent in
    real time so `test.log` is preserved verbatim and (b) keep a bounded
    in-memory snapshot of the first `head_bytes` and last `tail_bytes`
    for XML embedding on failures. Memory is bounded regardless of stream
    size. BrokenPipeError on the writer is suppressed so a closed parent
    stdout does not abort capture.

    The `tail_bytes` default must stay generous enough to contain the gtest
    summary line (`[       OK ] TestName (N ms)`); `_run_test()` greps for
    it inside the snapshot to do prefix-injection. If the test emits more
    than `tail_bytes` AFTER the summary, the prefix path silently falls
    over to the synthetic-XML emitter.
    """

    def __init__(
        self,
        writer,
        head_bytes: int = 4096,
        tail_bytes: int = 61440,
    ):
        self._writer = writer
        self._head = bytearray()
        self._head_cap = head_bytes
        # bytearray slice-trim is O(chunk); a deque(maxlen=tail_bytes).extend
        # on a bytes object iterates one int per byte.
        self._tail = bytearray()
        self._tail_cap = tail_bytes
        self._total = 0
        self._pipe_broken = False

    def consume(self, chunk: bytes) -> None:
        if not chunk:
            return
        self._total += len(chunk)
        if len(self._head) < self._head_cap:
            need = self._head_cap - len(self._head)
            self._head.extend(chunk[:need])
        self._tail.extend(chunk)
        if len(self._tail) > self._tail_cap:
            del self._tail[: len(self._tail) - self._tail_cap]
        if not self._pipe_broken:
            try:
                self._writer(chunk)
            except BrokenPipeError:
                self._pipe_broken = True

    def snapshot(self) -> bytes:
        """Return head + (optional marker) + tail (head/tail style truncation)."""
        head = bytes(self._head)
        tail = bytes(self._tail)
        if self._total <= len(head) + len(tail):
            overlap = len(head) + len(tail) - self._total
            return head + tail[overlap:]
        omitted = self._total - len(head) - len(tail)
        marker = f"\n\n[... {omitted} bytes truncated by run_test.py ...]\n\n".encode()
        return head + marker + tail


def pipe_to_tee(pipe, tee: StreamTee) -> None:
    """Drain a child-process pipe into a tee. Used as a Thread target."""
    try:
        for chunk in iter(lambda: pipe.read(65536), b""):
            tee.consume(chunk)
    finally:
        pipe.close()


def exit_info(returncode: int, timed_out: bool) -> dict:
    """Classify subprocess outcome from returncode + timeout flag.

    Returns {"kind": one of "OK"/"FAIL"/"CRASH"/"TIMEOUT",
             "signal": signal name str or None,
             "code":   returncode int or None for TIMEOUT}.
    """
    if timed_out:
        return {"kind": "TIMEOUT", "signal": None, "code": None}
    if returncode < 0:
        sig = -returncode
        try:
            name = signal.Signals(sig).name
        except ValueError:
            name = f"SIG{sig}"
        return {"kind": "CRASH", "signal": name, "code": returncode}
    if returncode > 0:
        return {"kind": "FAIL", "signal": None, "code": returncode}
    return {"kind": "OK", "signal": None, "code": 0}


def inject_streams_into_xml(
    xml_path: str, stdout_bytes: bytes, stderr_bytes: bytes
) -> bool:
    """Add <system-out>/<system-err> children to the relevant <testcase>(s).

    Single-testcase XML: stamp streams on it (the typical _run_test() case).
    Multi-testcase XML (TYPED_TEST / parametrized expansions where one
    --gtest_filter matches several entries): stamp only on testcases with a
    <failure> child so passers don't get unrelated stream content. Bytes
    are decoded with errors="replace" and scrubbed of XML-1.0-illegal
    control chars; the write is atomic via tmpfile + os.replace.

    Returns True on a successful update, False if the XML is malformed or
    has no testcases to enrich (caller should leave the file untouched).
    """
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return False
    testcases = list(tree.getroot().iter("testcase"))
    if not testcases:
        return False
    if len(testcases) == 1:
        targets = testcases
    else:
        targets = [tc for tc in testcases if tc.find("failure") is not None]
        if not targets:
            return False
    stdout_text = (
        _scrub_for_xml(stdout_bytes.decode("utf-8", "replace"))
        if stdout_bytes
        else None
    )
    stderr_text = (
        _scrub_for_xml(stderr_bytes.decode("utf-8", "replace"))
        if stderr_bytes
        else None
    )
    for testcase in targets:
        if stdout_text is not None:
            existing = testcase.find("system-out")
            if existing is not None:
                existing.text = stdout_text
            else:
                ET.SubElement(testcase, "system-out").text = stdout_text
        if stderr_text is not None:
            existing = testcase.find("system-err")
            if existing is not None:
                existing.text = stderr_text
            else:
                ET.SubElement(testcase, "system-err").text = stderr_text
    payload = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        tree.getroot(), encoding="utf-8"
    )
    _atomic_write_bytes(xml_path, payload)
    return True


def emit_test_boundary(
    kind: str,
    test_name: str,
    prefix: str,
    info: dict | None = None,
    duration_sec: float | None = None,
) -> None:
    """Print a forward-compat sentinel line bounding a single gtest run.

    kind in {"START", "END"}. Lands in test.log via parent stdout redirect.
    Consumers (QPN, T-RECS) can grep these to byte-range a per-test slice
    of the giant test.log without parsing the whole file.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if kind == "START":
        line = f"::NH_TEST_START name={test_name} prefix={prefix} ts={ts} ::"
    else:
        info = info or {"kind": "UNKNOWN", "signal": None, "code": None}
        status = info.get("kind", "UNKNOWN")
        code = info.get("code")
        sig = info.get("signal") or "-"
        ms = int((duration_sec or 0.0) * 1000)
        exit_str = "-" if code is None else str(code)
        line = (
            f"::NH_TEST_END   name={test_name} prefix={prefix} ts={ts} "
            f"status={status} exit={exit_str} signal={sig} ms={ms} ::"
        )
    print(line, flush=True)


_CORE_DUMP_DIRS = [
    "/var/core",
    "/var/lib/systemd/coredump",
]


_CORE_DUMP_MTIME_SLACK_SEC = 2.0


def find_recent_core_dump(
    start_time: float,
    deadline_sec: float = 2.0,
    poll_interval_sec: float = 0.1,
) -> str | None:
    """Return absolute path of the newest core file with mtime >= start_time.

    Polls until a matching file appears or `deadline_sec` elapses.
    systemd-coredumpd compresses the core asynchronously, so the file in
    /var/lib/systemd/coredump may not exist at the moment `proc.wait()`
    returns. mtime is compared with `_CORE_DUMP_MTIME_SLACK_SEC` of slack
    to absorb sub-second skew between filesystem mtime and `time.time()`.
    Picks the newest matching file by mtime to avoid attaching an
    unrelated leftover from a sibling process.
    """
    deadline = time.monotonic() + deadline_sec
    cutoff = start_time - _CORE_DUMP_MTIME_SLACK_SEC
    while True:
        best_path: str | None = None
        best_mtime = 0.0
        for dir_path in _CORE_DUMP_DIRS:
            if not os.path.isdir(dir_path):
                continue
            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        try:
                            if entry.is_file():
                                mtime = entry.stat().st_mtime
                                if mtime >= cutoff and mtime > best_mtime:
                                    best_path = entry.path
                                    best_mtime = mtime
                        except OSError:
                            continue
            except OSError:
                continue
        if best_path is not None:
            return best_path
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll_interval_sec)


def write_synthetic_failure_xml(
    xml_path: str,
    test_to_run: str,
    info: dict,
    stdout_tail: bytes = b"",
    stderr_tail: bytes = b"",
    core_dump_path: str | None = None,
    duration_sec: float = 0.0,
) -> None:
    """Write a rich GTest-compatible XML when the binary failed to emit one.

    Replaces the previous bare "<failure message='Test binary exited with
    return code N'/>" record. The new record carries:
      - <failure message=...> with the contextual one-line summary and an
        optional core-dump pointer (no embedded stream content — that lives
        in <system-out>/<system-err> to avoid duplicating bytes)
      - <properties> with addressable key/value pairs for fingerprinting
      - <system-out>/<system-err> tails for human + matcher triage

    Write is atomic — tmpfile + os.replace — so a partial write cannot
    leave a half-formed XML behind.
    """
    parts = test_to_run.split(".", 1)
    suite_name = parts[0] if len(parts) == 2 else "Unknown"
    case_name = parts[1] if len(parts) == 2 else test_to_run
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    kind = info.get("kind", "UNKNOWN")
    sig = info.get("signal")
    code = info.get("code")

    if kind == "CRASH":
        msg = f"CRASH: killed by {sig} (exit {code}) after {duration_sec:.3f}s"
    elif kind == "TIMEOUT":
        msg = f"TIMEOUT after {duration_sec:.3f}s"
    elif kind == "FAIL":
        msg = f"FAIL: test binary exited with code {code} after {duration_sec:.3f}s"
    else:
        msg = f"{kind}: no per-test XML emitted by test binary"

    body = f"{msg}\n\nCore dump: {core_dump_path}" if core_dump_path else msg

    testsuites = ET.Element(
        "testsuites",
        tests="1",
        failures="1",
        disabled="0",
        errors="0",
        time=f"{duration_sec:.3f}",
        timestamp=timestamp,
    )
    testsuite = ET.SubElement(
        testsuites,
        "testsuite",
        name=suite_name,
        tests="1",
        failures="1",
        disabled="0",
        errors="0",
        time=f"{duration_sec:.3f}",
    )
    testcase = ET.SubElement(
        testsuite,
        "testcase",
        name=case_name,
        classname=suite_name,
        time=f"{duration_sec:.3f}",
    )
    properties = ET.SubElement(testcase, "properties")
    ET.SubElement(properties, "property", name="exit_kind", value=kind)
    if sig is not None:
        ET.SubElement(properties, "property", name="exit_signal", value=sig)
    if code is not None:
        ET.SubElement(properties, "property", name="exit_code", value=str(code))
    if core_dump_path:
        ET.SubElement(
            properties, "property", name="core_dump_path", value=core_dump_path
        )
    ET.SubElement(
        properties, "property", name="duration_sec", value=f"{duration_sec:.3f}"
    )

    failure = ET.SubElement(testcase, "failure", message=msg)
    failure.text = body

    if stdout_tail:
        ET.SubElement(testcase, "system-out").text = _scrub_for_xml(
            stdout_tail.decode("utf-8", "replace")
        )
    if stderr_tail:
        ET.SubElement(testcase, "system-err").text = _scrub_for_xml(
            stderr_tail.decode("utf-8", "replace")
        )

    ET.indent(testsuites)
    payload = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        testsuites, encoding="utf-8"
    )
    _atomic_write_bytes(xml_path, payload)
