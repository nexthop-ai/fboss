#!/usr/bin/env python3
"""Find a suitable DUT from `nh tb show available` output.

- Run `nh tb show available`
- Look for rows where:
  * name ($2) matches a supported FBOSS platform prefix (gold)
  * in_service ($5) contains "True"
  * healthy ($6) contains "True"
  * and the name is not in INCOMPATIBLE_DUTS

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
    | wdg154        | t1-8                   |         | True       | True    | N/A       |

Usage:
  find_dut.py [prefix]

  Prints n randomly chosen DUT names to stdout and exits 0/
  Searches all FBOSS platforms if no prefix is given.

On success, prints ONLY the DUT name to stdout and exits 0.
On failure (no suitable DUT or command error), prints an ::error:: or
::warning:: message to stderr and exits non-zero.
"""

from __future__ import annotations

import random
import subprocess
import sys
from typing import Iterator, List

# Supported FBOSS platform prefixes: Golden Eagle, Wedge, Minipack
FBOSS_PLATFORMS = ("gold")

# Known devices that are incompatible with the CLI integration tests
INCOMPATIBLE_DUTS = {"gold208"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _iter_matching_duts(lines: List[str], dut_prefix: str) -> Iterator[str]:
    """Yield DUT names matching the prefix that are healthy, in-service, and not blocked.

    Replicates the awk logic:
      $2 ~ /prefix/ && $5 ~ /True/ && $6 ~ /True/ and not in INCOMPATIBLE_DUTS.
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
            if name not in INCOMPATIBLE_DUTS:
                yield name


def parse_all_duts_from_output(lines: List[str], dut_prefix: str | None = None) -> List[str]:
    """Return all matching DUT names, shuffled.

    If dut_prefix is None, searches across all FBOSS_PLATFORMS.
    """
    prefixes = (dut_prefix,) if dut_prefix else FBOSS_PLATFORMS
    seen: set[str] = set()
    results: List[str] = []
    for prefix in prefixes:
        for name in _iter_matching_duts(lines, prefix):
            if name not in seen:
                seen.add(name)
                results.append(name)
    random.shuffle(results)
    return results


def main() -> None:
    args = sys.argv[1:]
    count = 1
    if "--count" in args:
        idx = args.index("--count")
        count = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    dut_prefix: str | None = args[0] if args else None

    log("Running 'nh tb show available' to find DUT(s)...")

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

    lines = output.splitlines()

    duts = parse_all_duts_from_output(lines, dut_prefix)
    if not duts:
        log(
            "::warning::No healthy and in_service FBOSS DUT available. Skipping integration tests."
        )
        sys.exit(1)

    # IMPORTANT: print only DUT name(s) to stdout for the GHA step to capture.
    # parse_all_duts_from_output already shuffles, so order is randomised.
    print("\n".join(duts[:count]), flush=True)


if __name__ == "__main__":
    main()
