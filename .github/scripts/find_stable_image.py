#!/usr/bin/env python3
"""Find stable image build IDs from `ng te stable-image -o json --nos fboss`.

Prints a JSON object mapping family -> build_id to stdout, e.g.:
    {"blkt_fboss": 79559, "fboss_qual": 76461, "gold_fboss": 79559,
     "minipack3": 79559, "wedge800bact": 79559, "wedge800cact": 79029}

On success, prints the JSON mapping to stdout and exits 0.
On failure, prints an ::error:: or ::warning:: message to stderr and
exits with a non-zero status code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Dict


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


_BASE_CMD = ["ng", "te", "stable-image", "-o", "json", "--nos", "fboss"]


def _run_cmd(cmd: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def main() -> None:
    log("Querying for stable fboss image builds...")

    try:
        proc = _run_cmd(_BASE_CMD)
    except OSError as e:
        log(f"::error::Failed to run command: {e}")
        sys.exit(1)

    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()

    output = proc.stdout or ""
    log("Output:")
    log(output)

    if proc.returncode != 0:
        log("::error::Failed to query stable-image")
        sys.exit(proc.returncode or 1)

    try:
        images = json.loads(output)
    except json.JSONDecodeError as e:
        log(f"::error::Failed to parse JSON output: {e}")
        sys.exit(1)

    builds: Dict[str, int] = {}
    for img in images:
        family = img.get("family", "")
        build_id = img.get("build_id")
        if family and build_id is not None:
            builds[family] = build_id

    if not builds:
        log("::warning::Could not parse any build ids from output")
        sys.exit(1)

    print(json.dumps(builds), flush=True)


if __name__ == "__main__":
    main()
