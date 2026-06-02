#!/usr/bin/env python3
"""
Reconcile Meta-amended upstream PRs back into the private fork.

When we send a PR to facebook/fboss (upstream), Meta imports it internally,
sometimes *amends the code* (their internal linters/compilers are stricter than
the OSS ones), lands it, and the meta-codesync bot pushes the landed commit back
to GitHub and *closes* our PR (it never shows as "merged" from GitHub's view).
This leaves two problems:

  1. Drift  - Meta's amendments never make it back into origin
              (nexthop-ai/private-fboss), so our internal tree diverges from what
              actually shipped.
  2. Litter - the source branch of the upstream PR (on our nexthop-ai/fboss
              staging fork) is left dangling with "unmerged commits".

This script detects those meta-codesync closures, compares what landed against
what we submitted, and:

  - opens a small reconcile PR in origin carrying just Meta's incremental
    amendments when the code differs (committing conflict markers and opening
    the PR anyway if our internal tree has drifted since), or
  - deletes the stale source branch on the staging fork when only the commit
    message changed (Meta always adds Summary/Test Plan/trailers).

All interaction with facebook/fboss is READ-ONLY. Writes only touch repos we own:
the reconcile PR goes to origin (nexthop-ai/private-fboss); the branch to delete
is on the nexthop-ai remote (nexthop-ai/fboss).

Idempotency is stateless (no committed state file, no writes to upstream):
  - Each cycle is bounded to PRs closed since this workflow's last successful run
    (read from GitHub's own run history via `gh run list`), minus a 1-day overlap.
  - An existing reconcile PR in origin (matched by head branch, `--state all`,
    so it survives branch deletion and merge) is the durable "already handled"
    marker for the amend case.
  - Deleting an already-gone source branch is a no-op, so the clean case is
    inherently idempotent.

Usage:
    .github/scripts/reconcile-upstream-merges.py                 # scan recent
    .github/scripts/reconcile-upstream-merges.py --dry-run       # report only
    .github/scripts/reconcile-upstream-merges.py --pr 1153       # single PR
    .github/scripts/reconcile-upstream-merges.py --lookback-days 30
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Constants ──────────────────────────────────────────────────────────────

UPSTREAM_REPO = "facebook/fboss"
UPSTREAM_REMOTE = "upstream"
UPSTREAM_URL = f"https://github.com/{UPSTREAM_REPO}"

# Public staging fork: source branches of our upstream PRs live here.
STAGING_REPO = "nexthop-ai/fboss"
STAGING_REMOTE = "nexthop-ai"
STAGING_URL = f"https://github.com/{STAGING_REPO}"

# Our private fork: reconcile PRs are opened here. This is the repo the workflow
# runs in, so it is the `origin` remote of the checkout.
PRIVATE_REPO = "nexthop-ai/private-fboss"
PRIVATE_REMOTE = "origin"
PRIVATE_BASE = "main"

# Label applied by Meta automation to all our upstream PRs.
NEXTHOP_LABEL = "nexthop"
# Label applied by facebook-github-tools[bot] once a PR has actually landed.
MERGED_LABEL = "Merged"
# Actor that closes our PR and carries the landed SHA on the close event.
CODESYNC_BOT = "meta-codesync[bot]"

# Workflow file name, used to look up our own last successful run for the
# watermark. MUST match the actual workflow filename.
WORKFLOW_FILE = "reconcile-upstream-merges.yml"

# Never delete these branches even if they somehow show up as a PR head.
PROTECTED_BRANCHES = {"main", "master", "bazel-build", "benoit.blaze"}
PROTECTED_PREFIXES = ("sync-fboss-",)

RECONCILE_BRANCH_PREFIX = "reconcile/upstream-"

# Cap the range-diff embedded in the PR body so we don't post a wall of text.
MAX_RANGEDIFF_LINES = 300

# ─── Logging ──────────────────────────────────────────────────────────────────


def info(msg: str) -> None:
    print(f"💡 {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"⚠️  {msg}", flush=True)


def error(msg: str) -> None:
    print(f"💥 {msg}", file=sys.stderr, flush=True)


# ─── Subprocess helpers ─────────────────────────────────────────────────────


def run(cmd: list[str], *, check: bool = True, input: str | None = None,
        cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run a command, capturing stdout/stderr as text."""
    return subprocess.run(
        cmd, check=check, text=True, input=input,
        capture_output=True, cwd=cwd,
    )


def git(args: list[str], *, check: bool = True, cwd: str | None = None,
        input: str | None = None) -> subprocess.CompletedProcess:
    return run(["git", *args], check=check, cwd=cwd, input=input)


def gh_json(args: list[str]):
    """Run a `gh` command that emits JSON and parse it."""
    out = run(["gh", *args]).stdout.strip()
    return json.loads(out) if out else None


# ─── Remote setup ───────────────────────────────────────────────────────────


def ensure_remote(name: str, url: str) -> None:
    """Add the remote if missing, or fix its URL (mirrors sync_upstream.sh)."""
    existing = git(["remote"], check=False).stdout.split()
    if name in existing:
        git(["remote", "set-url", name, url], check=False)
    else:
        git(["remote", "add", name, url], check=False)


def setup_remotes() -> None:
    ensure_remote(UPSTREAM_REMOTE, UPSTREAM_URL)
    ensure_remote(STAGING_REMOTE, STAGING_URL)
    info(f"Fetching {UPSTREAM_REMOTE}/main and {PRIVATE_REMOTE}/{PRIVATE_BASE}")
    git(["fetch", UPSTREAM_REMOTE, "main"])
    git(["fetch", PRIVATE_REMOTE, PRIVATE_BASE])


# ─── Watermark ──────────────────────────────────────────────────────────────


def compute_lower_bound(lookback_days: int) -> datetime:
    """
    Lower bound for the candidate scan: the timestamp of this workflow's last
    successful run (minus a 1-day overlap), or `lookback_days` ago if there is
    no prior run / we can't read run history (e.g. local invocation).
    """
    try:
        runs = gh_json([
            "run", "list", "--workflow", WORKFLOW_FILE,
            "--status", "success", "--limit", "1", "--json", "createdAt",
        ])
        if runs:
            ts = datetime.fromisoformat(runs[0]["createdAt"].replace("Z", "+00:00"))
            lower = ts - timedelta(days=1)
            info(f"Watermark: last successful run {ts.isoformat()} "
                 f"→ scanning PRs closed since {lower.date()} (1-day overlap)")
            return lower
    except Exception as exc:  # noqa: BLE001 - any failure → safe fallback
        warn(f"Could not read run history ({exc}); falling back to lookback")

    lower = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    info(f"Watermark: no prior run → scanning PRs closed in the last "
         f"{lookback_days} days (since {lower.date()})")
    return lower


# ─── Candidate discovery ────────────────────────────────────────────────────

PR_FIELDS = "number,title,headRefName,headRefOid,labels,closedAt,author,state"


def label_names(pr: dict) -> set[str]:
    return {lbl["name"] for lbl in pr.get("labels", [])}


def find_candidates(lower_bound: datetime, single_pr: int | None) -> list[dict]:
    if single_pr is not None:
        pr = gh_json([
            "pr", "view", str(single_pr), "--repo", UPSTREAM_REPO,
            "--json", PR_FIELDS,
        ])
        return [pr] if pr else []

    since = lower_bound.strftime("%Y-%m-%dT%H:%M:%SZ")
    search = f"label:{NEXTHOP_LABEL} is:closed closed:>={since}"
    prs = gh_json([
        "pr", "list", "--repo", UPSTREAM_REPO, "--state", "closed",
        "--search", search, "--limit", "200", "--json", PR_FIELDS,
    ])
    return prs or []


# ─── Landed-SHA resolution ──────────────────────────────────────────────────


def resolve_landed_sha(pr_number: int) -> str | None:
    """
    Find the commit that landed for upstream PR <pr_number>.

    Primary (no API): Meta's landed commit body ends with
        Pull Request resolved: https://github.com/facebook/fboss/pull/<N>
    so we grep upstream/main locally.

    Fallback (API): the `closed` timeline event whose actor is meta-codesync[bot]
    carries `commit_id` == the landed SHA.
    """
    pattern = rf"Pull Request resolved: .*pull/{pr_number}$"
    out = git(
        ["log", f"{UPSTREAM_REMOTE}/main", "-E", f"--grep={pattern}",
         "--format=%H", "-n", "1"],
        check=False,
    ).stdout.strip()
    if out:
        return out.splitlines()[0]

    warn(f"PR #{pr_number}: no 'Pull Request resolved' trailer on "
         f"{UPSTREAM_REMOTE}/main; falling back to timeline API")
    try:
        timeline = gh_json([
            "api", f"repos/{UPSTREAM_REPO}/issues/{pr_number}/timeline",
            "--paginate",
        ]) or []
        for ev in timeline:
            if ev.get("event") == "closed" and \
                    (ev.get("actor") or {}).get("login") == CODESYNC_BOT:
                if ev.get("commit_id"):
                    return ev["commit_id"]
    except Exception as exc:  # noqa: BLE001
        warn(f"PR #{pr_number}: timeline lookup failed: {exc}")
    return None


# ─── Idempotency ────────────────────────────────────────────────────────────


def existing_reconcile_pr(pr_number: int) -> dict | None:
    """Durable 'already handled' check: a reconcile PR (any state) in origin."""
    branch = f"{RECONCILE_BRANCH_PREFIX}{pr_number}"
    prs = gh_json([
        "pr", "list", "--repo", PRIVATE_REPO, "--state", "all",
        "--head", branch, "--json", "number,url,state",
    ])
    return prs[0] if prs else None


# ─── Diff comparison ────────────────────────────────────────────────────────


def patch_id(diff_text: str) -> str:
    """Stable patch-id of a diff (empty string for an empty diff)."""
    if not diff_text.strip():
        return ""
    out = git(["patch-id", "--stable"], input=diff_text, check=False).stdout.strip()
    return out.split()[0] if out else ""


def changed_files(rev_range: str) -> list[str]:
    out = git(["diff", "--name-only", rev_range]).stdout
    return [line for line in out.splitlines() if line.strip()]


# ─── Branch deletion (clean case) ───────────────────────────────────────────


def branch_exists_on_staging(branch: str) -> bool:
    out = git(["ls-remote", "--heads", STAGING_REMOTE, branch], check=False).stdout
    return bool(out.strip())


def is_protected(branch: str) -> bool:
    return branch in PROTECTED_BRANCHES or \
        any(branch.startswith(p) for p in PROTECTED_PREFIXES)


def delete_staging_branch(branch: str, dry_run: bool) -> str:
    if is_protected(branch):
        warn(f"Refusing to delete protected branch '{branch}'")
        return "skipped-protected"
    if not branch_exists_on_staging(branch):
        info(f"Source branch '{branch}' already gone on {STAGING_REPO} (no-op)")
        return "already-gone"
    if dry_run:
        info(f"[dry-run] Would delete {STAGING_REPO} branch '{branch}'")
        return "would-delete"
    # gh api uses GH_TOKEN auth; no need for an authenticated git push remote.
    run(["gh", "api", "--method", "DELETE",
         f"repos/{STAGING_REPO}/git/refs/heads/{branch}"])
    info(f"🧹 Deleted stale source branch '{branch}' on {STAGING_REPO}")
    return "deleted"


# ─── Reconcile PR (amend case) ──────────────────────────────────────────────


def build_range_diff(base: str, head: str, landed: str) -> str:
    out = git(["range-diff", f"{base}..{head}", f"{landed}^..{landed}"],
              check=False).stdout
    lines = out.splitlines()
    if len(lines) > MAX_RANGEDIFF_LINES:
        lines = lines[:MAX_RANGEDIFF_LINES]
        lines.append(f"... (truncated at {MAX_RANGEDIFF_LINES} lines)")
    return "\n".join(lines)


def apply_amendment(worktree: str, head: str, landed: str,
                    files: list[str]) -> tuple[bool, list[str]]:
    """
    In `worktree` (checked out at origin/main on the reconcile branch), apply the
    delta `git diff <head> <landed> -- <files>` via 3-way merge.

    Because the diff's "old" side is our submitted version, the 3-way base is our
    code: upstream drift already present on origin/main merges cleanly, and only
    Meta's genuine amendments remain — with native conflict markers wherever our
    internal tree has diverged.

    Returns (clean, conflicted_files).
    """
    delta = git(["diff", head, landed, "--", *files]).stdout
    patch_path = os.path.join(worktree, ".reconcile-amend.patch")
    with open(patch_path, "w") as fh:
        fh.write(delta)

    applied = git(["apply", "--3way", "--index", patch_path],
                  check=False, cwd=worktree)
    os.unlink(patch_path)

    # Stage everything, including any files left with conflict markers.
    git(["add", "-A"], cwd=worktree)

    # Key on the unambiguous conflict-start marker ("<<<<<<< <label>") to avoid
    # false positives from "=======" dividers that appear in normal source.
    conflicted = sorted({
        line for line in git(
            ["grep", "--cached", "-l", "-E", r"^<{7} "],
            check=False, cwd=worktree,
        ).stdout.splitlines() if line.strip()
    })

    clean = applied.returncode == 0 and not conflicted
    return clean, conflicted


def assign_reviewer(pr_url: str, login: str) -> None:
    """Request the original author as reviewer; fall back to assignee."""
    if not login:
        return
    r = run(["gh", "pr", "edit", pr_url, "--add-reviewer", login], check=False)
    if r.returncode == 0:
        info(f"Requested review from @{login}")
        return
    warn(f"Could not add @{login} as reviewer ({r.stderr.strip()}); "
         f"trying assignee")
    r = run(["gh", "pr", "edit", pr_url, "--add-assignee", login], check=False)
    if r.returncode == 0:
        info(f"Assigned @{login}")
    else:
        warn(f"Could not assign @{login} either; leaving unassigned")


def create_reconcile_pr(pr: dict, base: str, head: str, landed: str,
                        files: list[str], dry_run: bool) -> str:
    number = pr["number"]
    branch = f"{RECONCILE_BRANCH_PREFIX}{number}"
    author = (pr.get("author") or {}).get("login", "")
    range_diff = build_range_diff(base, head, landed)

    worktree = tempfile.mkdtemp(prefix="reconcile-wt-")
    try:
        # Isolated worktree so we never disturb the caller's checkout.
        git(["worktree", "add", "-f", "-B", branch, worktree,
             f"{PRIVATE_REMOTE}/{PRIVATE_BASE}"])
        clean, conflicted = apply_amendment(worktree, head, landed, files)

        if git(["diff", "--cached", "--quiet"], check=False, cwd=worktree).returncode == 0:
            # Nothing to reconcile against origin/main (drift already synced and
            # no genuine amendment). Treat as clean.
            info(f"PR #{number}: amendments already present on "
                 f"{PRIVATE_REMOTE}/{PRIVATE_BASE}; nothing to reconcile")
            return "no-net-change"

        needs_resolution = bool(conflicted)
        flag = "[reconcile][needs-resolution]" if needs_resolution else "[reconcile]"
        title = f"{flag} Meta amendments to upstream #{number}: {pr['title']}"

        body_lines = [
            f"Meta amended this change before landing [upstream "
            f"PR #{number}](https://github.com/{UPSTREAM_REPO}/pull/{number}).",
            "",
            f"This PR carries those amendments back into `{PRIVATE_REPO}` so our "
            f"internal tree matches what actually shipped.",
            "",
            f"- Upstream PR: https://github.com/{UPSTREAM_REPO}/pull/{number}",
            f"- Landed commit: https://github.com/{UPSTREAM_REPO}/commit/{landed}",
            "",
        ]
        if needs_resolution:
            body_lines += [
                "### ⚠️ Manual conflict resolution required",
                "",
                "Our internal tree has drifted since we submitted upstream, so "
                "some of Meta's amendments could not be applied automatically. "
                "The following files contain conflict markers — check out this "
                "branch, resolve them, push, and land:",
                "",
                *[f"- [ ] `{f}`" for f in conflicted],
                "",
            ]
        body_lines += [
            "<details><summary>range-diff (submitted → landed)</summary>",
            "",
            "```",
            range_diff,
            "```",
            "</details>",
            "",
            "NHCI: clang-tidy=warn-only",
        ]
        body = "\n".join(body_lines)

        commit_msg = (
            f"{flag} Reconcile Meta amendments to upstream #{number}\n\n"
            f"{pr['title']}\n\n"
            f"Upstream PR: https://github.com/{UPSTREAM_REPO}/pull/{number}\n"
            f"Landed commit: {landed}\n"
        )
        if author:
            commit_msg += f"Original author: @{author}\n"

        if dry_run:
            verdict = "WITH CONFLICTS" if needs_resolution else "cleanly"
            info(f"[dry-run] Would open reconcile PR '{title}' ({verdict})")
            if conflicted:
                info(f"[dry-run] Conflicted files: {', '.join(conflicted)}")
            return "would-reconcile-conflict" if needs_resolution else "would-reconcile"

        git(["commit", "--no-verify", "-m", commit_msg], cwd=worktree)
        git(["push", "--force-with-lease", "--set-upstream",
             PRIVATE_REMOTE, branch], cwd=worktree)

        create_cmd = [
            "gh", "pr", "create", "--repo", PRIVATE_REPO,
            "--base", PRIVATE_BASE, "--head", branch,
            "--title", title, "--body", body,
        ]
        if needs_resolution:
            create_cmd.append("--draft")
        pr_url = run(create_cmd).stdout.strip()
        info(f"📬 Opened reconcile PR: {pr_url}")
        assign_reviewer(pr_url, author)
        return "reconciled-conflict" if needs_resolution else "reconciled"
    finally:
        git(["worktree", "remove", "--force", worktree], check=False)
        shutil.rmtree(worktree, ignore_errors=True)
        # Drop the local branch ref the worktree created; the pushed copy (if
        # any) on origin is what matters.
        git(["branch", "-D", branch], check=False)


# ─── Per-PR processing ──────────────────────────────────────────────────────


def fetch_objects(pr: dict, landed: str) -> bool:
    """Fetch the PR head (staging fork) and landed commit. Returns success."""
    head_oid = pr["headRefOid"]
    head_ref = pr["headRefName"]
    # Prefer fetching by branch name (reliable); fall back to the raw SHA.
    if git(["fetch", STAGING_REMOTE, head_ref], check=False).returncode != 0:
        if git(["fetch", STAGING_REMOTE, head_oid], check=False).returncode != 0:
            warn(f"PR #{pr['number']}: could not fetch head {head_oid[:10]} "
                 f"from {STAGING_REPO}")
            return False
    # landed is on upstream/main, already fetched, but be explicit for safety.
    git(["fetch", UPSTREAM_REMOTE, landed], check=False)
    return True


def clean_outcome(pr: dict, dry_run: bool) -> str:
    """Nothing to reconcile: leave any existing reconcile PR alone, else delete
    the stale source branch on the staging fork."""
    existing = existing_reconcile_pr(pr["number"])
    if existing:
        info(f"PR #{pr['number']}: reconcile PR already exists "
             f"({existing['url']}, {existing['state']}); leaving source branch")
        return "skip-have-reconcile"
    return delete_staging_branch(pr["headRefName"], dry_run)


def process_pr(pr: dict, dry_run: bool) -> str:
    number = pr["number"]
    title = pr["title"]
    labels = label_names(pr)
    info(f"── PR #{number}: {title}")

    if pr.get("state") != "CLOSED":
        info(f"PR #{number}: not closed ({pr.get('state')}); skipping")
        return "skip-open"
    if MERGED_LABEL not in labels:
        info(f"PR #{number}: no '{MERGED_LABEL}' label "
             f"(human-closed / abandoned); skipping")
        return "skip-unmerged"

    landed = resolve_landed_sha(number)
    if not landed:
        warn(f"PR #{number}: could not resolve landed SHA; skipping")
        return "skip-no-sha"
    info(f"PR #{number}: landed as {landed[:12]}")

    if not fetch_objects(pr, landed):
        return "skip-fetch-failed"

    # If the periodic upstream sync has already merged the landed commit into
    # origin/main, the change (amendments and all) is fully integrated — no PR
    # to open, just tidy up the stale source branch.
    if git(["merge-base", "--is-ancestor", landed,
            f"{PRIVATE_REMOTE}/{PRIVATE_BASE}"], check=False).returncode == 0:
        info(f"PR #{number}: landed commit already integrated via sync")
        return clean_outcome(pr, dry_run)

    head = pr["headRefOid"]
    base = git(["merge-base", head, landed]).stdout.strip()

    ours = git(["diff", base, head]).stdout
    theirs = git(["diff", f"{landed}^", landed]).stdout

    if patch_id(ours) == patch_id(theirs):
        # Identical hunks → only the commit message changed (Summary/Test
        # Plan/trailers). Clean: delete the stale source branch.
        info(f"PR #{number}: code identical (message-only land)")
        return clean_outcome(pr, dry_run)

    # Code differs. Already reconciled?
    existing = existing_reconcile_pr(number)
    if existing:
        info(f"PR #{number}: reconcile PR already exists "
             f"({existing['url']}, {existing['state']}); skipping")
        return "skip-have-reconcile"

    files = sorted(set(changed_files(f"{base}..{head}")) |
                   set(changed_files(f"{landed}^..{landed}")))
    info(f"PR #{number}: code amended by Meta; "
         f"building reconcile across {len(files)} file(s)")
    return create_reconcile_pr(pr, base, head, landed, files, dry_run)


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report actions without making any changes")
    parser.add_argument("--pr", type=int, default=None,
                        help="Process a single upstream PR number (skips watermark)")
    parser.add_argument("--lookback-days", type=int, default=30,
                        help="Fallback window when there is no prior run (default 30)")
    args = parser.parse_args()

    setup_remotes()

    lower_bound = (datetime.now(timezone.utc) - timedelta(days=args.lookback_days)
                   if args.pr is not None
                   else compute_lower_bound(args.lookback_days))
    candidates = find_candidates(lower_bound, args.pr)
    info(f"Found {len(candidates)} candidate PR(s)")

    summary: dict[str, list[int]] = {}
    for pr in candidates:
        try:
            outcome = process_pr(pr, args.dry_run)
        except subprocess.CalledProcessError as exc:
            error(f"PR #{pr.get('number')}: command failed: "
                  f"{exc.cmd}\n{exc.stderr}")
            outcome = "error"
        except Exception as exc:  # noqa: BLE001
            error(f"PR #{pr.get('number')}: {exc}")
            outcome = "error"
        summary.setdefault(outcome, []).append(pr.get("number"))

    info("── Summary")
    for outcome, numbers in sorted(summary.items()):
        nums = ", ".join(f"#{n}" for n in numbers)
        info(f"  {outcome}: {len(numbers)} ({nums})")

    # Surface failures as a nonzero exit so the workflow run is marked failed
    # (and the watermark for the next cycle stays put).
    return 1 if summary.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
