#!/usr/bin/env python3
"""Find a suitable DUT from `nh tb show available` output.

This mirrors the existing shell/awk logic used in the e2e_cli_test workflow:
- Run `nh tb show available`
- Look for the first row where:
  * name ($2) matches the provided prefix (e.g. "gold2")
  * in_service ($5) contains "True"
  * healthy ($6) contains "True"
  * and the name is not in the incompatible list (e.g. gold208)

Example `nh tb show available` output (truncated):

    +---------------+------------------------+---------+------------+---------+-----------+
    | name          | topology               | owner   | in_service | healthy | remaining |
    +---------------+------------------------+---------+------------+---------+-----------+
    | blkt156       | t1-8                   | testbot | True       | True    | N/A       |
    | blkt162       | t1-8                   | testbot | True       | True    | N/A       |
    | fboss101      | standalone             |         | False      | True    | N/A       |
    | fboss102      | t1-8                   |         | False      | True    | N/A       |
    | gold207       | t1-8                   | testbot | True       | True    | N/A       |
    | gold210       | t1-8                   | testbot | True       | True    | N/A       |
    | gold211_ix101 | MINT                   |         | True       | True    | N/A       |
    | gold404       | t1-8                   | testbot | True       | True    | N/A       |
    | gold405       | t0-8                   | testbot | True       | True    | N/A       |

On success, prints ONLY the DUT name to stdout and exits 0.
On failure (no suitable DUT or command error), prints an ::error:: or
::warning:: message to stderr and exits non-zero.
"""

from __future__ import annotations

import subprocess
import sys
from typing import List


INCOMPATIBLE_DUTS = {"gold208"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def parse_dut_from_output(lines: List[str], dut_prefix: str) -> str | None:
    """Parse nh tb show available output and return the first matching DUT name.

    This replicates the awk logic:
      $2 ~ /gold2/ && $5 ~ /True/ && $6 ~ /True/ and not in excluded list.
    Columns: $2=name | $3=topology | $4=owner | $5=in_service | $6=healthy.
    """

    for line in lines:
        if "| True" not in line:
            # The original pipeline had a `grep '| True'` before awk.
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 6:
            # Need at least: index, name, topology, owner, in_service, healthy
            continue

        name = parts[1]
        in_service = parts[4]
        healthy = parts[5]

        if dut_prefix in name and "True" in in_service and "True" in healthy:
            if name in INCOMPATIBLE_DUTS:
                continue
            return name

    return None


def main() -> None:
    log("Running 'nh tb show available' to find DUT...")

    try:
        proc = subprocess.run(
            ["nh", "tb", "show", "available"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        log(f"::error::Failed to run 'nh tb show available': {e}")
        sys.exit(1)

    output = proc.stdout or ""
    log("nh tb show available output:")
    if output:
        if not output.endswith("\n"):
            output += "\n"
        sys.stderr.write(output)
        sys.stderr.flush()

    if proc.returncode != 0:
        log("::error::'nh tb show available' exited with non-zero status")
        sys.exit(proc.returncode or 1)

    # Allow an optional prefix argument (e.g. "gold2") so the caller can
    # select a DUT family without hard-coding it here.
    dut_prefix = sys.argv[1] if len(sys.argv) > 1 else "gold2"

    dut_name = parse_dut_from_output(output.splitlines(), dut_prefix)
    if not dut_name:
        log(
            "::warning::No healthy and in_service gold* DUT available. Skipping E2E tests."
        )
        sys.exit(1)

    # IMPORTANT: print only the DUT name to stdout for the GHA step to capture.
    print(dut_name, flush=True)


if __name__ == "__main__":
    main()
