"""Sandbox tests for rebase_upstream_pr.py (the stack-aware upstream rebase).

Each test builds a synthetic 3-PR stack (br1 -> br2 -> br3, one commit each)
against local bare "upstream" and "fork" repositories, with fake_gh.py on
PATH serving the PR listing/bodies and fake_sync_lib.sh replacing the
stable-tarball / conflict-resolver / harness-overlay machinery. The script
under test runs as a real subprocess with REBASE_*_URL pointed at the local
remotes, so everything from discovery through the wip/lock ref pushes is
exercised for real — only GitHub itself is faked.

Run with:  python3 -m pytest .github/scripts/tests/test_rebase_upstream_pr.py
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent

class Sandbox:
    def __init__(self, root: Path):
        self.root = root
        self.upstream = root / "upstream.git"
        self.fork = root / "fork.git"
        self.private = root / "private.git"
        self.seed = root / "seed"
        self.work = root / "work"
        self.outputs = root / "outputs"
        self._build()

    # ── construction ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        for bare in (self.upstream, self.fork, self.private):
            self._sh("git", "init", "-q", "--bare", str(bare), cwd=self.root)

        self._sh("git", "init", "-q", str(self.seed), cwd=self.root)
        self.git_seed("config", "user.email", "t@t")
        self.git_seed("config", "user.name", "t")
        (self.seed / "base.txt").write_text("base\n")
        self.git_seed("add", ".")
        self.git_seed("commit", "-qm", "base")
        self.git_seed("branch", "-M", "main")
        # The stack: br1 (root) -> br2 -> br3, one commit each.
        for branch, f in (("br1", "f1"), ("br2", "f2"), ("br3", "f3")):
            self.git_seed("checkout", "-qb", branch)
            (self.seed / f"{f}.txt").write_text(f"{f}\n")
            self.git_seed("add", ".")
            self.git_seed("commit", "-qm", f"PR: {f}")
        # Upstream then advances past the branches: target commit T.
        self.git_seed("checkout", "-q", "main")
        (self.seed / "t.txt").write_text("t\n")
        self.git_seed("add", ".")
        self.git_seed("commit", "-qm", "upstream: T")
        self.git_seed("push", "-q", str(self.upstream), "main")
        self.git_seed("push", "-q", str(self.fork), "br1", "br2", "br3")

        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "rebase_upstream_pr.py").write_bytes((SCRIPTS_DIR / "rebase_upstream_pr.py").read_bytes())
        (scripts / "rebase_upstream_pr.py").chmod(0o755)
        (scripts / "sync-lib.sh").write_bytes((TESTS_DIR / "fake_sync_lib.sh").read_bytes())

        gh_bin = self.root / "bin"
        gh_bin.mkdir()
        (gh_bin / "gh").symlink_to(TESTS_DIR / "fake_gh.py")

        self._sh("git", "clone", "-q", str(self.private), str(self.work), cwd=self.root)
        self.git_work("config", "user.email", "t@t")
        self.git_work("config", "user.name", "t")
        self.git_work("fetch", "-q", str(self.upstream), "main")
        self.git_work("checkout", "-q", "FETCH_HEAD")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _sh(
        self, *cmd: str, cwd: Path, check: bool = True, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            text=True,
            capture_output=True,
            env={**os.environ, **env} if env else None,
        )

    def git_seed(self, *args: str) -> str:
        return self._sh("git", *args, cwd=self.seed).stdout.strip()

    def git_work(self, *args: str) -> str:
        return self._sh("git", *args, cwd=self.work).stdout.strip()

    def git_fork(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._sh("git", "--git-dir", str(self.fork), *args, cwd=self.root, check=check)

    def fork_ref(self, ref: str) -> str | None:
        r = self.git_fork("rev-parse", "--verify", "-q", ref, check=False)
        return r.stdout.strip() if r.returncode == 0 else None

    def fork_branch(self, name: str) -> str | None:
        return self.fork_ref(f"refs/heads/{name}")

    def is_ancestor(self, older: str, newer: str) -> bool:
        return self.git_fork("merge-base", "--is-ancestor", older, newer, check=False).returncode == 0

    def run_rebase(self, pr: int, *, resume: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.outputs.write_text("")
        env = {
            **os.environ,
            "PATH": f"{self.root / 'bin'}:{os.environ['PATH']}",
            "GH_TOKEN": "x",
            "GITHUB_OUTPUT": str(self.outputs),
            "SANDBOX": str(self.root),
            "REBASE_UPSTREAM_URL": f"file://{self.upstream}",
            "REBASE_FORK_URL": f"file://{self.fork}",
        }
        return subprocess.run(
            [str(self.root / "scripts" / "rebase_upstream_pr.py"), "rebase", str(pr), "--onto", "main"]
            + (["--resume-from-wip", "true"] if resume else []),
            cwd=self.work,
            env=env,
            check=check,
            text=True,
            capture_output=True,
        )

    def out(self, key: str) -> str:
        lines = self.outputs.read_text().splitlines()
        for i, line in enumerate(lines):
            if line == f"{key}<<GITHUB_OUTPUT_EOF":
                return "\n".join(lines[i + 1 : lines.index("GITHUB_OUTPUT_EOF", i + 1)])
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
        return ""

    def levels(self) -> list[dict]:
        return json.loads(self.out("levels"))

    def simulate_update_and_cleanup(self) -> None:
        """What the update-pr + cleanup jobs do after a green run."""
        for branch in ("br1", "br2", "br3"):
            wip = self.fork_branch(f"{branch}-rebase-wip")
            if wip:
                self.git_fork("update-ref", f"refs/heads/{branch}", wip)
                self.git_fork("update-ref", "-d", f"refs/heads/{branch}-rebase-wip")
        self.release_lock()

    def release_lock(self) -> None:
        if self.fork_ref("refs/rebase-locks/pr101"):
            self.git_fork("update-ref", "-d", "refs/rebase-locks/pr101")

    def advance_upstream_conflicting(self) -> None:
        """Push an upstream commit that conflicts with br2's f2.txt."""
        self.git_seed("checkout", "-q", "main")
        (self.seed / "f2.txt").write_text("conflict\n")
        self.git_seed("add", ".")
        self.git_seed("commit", "-qm", "upstream: conflicts with PR102")
        self.git_seed("push", "-q", str(self.upstream), "main")

    def merge_bottom_pr(self) -> str:
        """Land br1's commit on upstream main and flip PR 101 to the upstream
        merged state (closed + bot comment naming the landed sha)."""
        self.git_seed("fetch", "-q", str(self.upstream), "main")
        self.git_seed("checkout", "-q", "FETCH_HEAD")
        self.git_seed("fetch", "-q", str(self.fork), "br1")
        br1 = self.git_fork("rev-parse", "refs/heads/br1").stdout.strip()
        # Pin a distinct committer date: with the same parent, tree, author
        # date, and committer second, the cherry-pick would reproduce br1's
        # exact SHA and the "absorption" would be invisible.
        self._sh(
            "git",
            "cherry-pick",
            br1,
            cwd=self.seed,
            env={"GIT_COMMITTER_DATE": "2030-01-01T00:00:00 +0000"},
        )
        sha = self.git_seed("rev-parse", "HEAD")
        (self.root / "merged101").write_text(sha)
        self.git_seed("push", "-q", str(self.upstream), "HEAD:main")
        return sha


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)


def test_fresh_chain_rebase(sandbox: Sandbox) -> None:
    before = {b: sandbox.fork_branch(b) for b in ("br1", "br2", "br3")}
    sandbox.run_rebase(102)  # a mid-stack dispatch handles the whole stack

    assert sandbox.out("has_conflicts") == "false"
    assert sandbox.out("stack_size") == "3"
    assert sandbox.out("all_noop") == "false"
    assert sandbox.out("cli_changed") == "false"  # f1..f3.txt: no CLI paths
    levels = sandbox.levels()
    assert [lvl["pr"] for lvl in levels] == [101, 102, 103]
    assert all(not lvl["noop"] for lvl in levels)

    # PR branches untouched; every level staged on its wip; lock taken.
    assert {b: sandbox.fork_branch(b) for b in before} == before
    wips = [sandbox.fork_branch(f"{b}-rebase-wip") for b in ("br1", "br2", "br3")]
    assert all(wips)
    assert sandbox.fork_ref("refs/rebase-locks/pr101")

    # The staged chain keeps the stack invariant, the lease pins are the
    # pre-run heads, and the reported tips are the staged wips.
    assert sandbox.is_ancestor(wips[0], wips[1]) and sandbox.is_ancestor(wips[1], wips[2])
    assert levels[0]["old_head"] == before["br1"]
    assert levels[2]["new_tip"] == wips[2]


def test_cli_changed_flags_cli_paths_anywhere_in_stack(sandbox: Sandbox) -> None:
    # A CLI file on the root level (not the dispatched PR) still flips the
    # flag: the gate looks at the whole stack's diff on the target.
    sandbox.git_seed("checkout", "-q", "br1")
    (sandbox.seed / "fboss" / "cli").mkdir(parents=True)
    (sandbox.seed / "fboss" / "cli" / "cmd.cpp").write_text("cli\n")
    sandbox.git_seed("add", ".")
    sandbox.git_seed("commit", "-qm", "PR: cli")
    sandbox.git_seed("push", "-q", str(sandbox.fork), "br1")
    # br2/br3 now lag br1 (pending-restack); the chain rebase restacks them.
    sandbox.run_rebase(103)
    assert sandbox.out("has_conflicts") == "false"
    assert sandbox.out("cli_changed") == "true"


def test_lock_refuses_concurrent_dispatch(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    second = sandbox.run_rebase(103, check=False)
    assert second.returncode != 0
    assert "Stack lock" in second.stderr


def test_all_noop_rerun_preserves_shas(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    sandbox.simulate_update_and_cleanup()
    heads = {b: sandbox.fork_branch(b) for b in ("br1", "br2", "br3")}

    sandbox.run_rebase(101)
    assert sandbox.out("all_noop") == "true"
    assert sandbox.out("has_conflicts") == "false"
    assert all(lvl["noop"] for lvl in sandbox.levels())
    assert {b: sandbox.fork_branch(b) for b in heads} == heads
    assert sandbox.fork_branch("br1-rebase-wip") is None  # no wip churn on no-ops


def test_conflict_hands_off_wip_with_lower_levels_staged(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    sandbox.simulate_update_and_cleanup()
    sandbox.advance_upstream_conflicting()

    sandbox.run_rebase(101)
    assert sandbox.out("has_conflicts") == "true"
    assert sandbox.out("conflict_pr") == "102"
    assert sandbox.out("conflict_level") == "1"
    assert sandbox.out("wip_branch") == "br2-rebase-wip"
    assert sandbox.out("staged_prs") == "#101"
    assert sandbox.fork_branch("br1-rebase-wip")  # root staged below the conflict
    conflicted = sandbox.fork_branch("br2-rebase-wip")
    show = sandbox.git_fork("show", f"{conflicted}:f2.txt")
    assert "<<<<<<<" in show.stdout


def test_resume_adopts_staged_and_manual_fix(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    sandbox.simulate_update_and_cleanup()
    sandbox.advance_upstream_conflicting()
    sandbox.run_rebase(101)
    sandbox.release_lock()

    # A human resolves the conflicted level on its wip branch.
    sandbox.git_seed("fetch", "-q", str(sandbox.fork), "br2-rebase-wip")
    sandbox.git_seed("checkout", "-q", "FETCH_HEAD")
    (sandbox.seed / "f2.txt").write_text("resolved\n")
    sandbox.git_seed("add", "f2.txt")
    sandbox.git_seed("commit", "-q", "--amend", "--no-edit")
    sandbox.git_seed("push", "-qf", str(sandbox.fork), "HEAD:br2-rebase-wip")

    sandbox.run_rebase(101, resume=True)
    assert sandbox.out("has_conflicts") == "false"
    levels = sandbox.levels()
    # The manual fix is adopted verbatim, the chain above rebased onto it,
    # and the resolution reaches the stack top.
    assert levels[1]["new_tip"] == sandbox.fork_branch("br2-rebase-wip")
    assert sandbox.is_ancestor(levels[0]["new_tip"], levels[1]["new_tip"])
    assert sandbox.is_ancestor(levels[1]["new_tip"], levels[2]["new_tip"])
    assert sandbox.git_fork("show", f"{levels[2]['new_tip']}:f2.txt").stdout == "resolved\n"


def test_resume_root_wip_with_markers_rereports_conflict(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    sandbox.simulate_update_and_cleanup()
    # Upstream advances with a commit conflicting with the ROOT's f1.txt.
    sandbox.git_seed("checkout", "-q", "main")
    (sandbox.seed / "f1.txt").write_text("conflict\n")
    sandbox.git_seed("add", ".")
    sandbox.git_seed("commit", "-qm", "upstream: conflicts with PR101")
    sandbox.git_seed("push", "-q", str(sandbox.upstream), "main")

    sandbox.run_rebase(101)
    assert sandbox.out("has_conflicts") == "true"
    assert sandbox.out("conflict_pr") == "101"
    assert sandbox.out("conflict_level") == "0"
    assert "<<<<<<<" in sandbox.git_fork("show", f"{sandbox.fork_branch('br1-rebase-wip')}:f1.txt").stdout
    sandbox.release_lock()

    # Resume with the markers still unresolved: the root must get the same
    # marker gate as the other levels — re-report the conflict, don't adopt
    # the wip and sail into the build.
    sandbox.run_rebase(101, resume=True)
    assert sandbox.out("has_conflicts") == "true"
    assert sandbox.out("conflict_pr") == "101"
    assert sandbox.out("wip_branch") == "br1-rebase-wip"


def test_merged_bottom_pr_shrinks_stack_and_absorbs(sandbox: Sandbox) -> None:
    sandbox.run_rebase(102)
    sandbox.simulate_update_and_cleanup()
    sha = sandbox.merge_bottom_pr()

    sandbox.run_rebase(102)
    assert sandbox.out("has_conflicts") == "false"
    assert sandbox.out("stack_size") == "2"
    assert sandbox.out("merged_parent_pr") == "101"
    assert sandbox.out("merged_parent_state") == "merged"
    assert sandbox.out("merged_parent_sha") == sha
    assert sandbox.out("merged_parent_absorbed") == "true"

    levels = sandbox.levels()
    assert [lvl["pr"] for lvl in levels] == [102, 103]
    # The root carried the merged commit; the rebase absorbed it (2 -> 1),
    # flagged as a drop, with the merged content still present at the top.
    assert (levels[0]["orig_commits"], levels[0]["new_commits"]) == (2, 1)
    assert sandbox.out("dropped_commits") == "true"
    assert sandbox.is_ancestor(levels[0]["new_tip"], levels[1]["new_tip"])
    assert sandbox.git_fork("show", f"{levels[1]['new_tip']}:f1.txt").stdout == "f1\n"


def _import_script():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("rup", SCRIPTS_DIR / "rebase_upstream_pr.py")
    rup = importlib.util.module_from_spec(spec)
    # Registration is required for dataclasses to resolve the module's
    # `from __future__ import annotations` string annotations.
    sys.modules["rup"] = rup
    spec.loader.exec_module(rup)
    return rup


def test_heal_body_rewrites_only_declarations() -> None:
    rup = _import_script()

    body = textwrap.dedent(
        """\
        > **Stacked on #1391** (bgp neighbor). Review only this commit.
        >
        > **Stack (bottom → top):** #1446 → **#1395 (this PR)** → #1401

        ## Summary
        real content stays

        Based-on: "main"
        """
    ).rstrip("\n")
    healed = rup.heal_body(body, parent=1391, stack_list="#1391 → **#1395 (this PR)** → #1401")
    assert "> **Stack (bottom → top):** #1391 → **#1395 (this PR)** → #1401" in healed
    assert "Based-on: facebook/fboss#1391" in healed
    assert "real content stays" in healed
    assert 'Based-on: "main"' not in healed
    # A root keeps its "main" trailer and gains one if missing.
    assert rup.heal_body("no trailer here", parent=None, stack_list="x").endswith('Based-on: "main"')


def test_notify_message_builders() -> None:
    rup = _import_script()
    levels = json.dumps(
        [
            {"pr": 101, "branch": "br1", "old_head": "a" * 40, "new_tip": "b" * 40,
             "noop": False, "link": "root", "orig_commits": 2, "new_commits": 1},
            {"pr": 102, "branch": "br2", "old_head": "c" * 40, "new_tip": "c" * 40,
             "noop": True, "link": "intact", "orig_commits": 1, "new_commits": 1},
        ]
    )
    base = {"PR": "102", "MABEL": "U123", "RUN_URL": "http://run", "LEVELS": levels, "TARGET": "t" * 40}

    success = rup.build_success_message({**base, "STACK_SIZE": "2", "RESUMED": "false", "AUTHOR": "hillol"})
    assert "The 2-PR upstream stack of #102" in success
    assert f"git push --force origin {'a' * 40}:refs/heads/br1" in success  # revert command
    assert "Already in place (untouched): #102" in success
    assert "br2` →" not in success  # no-op levels get no moved line

    conflicts = rup.build_conflicts_message(
        {**base, "CONFLICT_PR": "102", "CONFLICT_LEVEL": "1", "STACK_SIZE": "2",
         "WIP_BRANCH": "br2-rebase-wip", "STAGED_PRS": "#101",
         "CONFLICTS": "f2.txt", "REPO": "nexthop-ai/private-fboss"}
    )
    assert "at stack level #102 (level 2 of 2)" in conflicts
    assert "Levels below it (#101) rebased cleanly" in conflicts
    assert "-f resume_from_wip=true" in conflicts
    assert "--ref " in conflicts  # resume must re-dispatch the same workflow version

    absorbed = rup.build_dropped_commits_message(
        {**base, "MERGED_PARENT_PR": "100", "MERGED_PARENT_STATE": "merged",
         "MERGED_PARENT_SHA": "d" * 40, "MERGED_PARENT_ABSORBED": "true"}
    )
    assert "• #101 `br1`: 1 dropped (2 → 1, link: root)" in absorbed
    assert "the expected outcome" in absorbed
    assert "#102" not in absorbed.split("Context:")[0].split("\n", 1)[1]  # no drop line for br2

    unabsorbed = rup.build_dropped_commits_message(
        {**base, "MERGED_PARENT_PR": "100", "MERGED_PARENT_STATE": "closed",
         "MERGED_PARENT_SHA": "", "MERGED_PARENT_ABSORBED": ""}
    )
    assert "WITHOUT a merge signal" in unabsorbed

    failure = rup.build_build_failure_message(
        {**base, "PR_BRANCH": "br2", "FAILED_TESTS": "", "FAILED_COUNT": ""}
    )
    assert "<none captured — likely a build failure>" in failure
    assert "build-and-test cycle" in failure

    sim_failure = rup.build_build_failure_message(
        {**base, "PR_BRANCH": "br2", "FAILED_TESTS": "", "FAILED_COUNT": "", "SIM_RESULT": "failure"}
    )
    assert "fboss-sim CLI integration test" in sim_failure
