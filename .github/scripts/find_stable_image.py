#!/usr/bin/env python3
"""Find stable image build IDs from `ng te stable-image -o json --nos fboss`.

Prints a JSON object mapping family -> build_id to stdout, e.g.:
    {"blkt_fboss": 79559, "fboss_qual": 76461, "gold_fboss": 79559,
     "minipack3": 79559, "wedge800bact": 79559, "wedge800cact": 79029}

Selection is scoped to the branch under validation, falling back to main for
families that branch has no qualified image for. See _target_branch().

On success, prints the JSON mapping to stdout and exits 0.
On failure, prints an ::error:: or ::warning:: message to stderr and
exits with a non-zero status code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


_BASE_CMD = ["ng", "te", "stable-image", "-o", "json", "--nos", "fboss"]


def _target_branch() -> str:
    """Branch whose images this run should prefer.

    The base branch on a pull_request, the checked-out ref otherwise. Both are
    bare branch names ("main", not "refs/heads/main"), which is what `-b` and
    the `branch` field of its output use -- the prefixed form matches nothing
    and would silently degrade every run to the main fallback.
    """
    return os.environ.get("GITHUB_BASE_REF") or os.environ.get("GITHUB_REF_NAME") or "main"


def _run_cmd(cmd: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def main() -> None:
    branch = _target_branch()
    # Query main alongside the branch so families it has not qualified still
    # resolve. An unknown branch (a stacked PR based on a feature branch) just
    # contributes no entries.
    cmd = _BASE_CMD + ["-b", branch]
    if branch != "main":
        cmd += ["-b", "main"]

    log(f"Querying for stable fboss image builds (branch: {branch})...")

    try:
        proc = _run_cmd(cmd)
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
        if not family or build_id is None:
            continue
        # One entry per (family, branch), so a family qualified on both the
        # target branch and main appears twice. Keying on family alone let
        # whichever entry came last win, which is how gold ended up on a build
        # from weeks earlier. Take the target branch's image, and main's only
        # for families the target branch has no image for.
        if img.get("branch") == branch or family not in builds:
            builds[family] = build_id

    if not builds:
        log("::warning::Could not parse any build ids from output")
        sys.exit(1)

    print(json.dumps(builds), flush=True)


if __name__ == "__main__":
    main()
