#!/usr/bin/env python3
"""Find the latest successful private-fboss build in Nexis and print its build id.

This script is intended to be called from GitHub Actions. It runs the
`nexis show` CLI, logs the full output to stderr, and then parses the first
row whose second '|'‑separated column is a numeric build id.

Example Nexis output (truncated):

    +-------+--------+--------+--------+--------+---------+-------------+-------+-------+
    |   id  |  repo  | branch | commit | userid |  status |   created   |  time | vm_ip |
    +-------+--------+--------+--------+--------+---------+-------------+-------+-------+
    | 32316 | pfboss |  main  |        | runner | success |    22:15    | 1h18m |       |
    | 32264 | pfboss |  main  |        | runner | success |  Wed 19:40  | 1h41m |       |
    | 32212 | pfboss |  main  |        | runner | success |  Wed 17:18  | 1h18m |       |

On success, it prints ONLY the build id to stdout and exits 0.
On failure, it prints an ::error:: or ::warning:: message to stderr and
exits with a non-zero status code.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Optional


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> None:
    log("Querying Nexis for latest successful private-fboss build...")

    try:
        proc = subprocess.run(
            [
                "nexis",
                "show",
                "--repo",
                "nh/private-fboss",
                "--status",
                "success",
                "--branch",
                "main",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        log("::error::Failed to run Nexis CLI: {e}".format(e=e))
        sys.exit(1)

    output = proc.stdout or ""

    log("Nexis output:")
    # Mirror the bash script's behavior of echoing the full Nexis output.
    if output:
        # Ensure exactly one trailing newline.
        if not output.endswith("\n"):
            output = output + "\n"
        sys.stderr.write(output)
        sys.stderr.flush()

    if proc.returncode != 0:
        log("::error::Failed to query Nexis for private-fboss builds")
        sys.exit(proc.returncode or 1)

    latest_build_id: Optional[str] = None
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) < 2:
            continue
        col2 = parts[1].strip()
        # Match a pure integer, like the awk /^[[:space:]]*[0-9]+[[:space:]]*$/
        if re.fullmatch(r"[0-9]+", col2):
            latest_build_id = col2
            break

    if not latest_build_id:
        log("::warning::Could not parse latest build id from Nexis output")
        sys.exit(1)

    # IMPORTANT: print only the build id on stdout so the GHA step can capture it.
    print(latest_build_id, flush=True)


if __name__ == "__main__":
    main()
