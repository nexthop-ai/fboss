#!/usr/bin/env python3
"""Render or refresh the conflict checklist in an upstream-sync PR's description.

One renderer, two callers: `sync-upstream.yml` renders the section with
`--print-section` when it opens a sync PR, and `/resync` refreshes it in place
with `--pr`. The file list is the working tree's conflict markers plus anything
the caller passes with `--conflict-list`, because git leaves modify/delete and
binary conflicts unmerged without ever writing markers into them. `--pr` mode
therefore requires the resync's list file, which is only written once a merge
has been replayed: without it the description is left alone. Owner guesses
come from nh's detect_conflict_owners.py and are optional: failing to guess one
lists the file without an owner and warns.

  update-sync-pr-body.py --print-section [--conflict-list FILE] [--owners-out FILE]
  update-sync-pr-body.py --pr 2586 [--dry-run]

Run the unit tests with:
  python3 -m pytest .github/scripts/tests/test_update_sync_pr_body.py
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "nexthop-ai/private-fboss")
DETECTOR_REPO = "nexthop-ai/nh"
DETECTOR_PATH = ".github/scripts/detect_conflict_owners.py"

# Markers bracketing the section this script owns. They render as nothing, so
# the description still reads as prose for humans, but the rewrite is anchored
# rather than guessed on every run after the first.
START_MARKER = "<!-- resync-conflict-list:start -->"
END_MARKER = "<!-- resync-conflict-list:end -->"

# The section sync-upstream.yml writes when it opens a sync PR. Keep the two in
# sync: find_section() falls back to these strings for descriptions written
# before the markers existed (and for the build-failure PR variant).
HEADING = "⚠️ **Manual conflict resolution required**"
ANCHOR = "The following files have conflicts that need to be resolved:"
CLEARED = "✅ **No conflicts remain** — nothing in this branch still needs manual resolution."

ENTRY_RE = re.compile(r"^- \[[ xX]\] (?P<item>.+)$")

# Anchor regex for a merge-conflict marker line, spelled so that this file
# doesn't itself trip the repo's "no merge markers" pre-commit hook and the
# build-and-test grep (which flags any line with four or more '<').
MARKER_RE = "^<{7} "


def info(msg: str) -> None:
    print(f"💡 INFO:  {msg}")


def warn(msg: str) -> None:
    print(f"⚠️  WARN:  {msg}", file=sys.stderr)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def failure(exc: subprocess.CalledProcessError) -> str:
    """Human-readable reason for a failed subprocess (stderr first)."""
    detail = (exc.stderr or exc.stdout or "").strip()
    return f"{' '.join(exc.cmd)} exited {exc.returncode}" + (f": {detail}" if detail else "")


# ─── The branch's conflict set ────────────────────────────────────────────────


def conflicted_files() -> list[str]:
    """Every tracked file in the working tree that still has conflict markers."""
    try:
        # Exit code 1 just means "no match": that is the clean branch case.
        out = run(["git", "grep", "-lI", "-E", MARKER_RE, "--", ":/"]).stdout
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 1:
            raise
        return []
    return sorted(path for path in out.splitlines() if path)


# ─── Rewriting the description ────────────────────────────────────────────────


def trim_end(lines: list[str], start: int, end: int) -> int:
    """Drop trailing blank lines from a span; the renderer re-emits the gap."""
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return end


def find_section(lines: list[str]) -> tuple[int, int] | None:
    """Line span of the conflict section in a PR description, or None.

    Marker-delimited bodies (written by this script) are found exactly. Bodies
    from create-pr have no markers, so they are found by the heading/anchor
    text and end after the checklist that follows it.
    """
    for i, line in enumerate(lines):
        if line.strip() != START_MARKER:
            continue
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == END_MARKER:
                return i, trim_end(lines, i, j + 1)
        # Unterminated marker: the section runs to the end of the body.
        return i, trim_end(lines, i, len(lines))

    start = next(
        (i for i, line in enumerate(lines) if line.strip() in (HEADING, ANCHOR)),
        None,
    )
    if start is None:
        return None
    for j in range(start, len(lines)):
        stripped = lines[j].strip()
        if stripped == "" or stripped in (HEADING, ANCHOR) or ENTRY_RE.match(stripped):
            continue
        return start, trim_end(lines, start, j)
    return start, trim_end(lines, start, len(lines))


def parse_owners(lines: list[str]) -> dict[str, str | None]:
    """`{path: owner or None}` for every checklist entry in a description."""
    owners: dict[str, str | None] = {}
    for line in lines:
        match = ENTRY_RE.match(line.strip())
        if not match:
            continue
        # create-pr writes "- [ ] <path>" with an optional " — @owner" suffix.
        path, _, annotation = match.group("item").partition(" — ")
        annotation = annotation.strip()
        owners[path.strip().strip("`")] = (
            annotation[1:].strip() if annotation.startswith("@") else None
        )
    return owners


def render_section(paths: list[str], owners: dict[str, str | None]) -> list[str]:
    """The section this script owns, as lines (no trailing blank line)."""
    if not paths:
        return [START_MARKER, "", CLEARED, "", END_MARKER]

    lines = [START_MARKER, "", HEADING, "", ANCHOR]
    for path in paths:
        owner = owners.get(path)
        lines.append(f"- [ ] {path}" + (f" — @{owner}" if owner else ""))
    return [*lines, "", END_MARKER]


def refresh(
    body: str,
    paths: list[str],
    detect: Callable[[list[str]], dict[str, str | None]],
) -> tuple[str, bool]:
    """Rebuild the description's conflict section; report whether it changed.

    `paths` must be the complete set of files still needing a manual decision --
    markers alone are not enough, since git leaves modify/delete and binary
    conflicts unmerged without writing markers into them. `detect` maps a list
    of paths to owner guesses, and is injected so the rewrite can be tested
    without git, gh, or the network.
    """
    lines = body.split("\n")
    span = find_section(lines)
    if span is None and not paths:
        # Nothing to say and nothing was said before: leave the body alone.
        return body, False

    known = parse_owners(lines)
    # A file already listed keeps whatever the description says about it,
    # including "no owner": create-pr's annotations come from a detector run the
    # resync workflow can't see, and re-guessing would only repeat that work.
    owners = {path: known[path] for path in paths if path in known}
    missing = [path for path in paths if path not in known]
    if missing:
        owners.update(detect(missing))

    section = render_section(paths, owners)
    if span is None:
        # A description with no section yet (a build-failure sync PR): append.
        end_of_body = len(lines)
        while end_of_body and lines[end_of_body - 1].strip() == "":
            end_of_body -= 1
        new_lines = [*lines[:end_of_body], "", *section, ""]
    else:
        start, end = span
        new_lines = [*lines[:start], *section, *lines[end:]]

    new_body = "\n".join(new_lines)
    return new_body, new_body != body


# ─── Owner detection (nh's detector, same source as sync_upstream.sh) ─────────


def fetch_detector() -> str:
    """Materialize nh's conflict-owner detector and return its path."""
    content = run(
        ["gh", "api", f"repos/{DETECTOR_REPO}/contents/{DETECTOR_PATH}", "--jq", ".content"]
    ).stdout
    fd, script = tempfile.mkstemp(suffix=".py", prefix="detect-conflict-owners-")
    try:
        with os.fdopen(fd, "wb") as fh:
            # b64decode ignores the newlines gh wraps the payload at.
            fh.write(base64.b64decode(content))
        os.chmod(script, 0o755)
    except (OSError, ValueError):
        # The caller never learns the path if we raise before returning it.
        os.unlink(script)
        raise
    return script


def detect_owners(paths: list[str]) -> dict[str, str | None]:
    """Guess an owner per path; {} if the detector can't be used or fails."""
    if not paths:
        return {}

    script = None
    try:
        script = fetch_detector()
        data = json.loads(run([sys.executable, script, *paths]).stdout)
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        detail = failure(exc) if isinstance(exc, subprocess.CalledProcessError) else exc
        warn(f"could not guess conflict owners via {DETECTOR_PATH}: {detail}")
        return {}
    finally:
        if script:
            os.unlink(script)

    owners = {
        path: owner["login"]
        for path, guess in data.items()
        if isinstance(owner := guess or {}, dict) and owner.get("login")
    }
    if paths and not owners:
        # Every path coming back empty means the detector could not blame
        # anything -- typically its origin/main rev is missing from the
        # checkout. Say so instead of rendering an ownerless list in silence.
        warn(
            f"{DETECTOR_PATH} found no owner for any of the {len(paths)} conflicted "
            "file(s); check that origin/main resolves in this checkout"
        )
    return owners


def read_path_list(path: str) -> list[str]:
    """Paths from a file, one per line, blanks and duplicates dropped."""
    with open(path, encoding="utf-8") as fh:
        return sorted({line.strip() for line in fh if line.strip()})


def write_owners(path: str, paths: list[str], owners: dict[str, str | None]) -> None:
    """Record the owner guessed for each path (null when none) for the caller."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({path_: owners.get(path_) for path_ in paths}, fh, indent=2)
        fh.write("\n")


# ─── GitHub plumbing ──────────────────────────────────────────────────────────


def get_body(pr: str) -> str:
    """The PR description exactly as stored (no jq newline to strip)."""
    return json.loads(run(["gh", "api", f"repos/{REPO}/pulls/{pr}"]).stdout)["body"] or ""


def set_body(pr: str, body: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(body)
        path = fh.name
    try:
        run(["gh", "pr", "edit", pr, "--repo", REPO, "--body-file", path])
    finally:
        os.unlink(path)


def set_output(name: str, value: str) -> None:
    """Publish a step output when running under GitHub Actions."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pr", help="PR number to update (needs --print-section to be omitted)")
    parser.add_argument("--print-section", action="store_true", help="print the section, don't touch a PR")
    parser.add_argument(
        "--conflict-list", help="file of unmerged paths to list as well (they never get markers)"
    )
    parser.add_argument("--owners-out", help="with --print-section: write the owners guessed as JSON")
    parser.add_argument("--dry-run", action="store_true", help="print the new description instead of editing")
    args = parser.parse_args()

    if args.owners_out and not args.print_section:
        parser.error("--owners-out requires --print-section")

    if not args.pr and not args.print_section:
        parser.error("--pr is required unless --print-section is given")

    # The resync writes the list only once it has replayed a merge, so its
    # presence is what says the set is complete. Without one (a /resync that had
    # nothing to rebase) there is nothing to compare the description against,
    # and refreshing it would drop the entries no grep can see.
    if not args.print_section and (
        not args.conflict_list or not Path(args.conflict_list).exists()
    ):
        info(f"PR #{args.pr}: no conflict list was produced; leaving the description alone")
        set_output("body_updated", "false")
        return 0

    paths = conflicted_files()
    if args.conflict_list:
        paths = sorted({*paths, *read_path_list(args.conflict_list)})

    if args.print_section:
        owners = detect_owners(paths)
        if args.owners_out:
            write_owners(args.owners_out, paths, owners)
        print("\n".join(render_section(paths, owners)))
        return 0

    body = get_body(args.pr)
    new_body, changed = refresh(body, paths, detect_owners)

    if not changed:
        info(
            f"PR #{args.pr}: description already lists the {len(paths)} conflicted file(s); "
            "nothing to update"
        )
        set_output("body_updated", "false")
        return 0

    if args.dry_run:
        print(new_body)
        return 0

    set_body(args.pr, new_body)
    set_output("body_updated", "true")
    if paths:
        info(f"PR #{args.pr}: description updated with {len(paths)} conflicted file(s)")
    else:
        info(f"PR #{args.pr}: no conflicts remain — description cleared")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (subprocess.CalledProcessError, KeyError, OSError, ValueError) as exc:
        reason = failure(exc) if isinstance(exc, subprocess.CalledProcessError) else exc
        warn(f"failed to refresh the PR description: {reason}")
        sys.exit(1)
