#!/usr/bin/env python3
# @noautodeps
# Copyright Meta Platforms, Inc. and affiliates.

"""Helpers for run_test.py that enrich gtest XML output.

Separated from run_test.py to keep the parent file close to upstream:
this module holds the test-infra-specific helpers (stream tee, exit-info
classifier, XML stream injection, synthetic-failure XML emitter, etc.).
"""

import json
import os
import re
import signal
import subprocess
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

    def __init__(self, writer, head_bytes: int = 4096, tail_bytes: int = 61440):
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


def inject_failure_into_xml(xml_path: str, message: str, text: str = "") -> bool:
    """Mark every passing <testcase> in `xml_path` as failed.

    Used when the test binary itself reported success but the harness
    detected an out-of-band failure during the test window -- typically a
    production agent (fboss_sw_agent / fboss_hw_agent@N) that crashed and
    was resurrected by systemd `Restart=` before the test noticed. gtest
    cannot see that, so the harness downgrades the recorded result here.

    Testcases that already carry a <failure> or <error> are left untouched;
    a <failure message=`message`> whose body is `text` (scrubbed of
    XML-1.0-illegal characters) is appended to the rest. The write is atomic
    (tmpfile + os.replace). Returns True on a successful update, False if the
    XML is malformed or has no testcases (caller should leave it untouched).
    """
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return False
    testcases = list(tree.getroot().iter("testcase"))
    if not testcases:
        return False
    body = _scrub_for_xml(text) if text else _scrub_for_xml(message)
    for testcase in testcases:
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            continue
        failure = ET.SubElement(testcase, "failure", message=_scrub_for_xml(message))
        failure.text = body
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


_CORE_DUMP_DIRS = ["/var/core", "/var/lib/systemd/coredump"]


_CORE_DUMP_MTIME_SLACK_SEC = 2.0


def _scan_core_dumps(cutoff: float) -> list[tuple[float, str]]:
    """One pass over `_CORE_DUMP_DIRS`: (mtime, path) of every core file with
    mtime >= cutoff, newest first. Unreadable directories and entries are
    skipped.
    """
    found: list[tuple[float, str]] = []
    for dir_path in _CORE_DUMP_DIRS:
        if not os.path.isdir(dir_path):
            continue
        try:
            with os.scandir(dir_path) as it:
                for entry in it:
                    try:
                        if not entry.is_file():
                            continue
                        mtime = entry.stat().st_mtime
                        if mtime >= cutoff:
                            found.append((mtime, entry.path))
                    except OSError:
                        continue
        except OSError:
            continue
    found.sort(reverse=True)
    return found


def find_recent_core_dump(
    start_time: float, deadline_sec: float = 2.0, poll_interval_sec: float = 0.1
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
        matches = _scan_core_dumps(cutoff)
        if matches:
            return matches[0][1]
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll_interval_sec)


def find_core_dumps_since(start_time: float) -> list[str]:
    """Return every core file with mtime >= start_time, newest first.

    Unlike `find_recent_core_dump` this does not poll and returns all
    matches, so a caller can check whether *any* process dumped core during
    a window (e.g. while a test ran against the production agents) and name
    each core in the failure reason.
    """
    cutoff = start_time - _CORE_DUMP_MTIME_SLACK_SEC
    return [path for _, path in _scan_core_dumps(cutoff)]


# systemd (PID 1) logs one line per main-process exit of every unit, e.g.
#   "fboss_hw_agent@0.service: Main process exited, code=dumped, status=6/ABRT"
# The unit name is also carried in the UNIT journal field. Parsing this line is
# preferable to `systemctl show -p NRestarts/Result`: NRestarts only moves for
# Restart=-triggered restarts (so a manual restart followed by a crash reads
# "unchanged"), and Result is reset to "success" the moment the unit is
# started again, so by the time a check runs after the test the crash has
# already been papered over. The journal keeps the record.
_MAIN_PROCESS_EXIT_RE = re.compile(
    r"^(?P<unit>\S+): Main process exited, code=(?P<code>\w+), "
    r"status=(?P<status>\d+)/(?P<name>\S+)$"
)
_OOM_KILL_RE = re.compile(
    r"^(?P<unit>\S+): A process of this unit has been killed by the OOM killer"
)

# Exits systemd's own `systemctl stop/restart` produces on a well-behaved unit:
# a clean exit, or termination by the stop signal (SIGTERM; SIGINT/SIGHUP for
# units that set KillSignal=) either as a signal death or as the 128+N status
# a shell/python wrapper returns when it relays it.
_GRACEFUL_SIGNALS = frozenset({"TERM", "INT", "HUP"})
_GRACEFUL_EXIT_STATUSES = frozenset(
    {0, 128 + signal.SIGTERM, 128 + signal.SIGINT, 128 + signal.SIGHUP}
)


def _classify_unit_exit(message: str) -> str | None:
    """Return a human-readable reason if `message` (a PID 1 journal line)
    records an unclean main-process exit of a unit, else None."""
    m = _OOM_KILL_RE.match(message)
    if m:
        return f"{m['unit']} killed by the OOM killer"
    m = _MAIN_PROCESS_EXIT_RE.match(message)
    if not m:
        return None
    code, status, name = m["code"], int(m["status"]), m["name"]
    if code == "exited" and status in _GRACEFUL_EXIT_STATUSES:
        return None
    if code == "killed" and name in _GRACEFUL_SIGNALS:
        return None
    what = {"dumped": "dumped core", "killed": "was killed", "exited": "exited"}.get(
        code, code
    )
    return f"{m['unit']} main process {what} (status={status}/{name})"


def find_unclean_unit_exits(start_time: float) -> list[str]:
    """Return one reason per systemd unit whose main process died uncleanly
    since `start_time` (crash, abort, OOM kill, non-zero exit), oldest first.

    Reads PID 1's journal records for the window. Clean stops and restarts --
    the ones the test infrastructure and the fboss2 CLI perform on purpose --
    exit 0 or die by SIGTERM and are not reported, so bouncing a unit inside
    the window is fine; only an exit systemd would count as a failure is.
    Returns [] when journalctl is unavailable or fails (workstations, the
    fboss-sim container).
    """
    since = int(start_time - _CORE_DUMP_MTIME_SLACK_SEC)
    try:
        result = subprocess.run(
            [
                "journalctl",
                "-q",
                "--no-pager",
                "-o",
                "json",
                f"--since=@{since}",
                "_PID=1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    reasons: list[str] = []
    for line in result.stdout.splitlines():
        try:
            message = json.loads(line).get("MESSAGE")
        except (ValueError, AttributeError):
            continue
        if not isinstance(message, str):
            continue
        reason = _classify_unit_exit(message)
        if reason:
            reasons.append(reason)
    return reasons


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
