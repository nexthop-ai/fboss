#!/usr/bin/env python3
"""Find a suitable DUT from `ng tb show available --output json` output.

- Run `ng tb show available --output json`
- Look for entries where:
  * name matches a supported FBOSS platform prefix (gold)
  * in_service is true
  * healthy is true
  * and the name is not one of the incompatible devices

Example `ng tb show available --output json` output (truncated):

    [
      {
        "id": 34,
        "name": "gold405",
        "type": "FANOUT",
        "topology": "t0-8",
        "owner": null,
        "department": "software",
        "claim_time": null,
        "release_time": null,
        "long_running": false,
        "in_service": true,
        "healthy": true,
        "prototype": false,
        "extra_config": {}
      },
      ...
    ]

Usage:
  find_dut.py [prefix]

  Prints n randomly chosen DUT names to stdout and exits 0.
  Searches all FBOSS platforms if no prefix is given.

On success, prints ONLY the DUT name to stdout and exits 0.
On failure (no suitable DUT or command error), prints an ::error:: or
::warning:: message to stderr and exits non-zero.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from typing import Iterator, List

# Supported FBOSS platform prefixes: Golden Eagle, Wedge, Minipack
FBOSS_PLATFORMS = ("gold",)

# Known devices that have Secure Boot enforced and will fail to load the FBOSS image
SECURE_BOOT_DUTS= {"gold101", "gold208", "gold210"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _is_incompatible_dut(name: str) -> bool:
    """Return True if the DUT should be excluded from selection.

    Blocks:
    - Exact matches in SECURE_BOOT_DUTS
    - gold1xx P1 units: differ enough from P2 that major changes are
    required before FBOSS works.
    """
    if name in SECURE_BOOT_DUTS:
        return True
    if name.startswith("gold1"):
        return True
    return False


def _iter_matching_duts(duts: List[dict], dut_prefix: str) -> Iterator[str]:
    """Yield DUT names matching the prefix that are healthy, in-service, and not blocked."""
    for dut in duts:
        name = dut.get("name", "")
        if (
            name.startswith(dut_prefix)
            and dut.get("in_service") is True
            and dut.get("healthy") is True
            and not _is_incompatible_dut(name)
        ):
            yield name


def parse_all_duts_from_output(duts: List[dict], dut_prefix: str | None = None) -> List[str]:
    """Return all matching DUT names, shuffled.

    If dut_prefix is None, searches across all FBOSS_PLATFORMS.
    """
    prefixes = (dut_prefix,) if dut_prefix else FBOSS_PLATFORMS
    seen: set[str] = set()
    results: List[str] = []
    for prefix in prefixes:
        for name in _iter_matching_duts(duts, prefix):
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

    log("Running 'ng tb show available --output json' to find DUT(s)...")

    try:
        proc = subprocess.run(
            ["ng", "tb", "show", "available", "--output", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        log(f"::error::Failed to run 'ng tb show available --output json': {e}")
        sys.exit(1)

    output = proc.stdout or ""
    log("ng tb show available output:")
    if output:
        if not output.endswith("\n"):
            output += "\n"
        sys.stderr.write(output)
        sys.stderr.flush()

    if proc.returncode != 0:
        log("::error::'ng tb show available --output json' exited with non-zero status")
        sys.exit(proc.returncode or 1)

    try:
        dut_list = json.loads(output)
    except json.JSONDecodeError as e:
        log(f"::error::Failed to parse JSON from 'ng tb show available --output json': {e}")
        sys.exit(1)

    duts = parse_all_duts_from_output(dut_list, dut_prefix)
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
