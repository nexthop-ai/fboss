#!/usr/bin/env python3
"""Stack-aware rebase of upstream facebook/fboss PRs (nexthop-ai/fboss branches).

Rebase a stale upstream PR — or the whole stack it belongs to — onto a target
commit (default: the latest stable commit) using our auto conflict resolver,
so we can build-and-test it before the FBOSS team reviews it. Designed to run
in GitHub Actions from the rebase-upstream-pr.yml workflow, but the happy path
is also runnable locally for debugging.

Subcommands (one per workflow job):

  rebase <pr> [--onto REF] [--resume-from-wip BOOL] [--dry-run BOOL]
      Discover and verify the PR's stack, then chain-rebase it root -> top.
      Any member PR is an equivalent handle to the whole stack. --onto always
      applies to the stack root (empty = latest stable commit; a branch name
      or SHA = that upstream commit). --dry-run stops after discovery +
      verification and reports the per-level plan without touching anything.
      --resume-from-wip adopts the -rebase-wip branches staged by a previous
      run (manually resolved conflicts included) instead of rebasing from the
      PR heads.

  push
      Force-push the validated rebase to every moved PR branch (env: LEVELS,
      TEST_BRANCH). A leased --dry-run pass over all branches runs first, so
      the update is all-or-nothing: if any PR branch moved since the rebase
      started, nothing is pushed.

  heal
      Best-effort re-alignment of the stack declarations in the member PRs'
      bodies (env: LEVELS): the '> **Stack (bottom → top):** ...' header line
      and '> **Stacked on #N**' line are refreshed when present, and the
      'Based-on:' trailer is rewritten (children: facebook/fboss#<parent>,
      root: "main") or appended. Failures (e.g. the token cannot edit another
      author's PR) are warnings, never errors.

  notify {success,conflicts,build-failure,dropped-commits}
      Build and post the Slack message for one workflow outcome (inputs via
      env; see the notify jobs in rebase-upstream-pr.yml). 'success' DMs the
      author when SLACK_BOT_TOKEN is set (internal usernames map to
      @nexthop.ai emails), falling back to the channel webhook; the @mabel
      handoffs always go to the channel webhook.

Stack discovery: each PR body declares its parent via a 'Stacked on #N' line
(preferred) or a 'Based-on: facebook/fboss#N' trailer. Declarations are only
trusted for membership and order; every link is verified against git ancestry
and classified intact / pending-restack (parent moved since the child was
stacked), with hard failures on cycles, inverted links, and tree-shaped
stacks. A declared parent that is no longer an open PR makes its child the
root, and its fate is classified: upstream merges don't use GitHub's merge
state — Meta's import CLOSES the PR and a bot comments "merged this pull
request in facebook/fboss@<sha>" — so the landed sha is extracted from that
comment and checked for containment in the rebase target (the carried copies
are then absorbed by the root's rebase, an expected commit drop). A parent
closed WITHOUT a merge signal gets a loud warning.

Stack mechanics: the root is rebased onto the target; every child replays
only its own commits onto its parent's new tip
(git rebase --onto <parent_new_tip> <merge-base(parent_old, child)>), so the
parent prefix stays SHA-identical across all branches. Levels already in
place are no-ops that keep their SHAs (no force-push, no CI churn). Each
cleanly rebased level is staged to its <branch>-rebase-wip on the fork
immediately, so a conflict, build failure, or crash never loses work. A
per-stack lock ref (refs/rebase-locks/pr<root> on the fork) stops concurrent
rebases of the same stack dispatched via different member PRs; the workflow's
cleanup job releases it.

Requires GH_TOKEN with read access to facebook/fboss and push access to
nexthop-ai/fboss (the public fork, used for fetching the PR branches and for
the wip/lock refs). The clean rebase gets our NH CI harness overlaid on top
of the stack top (via sync-lib.sh, shared with the sync workflows) and is
pushed straight to a convention-compliant branch on this checkout
(private-fboss) — build-and-test never touches the public fork. Outputs are
written to $GITHUB_OUTPUT when set; the per-level result is the `levels`
output, a JSON array ({pr, branch, old_head, new_tip, noop, link,
orig_commits, new_commits}) ordered bottom -> top. A plain PR is a stack of
size 1. `cli_changed` reports whether the stack's own diff on the target
touches the fboss2 CLI (or its test plumbing); the workflow gates the
informational fboss-sim and DUT CLI suites on it, mirroring the path filters
the internal PR flow applies (fboss-sim-cli.yml, integration_test.yml).

The REBASE_UPSTREAM_REPO / REBASE_FORK_REPO / REBASE_UPSTREAM_URL /
REBASE_FORK_URL environment overrides exist for the test suite, which points
them at local bare repositories.
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
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

UPSTREAM_REPO = os.environ.get("REBASE_UPSTREAM_REPO", "facebook/fboss")
FORK_REPO = os.environ.get("REBASE_FORK_REPO", "nexthop-ai/fboss")
FORK_OWNER = FORK_REPO.split("/", 1)[0]
FORK_REMOTE = "nexthop-ai"
UPSTREAM_BASE_BRANCH = "main"
# Branch to source the NH harness files from. The checkout action leaves no
# origin/* remote-tracking refs and a detached HEAD, so use $GITHUB_REF_NAME.
NH_REPO_BRANCH = os.environ.get("GITHUB_REF_NAME") or "main"

MERGE_COMMENT_RE = re.compile(r"merged this pull request in \S+@([0-9a-f]{40})")
STACKED_ON_RE = re.compile(r"stacked on #(\d+)", re.IGNORECASE)
# Paths whose change means the fboss2 CLI integration suites (fboss-sim + DUT)
# are worth running on a rebase: the CLI itself, its cmake lists, and the
# run_scripts overlaid onto the DUT. Same set the internal PR flow gates on
# (fboss-sim-cli.yml's dorny filter, integration_test.yml's detect step); the
# .github/ plumbing entries from the latter are omitted because the rebased
# tree is an upstream tree, whose .github/ is Meta's, not ours.
CLI_TEST_PATH_RE = re.compile(r"^(fboss/cli/|cmake/CliFboss2[^/]*\.cmake$|fboss/oss/scripts/run_scripts/)")
REBASE_ITERATION_CAP = 200


def info(msg: str) -> None:
    print(f"💡 INFO:  {msg}", flush=True)


def error(msg: str) -> None:
    print(f"❌ ERROR: {msg}", file=sys.stderr, flush=True)


def fail(msg: str) -> None:
    error(msg)
    sys.exit(1)


def run(
    cmd: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command, streaming output unless capture=True."""
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        env={**os.environ, **env} if env else None,
        capture_output=capture,
        input=stdin,
    )


def git_out(*args: str) -> str:
    return run(["git", *args], capture=True).stdout.strip()


def git_ok(*args: str) -> bool:
    return run(["git", *args], check=False, capture=True).returncode == 0


def git_run(*args: str, check: bool = True) -> int:
    return run(["git", *args], check=check).returncode


def gh_json(args: list[str]):
    return json.loads(run(["gh", *args], capture=True).stdout)


_sync_lib_snapshot: Path | None = None


def sync_lib(fn: str, *args: str, capture: bool = False) -> str:
    """Call one function from sync-lib.sh (shared with the sync workflows).

    Sourced from a startup snapshot outside the checkout: the chain rebase
    switches the working tree to the upstream stack's content, which doesn't
    carry .github/scripts, so the in-tree copy is gone by the time
    overlay_nh_harness runs (its file inputs come from git refs, not the tree).
    """
    global _sync_lib_snapshot
    if _sync_lib_snapshot is None:
        fd, name = tempfile.mkstemp(prefix="sync-lib.", suffix=".sh")
        os.close(fd)
        _sync_lib_snapshot = Path(shutil.copy2(SCRIPT_DIR / "sync-lib.sh", name))
    cmd = ["bash", "-c", f'source "{_sync_lib_snapshot}" && "$@"', "--", fn, *args]
    result = run(cmd, capture=capture)
    return result.stdout.strip() if capture else ""


def emit(key: str, value) -> None:
    """Write a workflow output (no-op when run locally)."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    text = "true" if value is True else "false" if value is False else str(value)
    with open(path, "a", encoding="utf-8") as f:
        if "\n" in text:
            f.write(f"{key}<<GITHUB_OUTPUT_EOF\n{text}\nGITHUB_OUTPUT_EOF\n")
        else:
            f.write(f"{key}={text}\n")


def step_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(markdown + "\n")


# ─── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Level:
    """One PR of the stack, bottom -> top order."""

    pr: int
    branch: str
    old_head: str = ""  # fetched head OID; also the force-with-lease pin
    boundary: str = ""  # rebase boundary: everything above it replays
    link: str = ""  # root | intact | pending-restack
    new_tip: str = ""
    noop: bool = False  # already in place: SHAs kept, nothing pushed
    orig_commits: int = 0
    new_commits: int = 0
    from_wip: bool = False  # this run's input came from the level's own wip

    @property
    def wip(self) -> str:
        return f"{self.branch}-rebase-wip"


@dataclass
class MergedParent:
    """The declared parent below the stack root that is no longer an open PR."""

    pr: int
    state: str  # merged | closed | open | missing
    sha: str = ""  # landed commit for state == merged (when discoverable)
    absorbed: str = ""  # "true"/"false": target already contains sha


def levels_json(levels: list[Level]) -> str:
    keys = ("pr", "branch", "old_head", "new_tip", "noop", "link", "orig_commits", "new_commits")
    return json.dumps(
        [{k: v for k, v in asdict(lvl).items() if k in keys} for lvl in levels],
        separators=(",", ":"),
    )


# ─── Discovery ─────────────────────────────────────────────────────────────────


def declared_parent(body: str) -> int | None:
    """The parent PR a body declares, or None for a root.

    'Stacked on #N' (the prose header blockquote) wins over the
    'Based-on: facebook/fboss#N' trailer — trailers go stale. Bodies come from
    the GitHub API with CRLF line endings; strip the CRs first.
    """
    body = body.replace("\r", "")
    m = STACKED_ON_RE.search(body)
    if m:
        return int(m.group(1))
    for line in body.splitlines():
        if line.lower().startswith("based-on:"):
            m = re.search(r"#(\d+)", line)
            return int(m.group(1)) if m else None
    return None


def open_fork_prs() -> dict[int, dict]:
    """Every open upstream PR whose head branch lives on our fork.

    GitHub has no server-side filter for the head-fork owner (search only
    supports author:/base:/head:<branch-name>, and REST's ?head= needs a
    specific owner:branch), so enumerate ALL open PRs with full pagination
    and filter client-side — a fixed --limit would silently drop stack
    members once the upstream open-PR count outgrows it, and a missing top
    member would rebase the stack out from under its children.
    """
    out = run(
        ["gh", "api", "--paginate", f"repos/{UPSTREAM_REPO}/pulls?state=open&per_page=100"],
        capture=True,
    ).stdout
    # --paginate concatenates one JSON array per page; decode them in sequence.
    decoder = json.JSONDecoder()
    prs: list[dict] = []
    idx = 0
    while idx < len(out):
        while idx < len(out) and out[idx].isspace():
            idx += 1
        if idx >= len(out):
            break
        page, idx = decoder.raw_decode(out, idx)
        prs.extend(page)
    return {
        p["number"]: {"headRefName": p["head"]["ref"], "body": p.get("body") or ""}
        for p in prs
        if ((p.get("head") or {}).get("repo") or {}).get("owner", {}).get("login") == FORK_OWNER
    }


def classify_closed_parent(pr: int) -> MergedParent:
    """Classify a declared parent that is not an open fork-headed PR.

    Upstream merges of our PRs do not use GitHub's merge state: Meta's import
    CLOSES the PR (mergedAt stays null) and a bot comments
    "... merged this pull request in facebook/fboss@<sha>."
    """
    result = run(
        ["gh", "pr", "view", str(pr), "--repo", UPSTREAM_REPO, "--json", "state,mergeCommit,comments"],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        return MergedParent(pr, "missing")
    data = json.loads(result.stdout)
    if data["state"] == "MERGED":
        return MergedParent(pr, "merged", (data.get("mergeCommit") or {}).get("oid", ""))
    if data["state"] != "CLOSED":
        return MergedParent(pr, "open")
    for comment in data.get("comments") or []:
        m = MERGE_COMMENT_RE.search(comment.get("body", ""))
        if m:
            return MergedParent(pr, "merged", m.group(1))
    return MergedParent(pr, "closed")


def discover_stack(seed: int) -> tuple[list[Level], MergedParent | None]:
    """Build the stack containing <seed> from the PR-body declarations.

    Walks down to the root, then up child by child, so any member is an
    equivalent handle to the whole stack. Returns the levels bottom -> top
    (heads freshly fetched) plus the classified below-root parent, if any.
    """
    info(f"Discovering the stack around PR #{seed}")
    by_pr = open_fork_prs()
    parents = {n: declared_parent(c["body"]) for n, c in by_pr.items()}

    if seed not in by_pr:
        fail(f"PR #{seed} is not an open {UPSTREAM_REPO} PR with its branch on {FORK_REPO}.")

    # Walk down to the root (cycle-guarded). A declared parent that is not an
    # open candidate ends the walk: this PR is the root, and the parent's fate
    # (merged vs abandoned) is recorded for verification and the reports.
    below_root: MergedParent | None = None
    chain = [seed]
    seen = {seed}
    while True:
        parent = parents[chain[0]]
        if parent is None:
            break
        if parent not in by_pr:
            below_root = classify_closed_parent(parent)
            cur = chain[0]
            if below_root.state == "merged":
                info(
                    f"#{cur}'s declared parent #{parent} was merged upstream "
                    f"({UPSTREAM_REPO}@{below_root.sha or 'unknown'}); #{cur} is the stack root "
                    "and the merged commits it carries are absorbed once the target contains them."
                )
            elif below_root.state == "closed":
                error(
                    f"WARNING: #{cur}'s declared parent #{parent} is closed WITHOUT a merge signal "
                    f"— #{cur} still carries its commits. Restack it or fix the declaration; "
                    f"proceeding with #{cur} as the stack root."
                )
            else:
                error(
                    f"WARNING: #{cur}'s declared parent #{parent} is '{below_root.state}' "
                    f"(not an open fork-headed PR); treating #{cur} as the stack root."
                )
            break
        if parent in seen:
            fail(f"Cycle in the declared stack at #{parent}; fix the Stacked on / Based-on declarations.")
        seen.add(parent)
        chain.insert(0, parent)

    # Walk up: the child is the candidate that declares the current top as parent.
    while True:
        kids = [n for n, p in parents.items() if p == chain[-1]]
        if not kids:
            break
        if len(kids) > 1:
            fail(
                f"PR #{chain[-1]} has multiple stacked children ({', '.join(f'#{k}' for k in sorted(kids))}); "
                "tree-shaped stacks are not supported — restack the sub-chains into one chain first."
            )
        if kids[0] in seen:
            fail(f"Cycle in the declared stack at #{kids[0]}; fix the Stacked on / Based-on declarations.")
        seen.add(kids[0])
        chain.append(kids[0])

    levels = [Level(pr=n, branch=by_pr[n]["headRefName"]) for n in chain]

    # One fetch for every member head. Use the fetched OIDs (not the listing,
    # which may be stale) for both the rebase math and the force-with-lease pins.
    refspecs = [f"+refs/heads/{lvl.branch}:refs/stack/{lvl.branch}" for lvl in levels]
    git_run("fetch", "--no-tags", FORK_REMOTE, *refspecs)
    for lvl in levels:
        lvl.old_head = git_out("rev-parse", f"refs/stack/{lvl.branch}")

    info("Stack (bottom -> top): " + " ".join(f"#{lvl.pr}" for lvl in levels))
    return levels, below_root


# ─── Verification ──────────────────────────────────────────────────────────────


def verify_stack(levels: list[Level], target: str, below_root: MergedParent | None) -> None:
    """Verify every declared link against git ancestry and set the boundaries.

    intact:          the child head contains the parent head (exact stacking).
    pending-restack: the parent moved since the child was stacked (review
                     fixes, an earlier partial rebase). The child's own
                     commits are boundary..head; replaying them onto the
                     parent's new tip restacks it, and patch-identical copies
                     of parent commits inside the range are dropped by git
                     rebase itself.
    A child fully contained in its parent is an inverted link: hard failure.
    """
    for i, lvl in enumerate(levels):
        if i == 0:
            lvl.boundary = git_out("merge-base", target, lvl.old_head)
            lvl.link = "root"
            continue
        parent_head = levels[i - 1].old_head
        lvl.boundary = git_out("merge-base", parent_head, lvl.old_head)
        if lvl.boundary == parent_head:
            lvl.link = "intact"
        elif lvl.boundary == lvl.old_head:
            fail(
                f"#{lvl.pr} ({lvl.branch}) is fully contained in its declared parent "
                f"#{levels[i - 1].pr} — inverted stack link; fix the branches or the "
                "declarations, then re-run."
            )
        else:
            lvl.link = "pending-restack"

    # A merged-away parent below the root: is its landed commit already in the
    # target? If so the root's rebase drops the carried copies (expected); if
    # not (target predates the merge) they stay carried — also fine, just noted.
    if below_root and below_root.state == "merged" and below_root.sha:
        present = git_ok("rev-parse", "-q", "--verify", f"{below_root.sha}^{{commit}}") or git_ok(
            "fetch", "--no-tags", "upstream", below_root.sha
        )
        if present and git_ok("merge-base", "--is-ancestor", below_root.sha, target):
            below_root.absorbed = "true"
            info(
                f"Target contains merged parent #{below_root.pr} ({below_root.sha}): "
                "its commits will be absorbed by the root's rebase."
            )
        else:
            below_root.absorbed = "false"
            info(
                f"Target does NOT contain merged parent #{below_root.pr} ({below_root.sha}) yet: "
                "the root keeps carrying its commits until the target catches up."
            )


def print_stack_plan(levels: list[Level], target: str, below_root: MergedParent | None) -> None:
    """Log the per-level plan and, under Actions, write it to the step summary.

    Predicts which levels will move: the root moves unless it already sits on
    the target; a child moves iff its parent moves or it is not exactly on the
    parent's tip.
    """
    rows = ["| Level | PR | Branch | Link | Plan |", "|---|---|---|---|---|"]
    if below_root:
        ctx = f"below the root: #{below_root.pr} ({below_root.state}"
        if below_root.state == "merged":
            ctx += f" as {below_root.sha or 'unknown'}, absorbed by target: {below_root.absorbed or 'unknown'}"
        ctx += ")"
        info(ctx)
        rows.insert(0, f"*{ctx}*\n")
    moved = False
    for i, lvl in enumerate(levels):
        onto = target if i == 0 else levels[i - 1].old_head
        own = int(git_out("rev-list", "--count", f"{lvl.boundary}..{lvl.old_head}"))
        if not moved and lvl.boundary == onto:
            action = "no-op (already in place)"
        else:
            action = f"rebase {own} own commit(s)"
            moved = True
        info(f"level {i}: #{lvl.pr} ({lvl.branch}) [{lvl.link}] -> {action}")
        rows.append(f"| {i} | #{lvl.pr} | {lvl.branch} | {lvl.link} | {action} |")
    step_summary(f"## Stack rebase plan (target: `{target}`)\n\n" + "\n".join(rows))


# ─── The chain rebase ──────────────────────────────────────────────────────────


def rebase_in_progress() -> bool:
    for kind in ("rebase-merge", "rebase-apply"):
        if Path(git_out("rev-parse", "--git-path", kind)).is_dir():
            return True
    return False


def fork_ref_exists(ref: str) -> bool:
    """True if <ref> exists on the fork, False only when it is genuinely
    absent (ls-remote --exit-code exits 2). Any other failure is fatal:
    conflating a transport error with absence sends callers down the wrong
    path — a resume would redo the rebase from the PR head and, on
    re-conflict, force-push over a human's manual fix on the wip; the lock
    check would misreport a live lock as stale."""
    rc = run(["git", "ls-remote", "--exit-code", FORK_REMOTE, ref], check=False, capture=True).returncode
    if rc == 0:
        return True
    if rc == 2:
        return False
    fail(f"'git ls-remote {FORK_REMOTE} {ref}' failed (exit {rc}) — cannot tell absence from a transport error.")
    return False  # unreachable; fail() exits


def conflict_marker_files() -> str:
    result = run(["git", "grep", "-lI", "^<<<<<<< ", "--", "."], check=False, capture=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def rebase_level_with_resolver(onto: str, boundary: str, head: str) -> tuple[str, bool]:
    """Replay boundary..head onto <onto>, driving the auto conflict resolver
    over every stop. Returns (tip, has_conflicts); on conflicts the working
    tree still carries the markers so the caller can push a best-effort wip.
    """
    git_run("checkout", "-q", "-B", "rebase-tmp", head)
    rc = run(["git", "rebase", "--onto", onto, boundary], check=False).returncode
    if rc != 0 and not rebase_in_progress():
        # The rebase failed without even starting (bad ref, unclean tree, ...):
        # nothing was replayed and there is nothing to resolve, so this is a
        # hard error — flowing on would return the ORIGINAL head as if the
        # rebase had succeeded cleanly.
        fail(f"'git rebase --onto {onto} {boundary}' failed without starting a rebase.")

    has_conflicts = False
    iterations = 0
    while rc != 0 and rebase_in_progress():
        iterations += 1
        if iterations > REBASE_ITERATION_CAP:
            # A runaway resolver loop, not a conflict: after the abort the
            # tree is pristine, so a conflict handoff would push a branch
            # with nothing on it to resolve.
            run(["git", "rebase", "--abort"], check=False)
            fail(f"Rebase did not converge after {iterations} steps; aborted.")

        sync_lib("run_conflict_resolver", NH_REPO_BRANCH)

        if git_out("diff", "--name-only", "--diff-filter=U"):
            # The resolver couldn't fully resolve this step. Stage everything
            # (markers included) so we can carry the rebase forward and hand a
            # best-effort branch off to a human; flag it so build-test is skipped.
            has_conflicts = True
            git_run("add", "-A")

        rc = run(["git", "rebase", "--continue"], check=False, env={"GIT_EDITOR": "true"}).returncode
        if rc != 0 and rebase_in_progress():
            # "continue" can fail when the resolved patch is now empty; skip it.
            rc = run(["git", "rebase", "--skip"], check=False, env={"GIT_EDITOR": "true"}).returncode
        if rc != 0 and not rebase_in_progress():
            # continue/skip failed AND tore down the rebase instead of
            # stopping at the next conflict: HEAD is a partially replayed
            # state that must not be returned as the rebased tip (only the
            # advisory dropped-commits warning would notice the truncation).
            fail("'git rebase --continue/--skip' failed and left no rebase in progress.")

    if rebase_in_progress():
        # Should be unreachable (the loop only exits with the rebase finished
        # or the cap hit above). Aborting restores the pristine pre-rebase
        # tree, so this must NOT be reported as a conflict — the handoff
        # would push a branch with no conflicts on it.
        run(["git", "rebase", "--abort"], check=False)
        fail("Rebase stuck mid-operation (continue/skip made no progress); aborted.")

    # Belt-and-suspenders: scan for any residual conflict markers in the tree.
    if conflict_marker_files():
        has_conflicts = True

    return git_out("rev-parse", "HEAD"), has_conflicts


def exit_with_conflicts(levels: list[Level], i: int, from_wip: bool) -> None:
    """Conflict handoff for level i: push the best-effort worktree state
    (markers included) to the level's -rebase-wip branch — unless the state
    came from that wip in the first place (a resume found the manual
    resolution still incomplete; never rewrite manual work). Levels below it
    are already staged on their own wips. Exits 0: conflicts are a handoff,
    not a workflow failure.
    """
    lvl = levels[i]
    files = conflict_marker_files()
    if files:
        print(files)
    if from_wip:
        error(f"⚠️ wip branch '{lvl.wip}' still contains conflict markers; leaving it untouched.")
    else:
        info(f"⚠️ Conflicts remain at #{lvl.pr}. Pushing best-effort branch '{lvl.wip}' for manual fix.")
        git_run("push", "--force", FORK_REMOTE, f"HEAD:refs/heads/{lvl.wip}")
    emit("has_conflicts", True)
    emit("conflict_pr", lvl.pr)
    emit("conflict_level", i)
    emit("wip_branch", lvl.wip)
    emit("staged_prs", " ".join(f"#{levels[j].pr}" for j in range(i)))
    emit("conflicting_files", files)
    sys.exit(0)


def take_stack_lock(levels: list[Level]) -> str:
    """Create-only lock ref on the fork, keyed by the root PR.

    The workflow-level concurrency group keys on the dispatched PR number, so
    it cannot dedupe two dispatches naming different members of the same
    stack; this can. It points at the root's existing head so no new objects
    reach the fork. Released by the workflow's cleanup job. The existence
    check runs first because pushing an OID a leftover lock already holds is
    an "up to date" no-op that sails past the lease; the lease still closes
    the check-then-create race for any concurrent run that moved the ref.
    """
    lock_ref = f"refs/rebase-locks/pr{levels[0].pr}"
    info(f"Taking stack lock {lock_ref} on {FORK_REPO}")
    held = fork_ref_exists(lock_ref)
    if held or not git_ok("push", FORK_REMOTE, f"{levels[0].old_head}:{lock_ref}", f"--force-with-lease={lock_ref}:"):
        fail(
            f"Stack lock {lock_ref} already exists on {FORK_REPO} — another rebase of this "
            "stack is (or was left) running. If you are certain none is, delete it with:\n"
            f'  gh api -X DELETE "repos/{FORK_REPO}/git/refs/{lock_ref.removeprefix("refs/")}"'
        )
    emit("lock_ref", lock_ref)
    return lock_ref


def chain_rebase(levels: list[Level], target: str, resume_from_wip: bool) -> None:
    """Rebase the stack root -> top, staging each clean level to its wip."""
    for i, lvl in enumerate(levels):
        onto = target if i == 0 else levels[i - 1].new_tip
        head = lvl.old_head
        boundary = lvl.boundary
        adopted = False
        lvl.orig_commits = int(git_out("rev-list", "--count", f"{boundary}..{head}"))

        # Resume: adopt what a previous run staged (and a human possibly fixed).
        # Existence is probed separately from the fetch: a failed fetch must
        # never read as "no wip staged" (see fork_ref_exists).
        if resume_from_wip and fork_ref_exists(f"refs/heads/{lvl.wip}"):
            git_run("fetch", "--no-tags", FORK_REMOTE, lvl.wip)
            wip_head = git_out("rev-parse", "FETCH_HEAD")
            if i == 0:
                # Root: re-rebase the wip onto the target (an identity
                # fast-forward when the target is unchanged, so the staged
                # SHAs are preserved). Same marker gate as the non-root
                # adopt below: an incomplete manual fix must re-report as
                # conflicted, not sail through the no-op path into the build.
                git_run("checkout", "-q", "-B", "rebase-tmp", wip_head)
                if conflict_marker_files():
                    exit_with_conflicts(levels, i, from_wip=True)
                head = wip_head
                boundary = git_out("merge-base", target, head)
                lvl.from_wip = True
                info(f"level {i}: resuming #{lvl.pr} from wip {lvl.wip} ({wip_head})")
            else:
                git_run("checkout", "-q", "-B", "rebase-tmp", wip_head)
                if conflict_marker_files():
                    exit_with_conflicts(levels, i, from_wip=True)
                if git_ok("merge-base", "--is-ancestor", onto, wip_head):
                    info(f"level {i}: adopting staged wip {lvl.wip} ({wip_head}) for #{lvl.pr}")
                    lvl.new_tip = wip_head
                    adopted = True
                else:
                    fail(
                        f"wip '{lvl.wip}' is stale relative to the rebased parent #{levels[i - 1].pr} "
                        "(the target or a lower level changed since it was staged). Delete it and "
                        "re-dispatch — manual fixes on it, if any, must be redone."
                    )

        if not adopted:
            if onto == boundary:
                lvl.new_tip = head
                if head == lvl.old_head:
                    # Already exactly in place: keep the SHAs, push nothing,
                    # re-test nothing.
                    info(f"level {i}: #{lvl.pr} ({lvl.branch}) already in place — no-op")
                    lvl.noop = True
                    lvl.new_commits = lvl.orig_commits
                    continue
                # (Root resume with an unchanged target): the wip already sits
                # on the target; the PR branch still needs the update.
            else:
                info(f"level {i}: rebasing #{lvl.pr} ({lvl.branch}): replaying {boundary}..{head} onto {onto}")
                tip, has_conflicts = rebase_level_with_resolver(onto, boundary, head)
                if has_conflicts:
                    exit_with_conflicts(levels, i, from_wip=lvl.from_wip)
                lvl.new_tip = tip
            # Stage the clean level immediately: a later conflict, build
            # failure, or crash then never loses it, and resume adopts it.
            git_run("push", "--force", FORK_REMOTE, f"{lvl.new_tip}:refs/heads/{lvl.wip}")

        lvl.new_commits = int(git_out("rev-list", "--count", f"{onto}..{lvl.new_tip}"))
        if lvl.new_commits < lvl.orig_commits:
            error(
                f"⚠️ level {i} (#{lvl.pr}): {lvl.orig_commits - lvl.new_commits} commit(s) dropped "
                f"({lvl.orig_commits} → {lvl.new_commits}). Expected for already-merged/absorbed "
                f"patches (link: {lvl.link}); verify no important commits vanished."
            )


def check_stack_invariant(levels: list[Level], target: str) -> None:
    """Every child must contain its parent's new tip (and the root the
    target) before anything can reach the PR branches. A violation is a bug
    in this script, not a conflict — fail hard."""
    if not git_ok("merge-base", "--is-ancestor", target, levels[0].new_tip):
        fail(
            f"internal error: rebased root #{levels[0].pr} does not contain the target "
            "— nothing was pushed to the PR branches."
        )
    for parent, child in zip(levels, levels[1:]):
        if not git_ok("merge-base", "--is-ancestor", parent.new_tip, child.new_tip):
            fail(f"internal error: stack invariant broken at #{child.pr} — nothing was pushed to the PR branches.")


# ─── Subcommands ───────────────────────────────────────────────────────────────


def setup_remotes(gh_token: str) -> None:
    upstream_url = os.environ.get("REBASE_UPSTREAM_URL", f"https://github.com/{UPSTREAM_REPO}")
    # Token embedded for push auth; it's a registered secret so Actions masks
    # it in logs.
    fork_url = os.environ.get("REBASE_FORK_URL", f"https://x-access-token:{gh_token}@github.com/{FORK_REPO}.git")
    for name, url in (("upstream", upstream_url), (FORK_REMOTE, fork_url)):
        if git_ok("remote", "get-url", name):
            git_run("remote", "set-url", name, url)
        else:
            git_run("remote", "add", name, url)


def cli_changed(target: str, top: str) -> bool:
    """Does the stack's own diff (target..top, before the harness overlay)
    touch the fboss2 CLI or its test plumbing? Drives the cli_changed output."""
    files = git_out("diff", "--name-only", target, top).splitlines()
    hits = [f for f in files if CLI_TEST_PATH_RE.match(f)]
    if hits:
        info(f"CLI-relevant files in the stack diff ({len(hits)}): fboss2 CLI suites will run")
        for f in hits[:20]:
            info(f"  {f}")
    else:
        info("No CLI-relevant files in the stack diff: fboss2 CLI suites (fboss-sim, DUT) will be skipped")
    return bool(hits)


def cmd_rebase(args: argparse.Namespace) -> None:
    gh_token = os.environ.get("GH_TOKEN") or ""
    if not gh_token:
        fail(f"GH_TOKEN required (read {UPSTREAM_REPO}, push {FORK_REPO})")
    setup_remotes(gh_token)
    git_run("fetch", "--no-tags", "upstream", UPSTREAM_BASE_BRANCH)

    # Resolve the dispatched PR -> author-derived names.
    info(f"Looking up upstream PR #{args.pr} in {UPSTREAM_REPO}")
    pr_data = gh_json(
        ["pr", "view", str(args.pr), "--repo", UPSTREAM_REPO, "--json", "headRefName,headRepositoryOwner,author"]
    )
    if pr_data["headRepositoryOwner"]["login"] != FORK_OWNER:
        fail(f"PR #{args.pr} head repo owner is '{pr_data['headRepositoryOwner']['login']}', expected '{FORK_OWNER}'. Aborting.")
    author_login = pr_data["author"]["login"]
    author_user = re.sub(r"[^a-z0-9_.-]", "-", author_login.removesuffix("-nexthop").lower()) or "upstream"
    test_branch = f"{author_user}.upstream-test.pr{args.pr}"
    info(f"PR branch:    {pr_data['headRefName']}")
    info(f"Author:       {author_login} -> user '{author_user}'")
    info(f"Test branch:  {test_branch} (private-fboss)")

    # Resolve the rebase target. The stable tarball pins the fboss sha
    # together with the dep pins it was validated with; they are used as a set
    # (the overlay consumes the same tarball that named the target).
    if not args.onto:
        stable_tarball = sync_lib(
            "materialize_stable_tarball",
            git_out("rev-list", "-1", f"upstream/{UPSTREAM_BASE_BRANCH}", "--", "fboss/oss/stable_commits"),
            capture=True,
        )
        target_ref = sync_lib("get_stable_commit", stable_tarball, capture=True)
        info(f"Rebase target: latest stable commit {target_ref}")
    else:
        target_ref = args.onto
        info(f"Rebase target: requested '{target_ref}'")
    # GitHub allows fetching a reachable SHA or a branch name the same way.
    git_run("fetch", "--no-tags", "upstream", target_ref)
    target = git_out("rev-parse", "FETCH_HEAD")
    info(f"Rebase target resolves to {target}")
    if args.onto:
        # Explicit target: no tarball names it, so take the newest one in the
        # target's own tree — the closest matching set of dep pins.
        stable_tarball = sync_lib(
            "materialize_stable_tarball",
            git_out("rev-list", "-1", target, "--", "fboss/oss/stable_commits"),
            capture=True,
        )
    emit("target", target)
    emit("pr_branch", pr_data["headRefName"])
    emit("author_user", author_user)
    emit("test_branch", test_branch)

    # Discover + verify the stack. A plain PR is a stack of size 1.
    levels, below_root = discover_stack(args.pr)
    verify_stack(levels, target, below_root)
    print_stack_plan(levels, target, below_root)
    emit("stack_size", len(levels))
    emit("merged_parent_pr", below_root.pr if below_root else "")
    emit("merged_parent_state", below_root.state if below_root else "")
    emit("merged_parent_sha", below_root.sha if below_root else "")
    emit("merged_parent_absorbed", below_root.absorbed if below_root else "")

    if args.dry_run:
        emit("dry_run", True)
        emit("has_conflicts", False)
        info("✅ Dry run: discovery + verification only; nothing was rebased or pushed.")
        return
    emit("dry_run", False)

    take_stack_lock(levels)
    chain_rebase(levels, target, args.resume_from_wip)

    emit("dropped_commits", any(lvl.new_commits < lvl.orig_commits for lvl in levels))
    emit("levels", levels_json(levels))

    if all(lvl.noop for lvl in levels):
        emit("all_noop", True)
        emit("has_conflicts", False)
        info("✅ Every level is already in place; nothing to rebase, build, or push.")
        return
    emit("all_noop", False)

    check_stack_invariant(levels, target)
    top = levels[-1].new_tip

    # Log the stack's net diff on the rebase target: the test branch is
    # deleted on cleanup, so this is the only record of what the rebase
    # actually produced.
    git_run("checkout", "-q", "-B", "rebase-tmp", top)
    info(f"Diff applied by the rebase ({target}..{top}):")
    git_run("diff", "--stat", target, top)
    git_run("diff", target, top)
    emit("cli_changed", cli_changed(target, top))

    info("Overlaying NH CI harness onto the stack top")
    sync_lib(
        "overlay_nh_harness",
        NH_REPO_BRANCH,
        stable_tarball,
        f"CI: build-test upstream PR {args.pr} stack with NH harness (do not merge)",
    )

    info(f"Pushing rebase + NH harness to private-fboss:{test_branch}")
    git_run("push", "--force", "origin", f"HEAD:refs/heads/{test_branch}")

    emit("has_conflicts", False)
    emit("rebased_sha", top)
    info(f"✅ Stack rebase complete ({len(levels)} level(s)).")


def cmd_push(_args: argparse.Namespace) -> None:
    gh_token = os.environ.get("GH_TOKEN") or ""
    if not gh_token:
        fail("GH_TOKEN required")
    levels = json.loads(os.environ["LEVELS"])
    test_branch = os.environ["TEST_BRANCH"]
    setup_remotes(gh_token)
    # test_branch (private-fboss) is the stack top plus our NH-harness overlay
    # commit; every level's new_tip is an ancestor of it, so one fetch brings
    # all the objects. Only the rebased commits are ever pushed to the real
    # (public) PR branches — never the harness overlay.
    git_run("fetch", "--no-tags", "origin", test_branch)
    moved = [lvl for lvl in levels if not lvl["noop"]]
    # Pass 1: leased dry-run for every branch, so the update is
    # all-or-nothing: if any PR branch moved since the rebase started,
    # nothing is pushed.
    for lvl in moved:
        git_run(
            "push",
            "--dry-run",
            f"--force-with-lease={lvl['branch']}:{lvl['old_head']}",
            FORK_REMOTE,
            f"{lvl['new_tip']}:refs/heads/{lvl['branch']}",
        )
    # Pass 2: the real pushes, bottom -> top.
    for lvl in moved:
        git_run(
            "push",
            f"--force-with-lease={lvl['branch']}:{lvl['old_head']}",
            FORK_REMOTE,
            f"{lvl['new_tip']}:refs/heads/{lvl['branch']}",
        )
        print(f"✅ Updated {FORK_REPO}:{lvl['branch']} to {lvl['new_tip']}")


def heal_body(body: str, parent: int | None, stack_list: str) -> str:
    """Re-align one PR body's stack declarations; everything else untouched."""
    based_on = f"Based-on: {UPSTREAM_REPO}#{parent}" if parent else 'Based-on: "main"'
    out: list[str] = []
    seen_trailer = False
    for line in body.replace("\r", "").split("\n"):
        if line.startswith("> **Stack (bottom → top):**"):
            out.append(f"> **Stack (bottom → top):** {stack_list}")
        elif parent and re.match(r"> \*\*Stacked on #\d+\*\*", line):
            out.append(re.sub(r"#\d+", f"#{parent}", line, count=1))
        elif line.lower().startswith("based-on:"):
            out.append(based_on)
            seen_trailer = True
        else:
            out.append(line)
    if not seen_trailer:
        out += ["", based_on]
    return "\n".join(out)


def cmd_heal(_args: argparse.Namespace) -> None:
    levels = json.loads(os.environ["LEVELS"])
    prs = [lvl["pr"] for lvl in levels]
    if len(prs) < 2:
        print("Single PR — no stack declarations to update.")
        return
    for i, pr in enumerate(prs):
        parent = prs[i - 1] if i else None
        stack_list = " → ".join(f"**#{p} (this PR)**" if j == i else f"#{p}" for j, p in enumerate(prs))
        body = run(
            ["gh", "pr", "view", str(pr), "--repo", UPSTREAM_REPO, "--json", "body", "--jq", ".body"],
            capture=True,
        ).stdout
        new_body = heal_body(body, parent, stack_list)
        if new_body == body.replace("\r", ""):
            print(f"#{pr}: stack declarations already current.")
            continue
        result = run(
            ["gh", "pr", "edit", str(pr), "--repo", UPSTREAM_REPO, "--body-file", "-"],
            check=False,
            capture=True,
            stdin=new_body,
        )
        if result.returncode == 0:
            print(f"#{pr}: stack declarations updated.")
        else:
            wanted = f"#{parent}" if parent else '"main" (root)'
            print(
                f"::warning::Could not update the stack declarations on #{pr} "
                f"(token lacks edit rights on that PR?). Update them manually: parent = {wanted}."
            )


# ─── Slack notifications ───────────────────────────────────────────────────────
#
# Message builders are pure functions over the notify job's environment (see
# the notify jobs in rebase-upstream-pr.yml for who sets what), so they are
# unit-testable; only slack_* below does I/O.


def build_success_message(env) -> str:
    """What happened and how to undo it. The old head OIDs are the one piece
    of state that's painful to dig up later (PR timeline archaeology), so a
    revert command per moved branch ships in the message."""
    levels = json.loads(env["LEVELS"])
    via = (
        "the staged/manually-resolved -rebase-wip branches (now deleted)"
        if env.get("RESUMED") == "true"
        else "automatic rebase"
    )
    scope = (
        f"The {env['STACK_SIZE']}-PR upstream stack of #{env['PR']}"
        if int(env.get("STACK_SIZE") or 1) > 1
        else f"Upstream PR #{env['PR']}"
    )
    lines = [
        f"✅ {scope} was rebased onto `{env['TARGET']}`, build and tests passed, "
        f"and the PR branch(es) in {FORK_REPO} were updated (via {via})."
    ]
    lines += [
        f"• #{lvl['pr']} `{lvl['branch']}` → `{lvl['new_tip'][:12]}` — revert: "
        f"`git push --force origin {lvl['old_head']}:refs/heads/{lvl['branch']}`"
        for lvl in levels
        if not lvl["noop"]
    ]
    unmoved = ", ".join(f"#{lvl['pr']}" for lvl in levels if lvl["noop"])
    if unmoved:
        lines.append(f"Already in place (untouched): {unmoved}")
    lines.append(f"Run: {env['RUN_URL']}")
    return "\n".join(lines)


def build_conflicts_message(env) -> str:
    staged = ""
    if env.get("STAGED_PRS"):
        staged = (
            f"\nLevels below it ({env['STAGED_PRS']}) rebased cleanly and are staged "
            "on their own -rebase-wip branches; the resume adopts them as-is."
        )
    where = f"at stack level #{env['CONFLICT_PR']}"
    if env.get("CONFLICT_LEVEL") and env.get("STACK_SIZE"):
        where += f" (level {int(env['CONFLICT_LEVEL']) + 1} of {env['STACK_SIZE']})"
    return (
        f"<@{env['MABEL']}> the rebase of upstream PR #{env['PR']} onto `{env['TARGET']}` "
        f"still has conflicts after nh-fix-merge-conflicts.py, {where}. "
        f"Please resolve the merge conflicts on branch `{env['WIP_BRANCH']}` in {FORK_REPO}, "
        "force-push the corrected rebase to that same branch, then resume validation with:\n"
        f"```gh workflow run rebase-upstream-pr.yml -R {env['REPO']} --ref {NH_REPO_BRANCH} "
        f"-f pr_number={env['PR']} -f rebase_onto={env['TARGET']} -f resume_from_wip=true```\n"
        "Do NOT push to the PR branches directly — the resume run build-tests the wip branches "
        f"and updates the PRs only on green.{staged}\n"
        f"Conflicting files:\n{env['CONFLICTS']}\n"
        f"Run: {env['RUN_URL']}"
    )


def build_build_failure_message(env) -> str:
    failed_tests = env.get("FAILED_TESTS") or "<none captured — likely a build failure>"
    what = "build-and-test cycle"
    if env.get("SIM_RESULT") == "failure":
        what = "fboss-sim CLI integration test (see the fboss-sim CLI Test job)"
    return (
        f"<@{env['MABEL']}> the {what} for rebased upstream PR #{env['PR']} "
        f"(branch `{env['PR_BRANCH']}`) failed. Please investigate and fix.\n"
        f"Failed tests ({env.get('FAILED_COUNT') or '?'}):\n{failed_tests}\n"
        f"Run: {env['RUN_URL']}"
    )


def build_dropped_commits_message(env) -> str:
    levels = json.loads(env["LEVELS"])
    lines = [
        f"• #{lvl['pr']} `{lvl['branch']}`: {lvl['orig_commits'] - lvl['new_commits']} dropped "
        f"({lvl['orig_commits']} → {lvl['new_commits']}, link: {lvl['link']})"
        for lvl in levels
        if lvl["orig_commits"] > lvl["new_commits"]
    ]
    # The merged-parent context makes an expected absorption distinguishable
    # from a real loss at a glance.
    ctx = ""
    state = env.get("MERGED_PARENT_STATE") or ""
    if state == "merged":
        if env.get("MERGED_PARENT_ABSORBED") == "true":
            ctx = (
                f"\nContext: the stack sat on #{env['MERGED_PARENT_PR']}, which was merged upstream "
                f"as `{env['MERGED_PARENT_SHA']}` and is contained in the rebase target — the root "
                "dropping its carried copies is the expected outcome."
            )
        else:
            ctx = (
                f"\nContext: the stack sat on #{env['MERGED_PARENT_PR']} (merged upstream as "
                f"`{env['MERGED_PARENT_SHA']}`), but the rebase target does not contain that commit yet."
            )
    elif state:
        ctx = (
            f"\nContext: the stack sat on #{env['MERGED_PARENT_PR']}, which is {state} WITHOUT "
            "a merge signal — dropped commits here deserve a real look."
        )
    return (
        f"<@{env['MABEL']}> ⚠️ the rebase of upstream PR #{env['PR']} dropped commit(s):\n"
        + "\n".join(lines)
        + ctx
        + "\nThis is expected for already-merged patches and for pending-restack links (copies of "
        "parent commits get absorbed), but please verify no important commits vanished before "
        "the PRs are updated.\n"
        f"Run: {env['RUN_URL']}"
    )


MESSAGE_BUILDERS = {
    "success": build_success_message,
    "conflicts": build_conflicts_message,
    "build-failure": build_build_failure_message,
    "dropped-commits": build_dropped_commits_message,
}


def _slack_api(url: str, *, token: str = "", payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode() if payload is not None else None, headers=headers
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": body.strip() == "ok"}  # incoming webhooks answer plain "ok"


def slack_dm(token: str, author: str, text: str) -> bool:
    """DM the author: internal usernames map to @nexthop.ai emails, which
    Slack resolves to a member id. Requires scopes chat:write +
    users:read.email."""
    query = urllib.parse.urlencode({"email": f"{author}@nexthop.ai"})
    lookup = _slack_api(f"https://slack.com/api/users.lookupByEmail?{query}", token=token)
    user_id = (lookup.get("user") or {}).get("id") if lookup.get("ok") else None
    if not user_id:
        return False
    posted = _slack_api(
        "https://slack.com/api/chat.postMessage", token=token, payload={"channel": user_id, "text": text}
    )
    return posted.get("ok") is True


def cmd_notify(args: argparse.Namespace) -> None:
    env = os.environ
    text = MESSAGE_BUILDERS[args.kind](env)
    if args.kind == "success":
        if env.get("SLACK_BOT_TOKEN") and slack_dm(env["SLACK_BOT_TOKEN"], env["AUTHOR"], text):
            return
        if env.get("SLACK_BOT_TOKEN"):
            print(f"::warning::Slack DM to '{env['AUTHOR']}' failed; falling back to channel webhook.")
        text = f"{env['AUTHOR']}: {text}"
    _slack_api(env["WEBHOOK"], payload={"text": text})


def str2bool(value: str) -> bool:
    return value.strip().lower() == "true"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    rebase = sub.add_parser("rebase", help="discover, verify, and chain-rebase the PR's stack")
    rebase.add_argument("pr", type=int, help=f"{UPSTREAM_REPO} PR number (any member of a stack)")
    rebase.add_argument("--onto", default="", help="rebase target for the root; empty = latest stable commit")
    rebase.add_argument("--resume-from-wip", type=str2bool, default=False, metavar="BOOL")
    rebase.add_argument("--dry-run", type=str2bool, default=False, metavar="BOOL")
    rebase.set_defaults(func=cmd_rebase)

    push = sub.add_parser("push", help="leased all-or-nothing force-push of the rebased branches")
    push.set_defaults(func=cmd_push)

    heal = sub.add_parser("heal", help="re-align stack declarations in the member PRs' bodies")
    heal.set_defaults(func=cmd_heal)

    notify = sub.add_parser("notify", help="build and post the Slack message for one workflow outcome")
    notify.add_argument("kind", choices=sorted(MESSAGE_BUILDERS))
    notify.set_defaults(func=cmd_notify)

    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        detail = f"\n{exc.stderr.strip()}" if exc.stderr else ""
        fail(f"command failed ({exc.returncode}): {' '.join(exc.cmd)}{detail}")


if __name__ == "__main__":
    main()
