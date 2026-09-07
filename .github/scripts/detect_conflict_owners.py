#!/usr/bin/env python3
"""Guess an owner for each conflicted file of an upstream sync merge.

For each file given on the command line (its working-tree copy still
containing conflict markers), blame the ours-side lines of every conflict
region and pick the Nexthop author who owns the most of them — skipping bots
and sync/merge/conflict-resolution commits, whose authors resolved a past
conflict rather than wrote the code. When region blame yields nothing (our
side of the conflict is empty, the file has no history on our main, or every
blamed line is noise), fall back to the file-level walk: the most recent
"real" Nexthop author in the file's history.

Prints a single-line JSON object on stdout:

    {"path/to/file": {"email": ..., "name": ..., "login": ...} | null, ...}

`login` is derived from the email local part + "-nexthop", the convention for
Nexthop GitHub accounts. Files with no plausible owner map to null.

--rev selects the commit blamed as "our side" (default origin/main, which is
what the sync branch is cut from).
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter

# Sync merges, conflict-resolution commits, and automation. Matching a real
# feature commit here only costs falling back to the next author in history.
NOISE_SUBJECT = re.compile(
    r"^(Merge |Sync with upstream|\[sync\]|fix \S+$|resolve )|conflict",
    re.IGNORECASE,
)
BOT_EMAILS = {"rabbit@nexthop.ai"}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def is_real_author(email: str, subject: str) -> bool:
    return (
        email not in BOT_EMAILS
        and "[bot]" not in email
        and email.endswith("@nexthop.ai")
        and not NOISE_SUBJECT.search(subject)
    )


def as_owner(email: str, name: str) -> dict:
    return {"email": email, "name": name,
            "login": email.split("@", 1)[0] + "-nexthop"}


def ours_chunks(path: str) -> list[list[str]]:
    """Ours-side line blocks of each conflict region in the working copy."""
    chunks, current = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("<<<<<<< "):
                current = []
            elif current is not None and (
                line.startswith("||||||| ") or line.startswith("=======")
            ):
                chunks.append(current)
                current = None
            elif current is not None:
                current.append(line.rstrip("\n"))
    return [c for c in chunks if c]


def find_chunk(haystack: list[str], chunk: list[str]) -> tuple[int, int] | None:
    """1-based (start, end) of chunk inside haystack, or None."""
    n = len(chunk)
    for i in range(len(haystack) - n + 1):
        if haystack[i:i + n] == chunk:
            return i + 1, i + n
    return None


def blame_owner(path: str, rev: str) -> dict | None:
    """Owner of the most ours-side conflicted lines, by region blame."""
    try:
        ours = git("show", f"{rev}:{path}").splitlines()
    except subprocess.CalledProcessError:
        return None  # file absent on our side
    counts: Counter[tuple[str, str]] = Counter()
    for chunk in ours_chunks(path):
        span = find_chunk(ours, chunk)
        if span is None:
            continue
        porcelain = git("blame", "--line-porcelain",
                        "-L", f"{span[0]},{span[1]}", rev, "--", path)
        email = name = subject = ""
        for line in porcelain.splitlines():
            if line.startswith("author "):
                name = line[len("author "):]
            elif line.startswith("author-mail "):
                email = line[len("author-mail "):].strip("<>")
            elif line.startswith("summary "):
                subject = line[len("summary "):]
            elif line.startswith("\t"):  # the blamed line itself ends a group
                if is_real_author(email, subject):
                    counts[(email, name)] += 1
    if not counts:
        return None
    (email, name), _ = counts.most_common(1)[0]
    return as_owner(email, name)


def history_owner(path: str, rev: str) -> dict | None:
    """Fallback: most recent real Nexthop author in the file's history."""
    log = git("log", "-n", "50", "--format=%ae\x1f%an\x1f%s", rev, "--", path)
    for line in log.splitlines():
        email, name, subject = line.split("\x1f", 2)
        if is_real_author(email, subject):
            return as_owner(email, name)
    return None


def guess_owner(path: str, rev: str) -> dict | None:
    try:
        return blame_owner(path, rev) or history_owner(path, rev)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"warning: {path}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rev", default="origin/main",
                        help="commit blamed as our side (default: origin/main)")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    print(json.dumps({p: guess_owner(p, args.rev) for p in args.files}))


if __name__ == "__main__":
    main()
