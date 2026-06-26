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


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _parse_secure_boot_duts(returncode: int, stdout: str, stderr: str) -> set[str]:
    """Parse the output of 'nh attributes device filter secure_boot_enforced=true --json'.

    On any failure the error is logged as a warning and an empty set is returned"""
    if returncode != 0:
        log(
            f"::warning::Failed to query secure-boot DUTs from attributes service "
            f"(exit {returncode}): {stderr.strip()}"
        )
        return set()

    try:
        records = json.loads(stdout)
        duts = {r["device_name"] for r in records if r.get("device_name")}
    except (json.JSONDecodeError, KeyError) as e:
        log(f"::warning::Failed to parse secure-boot DUTs from attributes service: {e}")
        return set()

    log(f"Secure-boot DUTs from attributes service: {sorted(duts) or '(none)'}")
    return duts


def _is_incompatible_dut(name: str, secure_boot_duts: set[str]) -> bool:
    """Return True if the DUT should be excluded from selection.

    Blocks:
    - Devices with secure boot enforced (from the attributes service)
    - gold1xx P1 units: differ enough from P2 that major changes are
    required before FBOSS works.
    """
    if name in secure_boot_duts:
        return True
    if name.startswith("gold1"):
        return True
    return False


def _iter_matching_duts(
    duts: List[dict], dut_prefix: str, secure_boot_duts: set[str]
) -> Iterator[str]:
    """Yield DUT names matching the prefix that are healthy, in-service, and not blocked."""
    for dut in duts:
        name = dut.get("name", "")
        if (
            name.startswith(dut_prefix)
            and dut.get("in_service") is True
            and dut.get("healthy") is True
            and not _is_incompatible_dut(name, secure_boot_duts)
        ):
            yield name


def parse_all_duts_from_output(
    duts: List[dict],
    dut_prefix: str | None = None,
    secure_boot_duts: set[str] | None = None,
) -> List[str]:
    """Return all matching DUT names, shuffled.

    If dut_prefix is None, searches across all FBOSS_PLATFORMS.
    """
    if secure_boot_duts is None:
        secure_boot_duts = set()
    prefixes = (dut_prefix,) if dut_prefix else FBOSS_PLATFORMS
    seen: set[str] = set()
    results: List[str] = []
    for prefix in prefixes:
        for name in _iter_matching_duts(duts, prefix, secure_boot_duts):
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

    log("Running 'ng tb show available' and querying attributes service in parallel...")

    try:
        tb_proc = subprocess.Popen(
            ["ng", "tb", "show", "available", "--output", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as e:  # noqa: BLE001
        log(f"::error::Failed to launch 'ng tb show available': {e}")
        sys.exit(1)

    try:
        attr_proc = subprocess.Popen(
            ["nh", "attributes", "device", "filter", "secure_boot_enforced=true", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        attr_stdout, attr_stderr = None, None
    except Exception as e:  # noqa: BLE001
        log(f"::warning::Failed to launch 'nh attributes device filter': {e}")
        attr_proc = None
        attr_stdout, attr_stderr = "", ""
        attr_returncode = 0

    tb_stdout, _ = tb_proc.communicate()
    if attr_proc is not None:
        attr_stdout, attr_stderr = attr_proc.communicate()
        attr_returncode = attr_proc.returncode

    output = tb_stdout or ""
    log("ng tb show available output:")
    if output:
        if not output.endswith("\n"):
            output += "\n"
        sys.stderr.write(output)
        sys.stderr.flush()

    if tb_proc.returncode != 0:
        log("::error::'ng tb show available --output json' exited with non-zero status")
        sys.exit(tb_proc.returncode or 1)

    try:
        dut_list = json.loads(output)
    except json.JSONDecodeError as e:
        log(f"::error::Failed to parse JSON from 'ng tb show available --output json': {e}")
        sys.exit(1)

    secure_boot_duts = _parse_secure_boot_duts(attr_returncode, attr_stdout, attr_stderr)
    duts = parse_all_duts_from_output(dut_list, dut_prefix, secure_boot_duts)
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
