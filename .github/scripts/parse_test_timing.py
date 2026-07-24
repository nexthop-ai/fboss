#!/usr/bin/env python3
"""Parse gtest output into a per-test timing table.

Usage: parse_test_timing.py <log_file> <dut>

Writes a markdown table to $GITHUB_STEP_SUMMARY (if set) and echoes it to
stdout. Per-test result lines look like:
    [       OK ] SuiteName.TestName (123 ms)      <- raw gtest output
    [ PASSED ] SuiteName.TestName (123 ms)        <- run_test.py summary
    [ FAILED ] SuiteName.TestName (456 ms)
    [ SKIPPED ] SuiteName.TestName (1 ms)
A run_test.py log contains BOTH: raw gtest output is teed through per test
invocation, then the final report re-lists every test. To avoid counting
tests twice, parsing is restricted to the final report (everything after the
last "Running all tests took" line) when that marker is present; a bare
gtest-binary log has no marker and is parsed in full.
"""

import os
import re
import sys


def main() -> None:
    log_path = sys.argv[1]
    dut = sys.argv[2]
    with open(log_path, "r", errors="replace") as f:
        log = f.read()

    marker = log.rfind("Running all tests took")
    region = log[marker:] if marker != -1 else log

    pattern = re.compile(
        r"^\[\s+(OK|PASSED|FAILED|TIMEOUT|SKIPPED)\s+\]\s+(\S+)\s+\((\d+)\s*ms\)",
        re.M,
    )
    rows = pattern.findall(region)
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
        total_ms = passed = failed = skipped = 0
        for i, (status, name, ms) in enumerate(rows, 1):
            ms_i = int(ms)
            total_ms += ms_i
            if status in ("OK", "PASSED"):
                passed += 1
                icon = "✅ OK"
            elif status == "SKIPPED":
                skipped += 1
                icon = "⏭️ SKIPPED"
            else:
                failed += 1
                icon = f"❌ {status}"
            out.append(f"| {i} | {icon} | `{name}` | {ms_i} ms |")
        out += [
            "",
            f"**Total tests:** {len(rows)}  ",
            f"**Passed:** {passed}  ",
            f"**Failed:** {failed}  ",
            f"**Skipped:** {skipped}  ",
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
