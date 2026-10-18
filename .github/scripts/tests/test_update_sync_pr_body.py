"""Tests for update-sync-pr-body.py.

Most cases exercise the pure rewrite (body text in, body text out). A handful
run the script as a subprocess in a throwaway repo with markers committed, a
fake `gh` on PATH, a fake detector and a $GITHUB_OUTPUT file, so
git-grep -> render/refresh -> `gh pr edit` is covered for real.

Run with:  python3 -m pytest .github/scripts/tests/test_update_sync_pr_body.py
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "update-sync-pr-body.py"
_SPEC = importlib.util.spec_from_file_location("update_sync_pr_body", SCRIPT)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

# Spelled at runtime: literal conflict markers in this file would trip the
# repo's merge-marker pre-commit hook and the build-and-test grep.
MARKER = "<" * 7 + " HEAD"

A = "fboss/agent/SwSwitch.cpp"
B = "fboss/agent/hw/Jericho2Asic.cpp"
C = "fboss/cli/tools/bgp_json_to_cli.py"


def body_with(entries: list[str]) -> str:
    """A description as sync-upstream.yml's create-pr step used to write it."""
    return "\n".join(
        [
            "This PR syncs private-fboss with upstream stable commit.",
            "",
            "**Stable Commit:** `db68cb3d891c6a1a6089c74c8245f13e674c8cbb`",
            "",
            mod.HEADING,
            "",
            mod.ANCHOR,
            *entries,
            "",
            "Please resolve these conflicts and merge when ready.",
            "",
        ]
    )


def detect_all(paths: list[str]) -> dict[str, str | None]:
    return dict.fromkeys(paths, "detected-nexthop")


def no_detect(paths: list[str]) -> dict[str, str | None]:
    raise AssertionError(f"owner detection must not run for {paths}")


def test_find_section():
    """Legacy bodies, marker bodies, bodies without one, unterminated markers."""
    lines = body_with([f"- [ ] {A} — @saty-nexthop"]).split("\n")
    start, end = mod.find_section(lines)
    assert (lines[start], lines[end - 1]) == (mod.HEADING, f"- [ ] {A} — @saty-nexthop")

    rendered, _ = mod.refresh(body_with([f"- [ ] {A}"]), [A], detect_all)
    lines = rendered.split("\n")
    start, end = mod.find_section(lines)
    assert (lines[start], lines[end - 1]) == (mod.START_MARKER, mod.END_MARKER)

    assert mod.find_section(["just a description", ""]) is None

    unterminated = [mod.START_MARKER, "", mod.HEADING, "", mod.ANCHOR, f"- [ ] {A}", ""]
    assert mod.find_section(unterminated) == (0, 6)


def test_refresh_rewrites_the_list():
    """The reported bug: a file resolved by a fix commit has to drop off, a file
    that appeared since has to be added, and the rest keeps its annotations."""
    body = body_with([f"- [ ] {A} — @saty-nexthop", f"- [x] {B} — @abhi-nexthop"])
    new, changed = mod.refresh(body, [A, C], detect_all)

    assert changed
    assert new.startswith("This PR syncs private-fboss with upstream stable commit.")
    assert new.endswith("Please resolve these conflicts and merge when ready.\n")
    assert "\n\n\n" not in new  # the trailer keeps exactly one blank line
    assert mod.START_MARKER in new and mod.END_MARKER in new
    assert f"- [ ] {A} — @saty-nexthop" in new  # annotation reused
    assert f"- [ ] {C} — @detected-nexthop" in new  # appeared since: guessed
    assert B not in new
    assert "- [x]" not in new  # a tick would claim a resolution the branch lacks


def test_the_created_description_round_trips_through_a_refresh():
    """A new sync PR must not be rewritten by its first /resync.

    This pins the cross-file contract: the description create-pr assembles (a
    --print-section spliced into the body the way sync-upstream.yml indents it)
    has to be a fixed point of refresh -- markers, blank lines and all.
    """
    section = "\n".join(mod.render_section([A, B], {A: "saty-nexthop", B: None}))
    body = (
        "This PR syncs private-fboss with upstream stable commit.\n\n"
        "**Stable Commit:** `db68cb3d891c6a1a6089c74c8245f13e674c8cbb`\n\n"
        f"{section}\n\n"
        "Please resolve these conflicts and merge when ready."
    )

    assert mod.refresh(body, [A, B], no_detect) == (body, False)


def test_refresh_guesses_only_for_files_it_has_never_listed():
    seen: list[list[str]] = []

    def detect(missing: list[str]):
        seen.append(missing)
        return detect_all(missing)

    # A is annotated, B is listed without an owner (the sync PR's detector found
    # none), C is new.
    new, _ = mod.refresh(body_with([f"- [ ] {A} — @saty-nexthop", f"- [ ] {B}"]), [A, B, C], detect)

    assert seen == [[C]]
    assert f"- [ ] {B}" in new and f"- [ ] {C} — @detected-nexthop" in new


def test_refresh_clears_an_empty_list_and_can_refill_it():
    body, _ = mod.refresh(body_with([f"- [ ] {A}"]), [A], detect_all)

    cleared, changed = mod.refresh(body, [], no_detect)
    assert changed and mod.CLEARED in cleared and mod.HEADING not in cleared and A not in cleared

    again, changed = mod.refresh(cleared, [B], detect_all)
    assert changed and mod.CLEARED not in again and mod.HEADING in again
    assert f"- [ ] {B}" in again


def test_refresh_appends_when_there_is_no_section_yet():
    """A build-failure sync PR has a body with no conflict list at all."""
    body = "This PR syncs private-fboss with upstream stable commit.\n\n:x: **Build/test failed**\n"
    assert mod.refresh(body, [], no_detect) == (body, False)  # nothing to say, nothing said

    new, changed = mod.refresh(body, [A], detect_all)
    assert changed and new.startswith(body.rstrip("\n"))
    assert f"- [ ] {A} — @detected-nexthop" in new
    assert new.endswith("\n") and "\n\n\n" not in new


def test_refresh_is_a_no_op_once_the_description_matches():
    body, _ = mod.refresh(body_with([f"- [ ] {A} — @saty-nexthop"]), [A], no_detect)
    assert mod.refresh(body, [A], no_detect) == (body, False)


@pytest.mark.parametrize(
    "line,expected",
    [
        (f"- [ ] {A} — @saty-nexthop", "saty-nexthop"),
        (f"- [x] {A} — @saty-nexthop", "saty-nexthop"),
        (f"- [ ] {A}", None),
        (f"- [ ] `{A}` — @saty-nexthop", "saty-nexthop"),
        (f"- [ ] {A} — @saty-nexthop  ", "saty-nexthop"),
    ],
)
def test_parse_owners(line, expected):
    assert mod.parse_owners([line]) == {A: expected}


def test_parse_owners_ignores_anything_that_is_not_a_checkbox():
    assert mod.parse_owners(["Failed tests (2):", "- `SomeTest`", "# heading"]) == {}


def test_script_carries_no_conflict_markers_of_its_own():
    """It works around the repo's marker checks, so it must not trip them."""
    for line in SCRIPT.read_text().splitlines():
        assert not line.startswith(("<" * 7 + " ", "=" * 7, ">" * 7 + " ")), line


FAKE_GH = """#!/usr/bin/env bash
set -euo pipefail
case "$1 $2" in
  "api repos/nexthop-ai/private-fboss/pulls/2586") cat "$SANDBOX/pr.json" ;;
  "api repos/nexthop-ai/nh/contents/.github/scripts/detect_conflict_owners.py")
    cat "$SANDBOX/detector.b64" ;;
  "pr edit")
    shift 2
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --body-file) cp "$2" "$SANDBOX/edited-body"; shift 2 ;;
        *) shift ;;
      esac
    done
    ;;
  *) echo "fake gh: unhandled: $*" >&2; exit 1 ;;
esac
"""

FAKE_DETECTOR = """#!/usr/bin/env python3
import json, os, sys
# $SANDBOX/null-owners stands for a detector whose rev is missing: all nulls.
null = os.path.exists(os.path.join(os.environ["SANDBOX"], "null-owners"))
print(json.dumps({p: (None if null else {"login": "detected-nexthop"}) for p in sys.argv[1:]}))
"""


class Sandbox:
    """A repo with markers committed, a fake gh on PATH, a fake detector."""

    def __init__(self, root: Path):
        self.root, self.repo, self.bin = root, root / "work", root / "bin"
        self.outputs, self.edited = root / "github_output", root / "edited-body"
        self.repo.mkdir()
        self.bin.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        (root / "detector.b64").write_text(base64.b64encode(FAKE_DETECTOR.encode()).decode())

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, text=True, capture_output=True
        ).stdout

    def commit(self, files: dict[str, str]) -> None:
        for name, content in files.items():
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_text(content)
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "conflicted")

    def set_body(self, body: str) -> None:
        (self.root / "pr.json").write_text(json.dumps({"body": body}))

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.outputs.write_text("")
        env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "GH_TOKEN": "x",
            "GITHUB_REPOSITORY": "nexthop-ai/private-fboss",
            "GITHUB_OUTPUT": str(self.outputs),
            "SANDBOX": str(self.root),
        }
        return subprocess.run(
            [str(SCRIPT), *args], cwd=self.repo, env=env, text=True, capture_output=True, check=check
        )

    def refresh(self, *extra: str, conflict_list: Path | None = None, check: bool = True):
        """A refresh needs the list the resync writes; by default an empty one,
        which is what a replayed merge where everything got resolved produces."""
        if conflict_list is None:
            conflict_list = self.root / "unmerged.txt"
            conflict_list.write_text("")
        return self.run("--pr", "2586", "--conflict-list", str(conflict_list), *extra, check=check)

    def out(self, key: str) -> str:
        for line in self.outputs.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
        return ""


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)


def test_e2e_refreshes_the_description(sandbox: Sandbox) -> None:
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n", "clean.cpp": "int main() {}\n"})
    sandbox.set_body(body_with([f"- [ ] {B} — @someone-nexthop"]))

    result = sandbox.refresh()

    assert result.returncode == 0, result.stderr
    body = sandbox.edited.read_text()
    assert f"- [ ] {A} — @detected-nexthop" in body
    assert B not in body and "clean.cpp" not in body
    assert sandbox.out("body_updated") == "true"


def test_e2e_leaves_a_matching_description_alone(sandbox: Sandbox) -> None:
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n"})
    matching, _ = mod.refresh(body_with([f"- [ ] {A} — @saty-nexthop"]), [A], no_detect)
    sandbox.set_body(matching)

    result = sandbox.refresh()

    assert result.returncode == 0, result.stderr
    assert not sandbox.edited.exists()
    assert sandbox.out("body_updated") == "false"


def test_e2e_lists_paths_that_never_get_markers(sandbox: Sandbox) -> None:
    """modify/delete and binary conflicts are unmerged without markers."""
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n", B: "int main() {}\n"})
    owners = sandbox.root / "owners.json"

    without = sandbox.run("--print-section")
    unmerged = sandbox.root / "unmerged.txt"
    unmerged.write_text(f"{A}\n{B}\n")
    with_ = sandbox.run("--print-section", "--conflict-list", str(unmerged), "--owners-out", str(owners))

    assert without.returncode == 0 and with_.returncode == 0, with_.stderr
    assert B not in without.stdout
    entries = [line for line in with_.stdout.splitlines() if line.startswith("- [ ]")]
    assert entries == [f"- [ ] {A} — @detected-nexthop", f"- [ ] {B} — @detected-nexthop"]
    assert json.loads(owners.read_text()) == dict.fromkeys([A, B], "detected-nexthop")


def test_e2e_survives_an_unavailable_detector(sandbox: Sandbox) -> None:
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n"})
    (sandbox.root / "detector.b64").unlink()

    result = sandbox.run("--print-section")

    assert result.returncode == 0, result.stderr
    assert f"- [ ] {A}\n" in result.stdout and "@" not in result.stdout
    assert "could not guess conflict owners" in result.stderr


def test_e2e_says_so_when_no_owner_can_be_guessed(sandbox: Sandbox) -> None:
    """An ownerless list is a symptom (usually a missing origin/main in the
    checkout), so it must not look like a normal render."""
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n"})
    (sandbox.root / "null-owners").touch()

    result = sandbox.run("--print-section")

    assert result.returncode == 0, result.stderr
    assert f"- [ ] {A}\n" in result.stdout
    assert "found no owner for any of the" in result.stderr


def test_owners_out_requires_print_section(sandbox: Sandbox) -> None:
    result = sandbox.run("--pr", "2586", "--owners-out", "/tmp/nope.json", check=False)

    assert result.returncode == 2
    assert "--owners-out requires --print-section" in result.stderr


def test_print_section_is_the_only_mode_without_a_pr(sandbox: Sandbox) -> None:
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n"})

    result = sandbox.run(check=False)

    assert result.returncode == 2
    assert "--pr is required unless --print-section is given" in result.stderr


def test_e2e_a_resync_that_had_nothing_to_do_leaves_the_description_alone(sandbox: Sandbox) -> None:
    """The no-op /resync never writes the list file, so the refresh must not run.

    Without it the set of files is unknowable -- a modify/delete conflict has no
    markers -- so rewriting the section would drop entries and wipe the ticks of
    work already done.
    """
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n", B: "int main() {}\n"})
    sandbox.set_body(body_with([f"- [x] {A} — @saty-nexthop", f"- [ ] {B} — @abh-nexthop"]))

    noop = sandbox.refresh(conflict_list=sandbox.root / "never-written.txt")

    assert noop.returncode == 0, noop.stderr
    assert not sandbox.edited.exists()
    assert sandbox.out("body_updated") == "false"
    assert "no conflict list was produced" in noop.stdout + noop.stderr


def test_e2e_an_empty_list_from_a_replay_is_authoritative(sandbox: Sandbox) -> None:
    """A merge was replayed and nothing survived it: the list is complete, so an
    entry that no longer has markers and is not unmerged does drop off."""
    sandbox.commit({A: f"one\n{MARKER}\ntwo\n", B: "int main() {}\n"})
    sandbox.set_body(body_with([f"- [ ] {A} — @saty-nexthop", f"- [ ] {B} — @abh-nexthop"]))
    result = sandbox.refresh()

    assert result.returncode == 0, result.stderr
    assert B not in sandbox.edited.read_text()
    assert sandbox.out("body_updated") == "true"
