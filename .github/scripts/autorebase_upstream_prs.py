#!/usr/bin/env python3
"""Dispatch rebase-upstream-pr.yml for upstream PRs whose author opted in with /autorebase.

Scans open facebook/fboss PRs labelled both "CLA Signed" and "nexthop", and for
each one whose *author* has posted a comment containing `/autorebase`, dispatches
.github/workflows/rebase-upstream-pr.yml with rebase_onto=main (all other inputs
left at their defaults).

Why the gate matters: a dispatched rebase builds the PR's code and runs its
tests on our on-prem CloudStack runners, with the rebase workflow's secrets in
scope and inside our internal network (build caches, Harbor, lab DUTs). Anything
in the PR — a CMakeLists.txt, a getdeps manifest, a test — therefore runs as
arbitrary code inside our CI. facebook/fboss accepts PRs from anyone, and this
sweep acts without a human looking at the PR, so it must never dispatch for
code that didn't come from Nexthop. The checks below enforce that; don't loosen
them without an equivalent guarantee.

Eligibility (all must hold, re-verified against the PR itself rather than the
search index, which can be stale):
  - open, and labelled both "CLA Signed" and "nexthop";
  - head branch lives on exactly the nexthop-ai/fboss fork, not merely any
    nexthop-ai repo. This is the key security check: only Nexthop can push to
    that repo, so the code under test is ours no matter who opened the PR or
    who applied the labels;
  - base branch is main. Stacked PRs (base = another PR's branch) are skipped:
    the rebase workflow treats any member as a handle to the whole stack, so
    they are rebased along with their root once the root opts in, and become
    eligible themselves once their parent lands and they retarget main;
  - an issue comment by the PR author contains the /autorebase command.
    Comments from anyone else — including maintainers — are ignored, so
    nobody else can make the rebase run.

Requires UPSTREAM_GH_TOKEN (read facebook/fboss) and, unless --plan or --dry-run
is given, DISPATCH_GH_TOKEN (actions:write on the repo running the rebase
workflow, $GITHUB_REPOSITORY). With --plan FILE the eligible PR numbers are
written to FILE as a JSON list and nothing is dispatched; the workflow then
dispatches each one as its author (see resolve_upstream_pat.sh).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

UPSTREAM_REPO = os.environ.get("AUTOREBASE_UPSTREAM_REPO", "facebook/fboss")
FORK_REPO = os.environ.get("AUTOREBASE_FORK_REPO", "nexthop-ai/fboss")
REQUIRED_LABELS = ("CLA Signed", "nexthop")
BASE_BRANCH = "main"
REBASE_WORKFLOW = "rebase-upstream-pr.yml"
# Standalone token: not part of a path/URL (foo/autorebase) or a longer word
# (/autorebased).
AUTOREBASE_RE = re.compile(r"(?<![\w/])/autorebase(?![\w-])")


def info(msg: str) -> None:
    print(f"💡 INFO:  {msg}", flush=True)


def gh_api(path: str, token: str) -> dict:
    out = subprocess.run(
        ["gh", "api", path], check=True, capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token}
    ).stdout
    return json.loads(out)


def gh_api_list(path: str, token: str, jq: str) -> list[dict]:
    """Paginated GET; `jq` selects the items of each page, emitted one JSON object per line."""
    out = subprocess.run(
        ["gh", "api", "--paginate", "--jq", jq, path],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "GH_TOKEN": token},
    ).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def search_candidates(token: str) -> list[int]:
    labels = " ".join(f'label:"{label}"' for label in REQUIRED_LABELS)
    q = quote(f"repo:{UPSTREAM_REPO} is:pr is:open {labels}", safe="")
    items = gh_api_list(f"search/issues?per_page=100&q={q}", token, ".items[] | {number}")
    return sorted({item["number"] for item in items})


def author_opted_in(author: str, comments: list[dict]) -> bool:
    author = author.lower()
    if not author:
        return False
    return any(
        ((c.get("user") or {}).get("login") or "").lower() == author and AUTOREBASE_RE.search(c.get("body") or "")
        for c in comments
    )


def pr_skip_reason(pr: dict) -> str | None:
    """Return why `pr` (a REST pulls/N object) is ineligible regardless of comments, or None."""
    if pr.get("state") != "open":
        return f"state is {pr.get('state')}"
    labels = {label["name"] for label in pr.get("labels", [])}
    missing = [label for label in REQUIRED_LABELS if label not in labels]
    if missing:
        return f"missing label(s) {missing}"
    head_repo = ((pr.get("head") or {}).get("repo") or {}).get("full_name")
    if head_repo != FORK_REPO:
        return f"head repo is {head_repo!r}, not {FORK_REPO!r}"
    base = (pr.get("base") or {}).get("ref")
    if base != BASE_BRANCH:
        return f"targets {base!r}, not {BASE_BRANCH!r} (stacked PR)"
    return None


def evaluate(pr: dict, comments_fn) -> str | None:
    """Return None if `pr` should be rebased, else the skip reason. `comments_fn()` is only
    called (one paginated fetch) once the PR itself is eligible."""
    reason = pr_skip_reason(pr)
    if reason:
        return reason
    author = (pr.get("user") or {}).get("login") or ""
    if not author_opted_in(author, comments_fn()):
        return f"no /autorebase comment from the author ({author})"
    return None


def dispatch(pr_number: int, token: str, repo: str, ref: str) -> None:
    subprocess.run(
        [
            "gh", "workflow", "run", REBASE_WORKFLOW,
            "--repo", repo,
            "--ref", ref,
            "-f", f"pr_number={pr_number}",
            "-f", f"rebase_onto={BASE_BRANCH}",
        ],
        check=True,
        env={**os.environ, "GH_TOKEN": token},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Report what would be dispatched; dispatch nothing")
    parser.add_argument("--pr", type=int, help="Evaluate a single upstream PR instead of searching")
    parser.add_argument("--plan", metavar="FILE", help="Write eligible PR numbers to FILE as JSON; dispatch nothing")
    args = parser.parse_args()

    upstream_token = os.environ.get("UPSTREAM_GH_TOKEN", "")
    dispatch_token = os.environ.get("DISPATCH_GH_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF_NAME") or "main"
    if not upstream_token or (not (args.dry_run or args.plan) and not (dispatch_token and repo)):
        print("❌ ERROR: UPSTREAM_GH_TOKEN, DISPATCH_GH_TOKEN and GITHUB_REPOSITORY are required", file=sys.stderr)
        return 1

    candidates = [args.pr] if args.pr else search_candidates(upstream_token)
    info(f"{len(candidates)} candidate PR(s) in {UPSTREAM_REPO}")

    dispatched, skipped, failed = [], [], []
    for number in candidates:
        pr = gh_api(f"repos/{UPSTREAM_REPO}/pulls/{number}", upstream_token)
        reason = evaluate(
            pr,
            lambda: gh_api_list(
                f"repos/{UPSTREAM_REPO}/issues/{number}/comments?per_page=100",
                upstream_token,
                ".[] | {user: {login: .user.login}, body}",
            ),
        )
        if reason:
            skipped.append((number, reason))
            info(f"#{number}: skip — {reason}")
            continue
        if args.dry_run or args.plan:
            info(f"#{number}: would dispatch {REBASE_WORKFLOW} (rebase_onto={BASE_BRANCH})")
            dispatched.append(number)
            continue
        try:
            dispatch(number, dispatch_token, repo, ref)
            info(f"#{number}: dispatched {REBASE_WORKFLOW} (rebase_onto={BASE_BRANCH})")
            dispatched.append(number)
        except subprocess.CalledProcessError as e:
            print(f"❌ ERROR: #{number}: dispatch failed: {e}", file=sys.stderr)
            failed.append(number)

    if args.plan:
        with open(args.plan, "w") as f:
            json.dump(dispatched, f)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        verb = "Would dispatch" if args.dry_run else "Eligible" if args.plan else "Dispatched"
        lines = ["## /autorebase sweep\n", f"**{verb}:** {len(dispatched)}\n"]
        lines += [f"- [#{n}](https://github.com/{UPSTREAM_REPO}/pull/{n})\n" for n in dispatched]
        if failed:
            lines += [f"\n**Dispatch failed:** {len(failed)}\n"]
            lines += [f"- [#{n}](https://github.com/{UPSTREAM_REPO}/pull/{n})\n" for n in failed]
        lines += [f"\n<details><summary>Skipped: {len(skipped)}</summary>\n\n"]
        lines += [f"- [#{n}](https://github.com/{UPSTREAM_REPO}/pull/{n}): {r}\n" for n, r in skipped]
        lines += ["\n</details>\n"]
        with open(summary_path, "a") as f:
            f.writelines(lines)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
