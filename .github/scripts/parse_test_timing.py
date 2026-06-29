#!/usr/bin/env python3
"""Parse gtest output into a per-test timing table.

Usage: parse_test_timing.py <log_file> <dut>

Writes a markdown table to $GITHUB_STEP_SUMMARY (if set) and echoes it to
stdout. gtest per-test lines look like:
    [       OK ] SuiteName.TestName (123 ms)
    [  FAILED  ] SuiteName.TestName (456 ms)
"""

import os
import re
import sys


def main() -> None:
    log_path = sys.argv[1]
    dut = sys.argv[2]
    with open(log_path, "r", errors="replace") as f:
        log = f.read()

    pattern = re.compile(r"^\[\s+(OK|FAILED)\s+\]\s+(\S+)\s+\((\d+)\s*ms\)", re.M)
    rows = pattern.findall(log)
    print(
        f"Parsed {len(rows)} per-test result line(s) "
        f"from {log.count(chr(10))} log line(s)"
    )

    out = [f"## Integration Test Results ({dut})", ""]
    if not rows:
        out.append("_No per-test timing data parsed from log._")
    else:
        out.append("| # | Status | Test | Duration |")
        out.append("|---|--------|------|----------|")
        total_ms = passed = failed = 0
        for i, (status, name, ms) in enumerate(rows, 1):
            ms_i = int(ms)
            total_ms += ms_i
            if status == "OK":
                passed += 1
                icon = "✅ OK"
            else:
                failed += 1
                icon = "❌ FAILED"
            out.append(f"| {i} | {icon} | `{name}` | {ms_i} ms |")
        out += [
            "",
            f"**Total tests:** {len(rows)}  ",
            f"**Passed:** {passed}  ",
            f"**Failed:** {failed}  ",
            f"**Total duration:** {total_ms} ms ({total_ms / 1000:.1f} s)",
        ]

    table = "\n".join(out)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(table + "\n")

    # Echo into the step log so it is visible inline without the Summary tab.
    print("::group::Per-test timing table")
    print(table)
    print("::endgroup::")


if __name__ == "__main__":
    main()
