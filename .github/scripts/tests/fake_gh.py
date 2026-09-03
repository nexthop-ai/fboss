#!/usr/bin/env python3
"""Fake `gh` for the rebase_upstream_pr.py test suite (installed on PATH).

Serves the two GitHub calls the script under test makes, backed by the
sandbox's local fork repository ($SANDBOX/fork.git):

  gh pr view <n> --repo facebook/fboss --json ...
  gh api --paginate repos/facebook/fboss/pulls?state=open...

The listing is emitted as two concatenated JSON arrays — exactly what
`gh api --paginate` produces — so open_fork_prs()'s page decoding is
exercised, and it includes a foreign-fork PR plus one with a deleted head
repo that discovery must filter out without crashing.

When $SANDBOX/merged101 exists, PR 101 flips to the upstream merged state:
gone from the listing, and its view shows the real merge signal — state
CLOSED (mergedAt null) plus a bot comment naming the landed sha (the flag
file's content).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SANDBOX = Path(os.environ["SANDBOX"])
FORK = SANDBOX / "fork.git"
BRANCHES = {101: "br1", 102: "br2", 103: "br3"}


def oid(branch: str) -> str:
    return subprocess.run(
        ["git", "--git-dir", str(FORK), "rev-parse", f"refs/heads/{branch}"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def merged_sha() -> str | None:
    flag = SANDBOX / "merged101"
    return flag.read_text().strip() if flag.exists() else None


def pr_view(number: int) -> dict:
    sha = merged_sha()
    if number == 101 and sha:
        return {
            "state": "CLOSED",
            "mergeCommit": None,
            "comments": [{"body": f"@someone merged this pull request in facebook/fboss@{sha}."}],
            "headRefName": "br1",
            "headRepositoryOwner": {"login": "nexthop-ai"},
            "author": {"login": "hillol-nexthop"},
            "body": "",
        }
    if number not in BRANCHES:
        sys.exit(f"fake gh: unknown pr {number}")
    branch = BRANCHES[number]
    return {
        "headRefName": branch,
        "headRefOid": oid(branch),
        "state": "OPEN",
        "mergeCommit": None,
        "comments": [],
        "body": "",
        "headRepositoryOwner": {"login": "nexthop-ai"},
        "author": {"login": "hillol-nexthop"},
    }


def rest_entry(number: int, branch: str, owner: str | None, body: str | None) -> dict:
    repo = {"owner": {"login": owner}} if owner else None
    return {"number": number, "head": {"ref": branch, "repo": repo}, "body": body}


def pulls_listing() -> str:
    page1 = []
    if not merged_sha():
        page1.append(rest_entry(101, "br1", "nexthop-ai", 'Based-on: "main"'))
    page1 += [
        rest_entry(102, "br2", "nexthop-ai", "Stacked on #101"),
        rest_entry(103, "br3", "nexthop-ai", "Stacked on #102"),
    ]
    page2 = [
        rest_entry(900, "other", "somebody", ""),
        rest_entry(901, "gone", None, None),  # deleted head repo
    ]
    return json.dumps(page1) + "\n" + json.dumps(page2)


def main() -> None:
    args = sys.argv[1:]
    if args[:2] == ["pr", "view"]:
        print(json.dumps(pr_view(int(args[2]))))
    elif args[:2] == ["api", "--paginate"] and args[2].startswith("repos/facebook/fboss/pulls"):
        print(pulls_listing())
    else:
        sys.exit(f"fake gh: unhandled: {args}")


if __name__ == "__main__":
    main()
