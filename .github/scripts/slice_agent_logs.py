#!/usr/bin/env python3
"""Print wedge_agent.log slices covering each failed test's run window.

Runs ON the DUT. run_test.py brackets every test invocation with sentinel
lines in the test log:
    ::NH_TEST_START name=Suite.Test prefix=cold_boot. ts=2026-07-13T05:31:20Z ::
    ::NH_TEST_END   name=Suite.Test prefix=cold_boot. ts=2026-07-13T05:31:45Z status=FAIL exit=1 signal=- ms=25000 ::
For every END with status != OK, this prints the agent log lines whose glog
timestamps fall inside [start - slack, end + slack]. This targets the exact
agent activity behind a failure, which a fixed-size end-of-run tail can miss
because run_test.py keeps running (and cold booting) after a failure.

Assumes DUT clock is UTC: NH_TEST timestamps are UTC and glog stamps local
time, so a non-UTC DUT would shift the windows.

Usage: slice_agent_logs.py [test_log] [agent_log]
"""

import re
import sys
from datetime import datetime, timedelta

TEST_LOG = sys.argv[1] if len(sys.argv) > 1 else "/tmp/fboss2_itest.log"
AGENT_LOG = (
    sys.argv[2] if len(sys.argv) > 2 else "/var/facebook/logs/fboss/wedge_agent.log"
)
SLACK = timedelta(seconds=5)
MAX_LINES_PER_WINDOW = 500

BOUNDARY_RE = re.compile(
    r"::NH_TEST_(START|END)\s+name=(\S+) prefix=(\S+) ts=(\S+)"
    r"(?: status=(\S+) exit=\S+ signal=\S+ ms=\S+)? ::"
)
# glog line prefix: I0713 05:31:22.622126 <tid> <file:line>] msg
GLOG_RE = re.compile(r"^[IWEF](\d{4} \d\d:\d\d:\d\d)")


def parse_sentinel_ts(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


def failed_test_windows(text: str) -> list[tuple[str, str, datetime, datetime]]:
    starts: dict[tuple[str, str], datetime] = {}
    windows = []
    for m in BOUNDARY_RE.finditer(text):
        kind, name, prefix, ts, status = m.group(1, 2, 3, 4, 5)
        if kind == "START":
            starts[(name, prefix)] = parse_sentinel_ts(ts)
        elif status and status != "OK":
            start = starts.get((name, prefix))
            if start:
                windows.append(
                    (name, status, start - SLACK, parse_sentinel_ts(ts) + SLACK)
                )
    return windows


def glog_line_ts(line: str, year: int) -> datetime | None:
    m = GLOG_RE.match(line)
    if not m:
        return None
    try:
        return datetime.strptime(f"{year}{m.group(1)}", "%Y%m%d %H:%M:%S")
    except ValueError:  # e.g. Feb 29 artifacts from a wrong year guess
        return None


def print_window(name: str, status: str, lo: datetime, hi: datetime) -> None:
    print(f"=== {name} ({status}) agent log {lo:%H:%M:%S}..{hi:%H:%M:%S} UTC ===")
    # glog omits the year; take it from the window itself. A run never spans
    # a year boundary by more than the slack, so this is safe.
    year = lo.year
    printed = 0
    inside = False
    try:
        with open(AGENT_LOG, errors="replace") as f:
            for line in f:
                ts = glog_line_ts(line, year)
                if ts is not None:
                    inside = lo <= ts <= hi
                if inside:
                    printed += 1
                    if printed <= MAX_LINES_PER_WINDOW:
                        sys.stdout.write(line)
    except OSError as e:
        print(f"cannot read {AGENT_LOG}: {e}")
        return
    if printed > MAX_LINES_PER_WINDOW:
        print(f"... truncated ({printed - MAX_LINES_PER_WINDOW} more lines in window)")
    if printed == 0:
        print("(no agent log lines in this window)")


def main() -> None:
    try:
        with open(TEST_LOG, errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"no test log to slice from: {e}")
        return
    windows = failed_test_windows(text)
    if not windows:
        print("no failed tests found in NH_TEST markers — nothing to slice")
        return
    for window in windows:
        print_window(*window)


if __name__ == "__main__":
    main()
