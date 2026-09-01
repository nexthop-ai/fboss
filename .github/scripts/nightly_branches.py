#!/usr/bin/env python3
"""Decide which branches the Nightly Build builds.

Usage: nightly_branches.py <families.yaml> [--repo OWNER/REPO]

Prints a JSON list to stdout: always "main" first, then every `branch:` under
`branch_families` in Tide's config that is an exact nh-fboss-* name (in file
order, no duplicates). With --repo, each of those branches must exist in that
repo (checked with `gh api`, needs GH_TOKEN).

Anything that stops the whole list from being read — unreadable file, no
branch_families block, a listed branch that does not exist — prints an
::error:: line to stderr and exits 1; the workflow then builds main only and
warns on Slack. A single bad rule (a pattern such as nh-fboss-* instead of a
branch name) is skipped with a ::warning::, so the other branches still build.

The file is parsed with PyYAML (the same parser Tide uses); the k8s runner
image ships it since nexthop-ai/nhsystem-ops#622.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import NoReturn

import yaml

FBOSS_PREFIX = "nh-fboss-"
GLOB_CHARS = set("*?[")


def fail(msg: str) -> NoReturn:
    print(f"::error::{msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def branch_rules(text: str, path: str) -> list[str]:
    """Every `branch:` value under branch_families, in file order."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        fail(f"{path} is not valid YAML: {e}")
    if not isinstance(doc, dict) or "branch_families" not in doc:
        fail(f"no 'branch_families:' in {path} — did the Tide config format change?")
    return [
        str(rule["branch"])
        for rule in doc["branch_families"] or []
        if "branch" in rule
    ]


def nightly_branches(text: str, path: str) -> list[str]:
    branches = ["main"]
    for value in branch_rules(text, path):
        if not value.startswith(FBOSS_PREFIX):
            continue  # SONiC release rules etc.
        if GLOB_CHARS & set(value):
            # One author's glob must not stop the correctly-listed branches
            # from building; skip the rule and leave a trace in the run log.
            print(
                f"::warning::branch_families rule '{value}' is a pattern; "
                "the nightly can only build exact branch names - skipping it.",
                file=sys.stderr,
            )
            continue
        if value not in branches:
            branches.append(value)
    return branches


def branch_exists(repo: str, branch: str) -> bool:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/{branch}", "--silent"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decide which branches the Nightly Build builds."
    )
    parser.add_argument("families_yaml")
    parser.add_argument(
        "--repo", help="OWNER/REPO in which every EFT branch must exist"
    )
    args = parser.parse_args()

    try:
        with open(args.families_yaml, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        fail(f"cannot read {args.families_yaml}: {e.strerror}")

    branches = nightly_branches(text, args.families_yaml)

    if args.repo:
        for branch in branches[1:]:
            if not branch_exists(args.repo, branch):
                fail(
                    f"Tide lists '{branch}' but it does not exist in {args.repo}. "
                    "Fix the Tide config or create the branch."
                )

    print(json.dumps(branches, separators=(",", ":")))


if __name__ == "__main__":
    main()
