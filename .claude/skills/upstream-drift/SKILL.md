---
name: upstream-drift
title: Upstream Drift Audit
description: Load when the user wants to know what a directory of this fork (fboss/cli/fboss2, fboss/agent, any --scope) carries that facebook/fboss doesn't, and whether each feature should be upstreamed, kept private, or deleted because upstream has an equivalent — "upstream drift", "what should we upstream", "what can we delete vs upstream", "fork divergence audit", "why does this dir conflict every sync". Skip for sending one PR upstream (upstream-pr) or rebasing an existing upstream PR (rebase-upstream-pr workflow).
metadata:
  argument-hint: '--scope <path> [--grouping auto|dir|cli] [--depth 2] [--base origin/main]'
---

# Upstream Drift Audit

Answers, per feature group under any `--scope`: is our version `UPSTREAM` / `KEEP` / `DROP` / `SPLIT` /
`UNSURE`, with effort and benefit, from a three-way diff against the merge-base. Git does the
*who changed what*; Claude does the *what should we do*. GitHub supplies current open-PR metadata and diffs.

## 1. Collect (script, ~20 s)

```bash
cd "$(git rev-parse --show-toplevel)"
git fetch --multiple upstream origin
OUT=$(mktemp -d)
python3 .claude/skills/upstream-drift/scripts/drift.py --scope fboss/cli/fboss2 --out "$OUT"   # any path; --base to override
```
Prints `{"merge_base","OURS","BOTH","THEIRS","groups"}` and writes:

- `index.json` — per-group stats + file lists
- `groups/<group>.md` — packet header: stats, files tagged `OURS|BOTH` + our `A|M|D`, upstream
  commits since merge-base, files upstream added in the same dirs, **Upstream today** (identifiers
  we introduced and where they already exist on `upstream/main`, whole tree)
- `groups/<group>.partN.md` — complete diffs, split on file boundaries at ~1500 lines:
  *Our change* (merge-base → ours) and *Upstream change on BOTH files* (merge-base → upstream)
- `report.md` — skeleton, verdict columns empty

Tags: `OURS` = only we changed it since merge-base · `BOTH` = both sides · `THEIRS` = only upstream
(pending merge — **not drift**, listed but never judged).

`index.json` records `grouping`/`depth`, so render and the validators regroup exactly the same way.

## 2. Judge + notes (Claude, parallel)

Split `index.json` groups into ~4 batches by size. For each batch dispatch one subagent
(`superpowers:dispatching-parallel-agents`) with the contents of
`.claude/skills/upstream-drift/JUDGE_PROMPT.md`, telling it OUT, BATCH letter and the group list.
It reads every packet's **Gap today** parts and the **Open upstream PRs** header, decides
`SUBMITTED | UPSTREAM | KEEP | DROP | SPLIT | UNSURE` + effort/benefit, and writes
`OUT/.judge_<BATCH>.jsonl` (one JSON line per group with `do`, `notes`, `evidence`, `open_prs`).

Merge every batch: `python3 .claude/skills/upstream-drift/scripts/merge_verdicts.py "$OUT" < "$OUT/.judge_A.jsonl"`
(verifies each evidence quote exists in a packet; prints X/Y per group).

## 3. Render, then validate

```bash
python3 .claude/skills/upstream-drift/scripts/drift.py --render --out "$OUT"
python3 .claude/skills/upstream-drift/scripts/verify_report.py   "$OUT"   # claims vs git/GitHub
python3 .claude/skills/upstream-drift/scripts/validate_report.py "$OUT"   # the rendered report vs git
```

`validate_report.py` is the mandatory last step and the only check that reads the artifact people
actually share. It re-derives groups, tags, counts and gap sizes from git and compares the report to
that — it assumes nothing from `index.json`. Its `coverage` check is the important one: a SUBMITTED
verdict fails unless the cited PRs' **added lines** contain the symbols our diff adds. Filename
overlap is not coverage; that mistake produced wrong verdicts before this check existed. Both
scripts exit non-zero on any problem, so they can gate CI.

`report.md` rows are sorted by benefit and effort. Hand the user the report path plus the top five rows.

## Running it again later

Every collection is a fresh audit. GitHub metadata and cited PR diffs are fetched again by collection,
judgement merging and validation; no responses are read from or written to a disk cache. GitHub
failures stop the operation instead of being treated as an empty list of PRs.

Use a new `--out` directory to retain previous reports. Reusing a directory replaces the inventory
and clears its verdicts, so **all groups must be judged again**, even if their Git diff is unchanged.
Rendering and merging batches within that audit still read its saved `index.json` and `verdicts.json`.
The `gap_hash` and judged revisions record the evidence used for the current judgement; they are
validation metadata, not a reason to carry a verdict into a later audit. Legacy `cache/` files are ignored.

## Gotchas

- `--no-renames` is deliberate: git's similarity guess pairs unrelated files
  (`platform_mapping.json => ...PlatformMapping.h`) and `{a => b}` paths break grouping.
- Local `upstream` remote may be shallow; only `merge-base..upstream/main` history is used, so that
  is fine. "Upstream today" greps the *tree*, not history, so older upstream equivalents still show.
- Grouping (`--grouping`, default `auto`):
  - `dir` — the file's directory, cut to `--depth` levels below scope (default 2: `fboss/agent/hw/sai/api/X.h`
    -> `hw/sai`). Files directly in scope -> `root`. Used for every scope except the CLI.
  - `cli` — auto-selected for `fboss/cli/fboss2`. Groups are features, not verbs: `commands/config/acl` +
    `commands/delete/acl` -> `acl`; `protocol/<name>` is one level deeper; `show/*` keeps its verb.
  - Either way, a file under a `test/` or `tests/` dir joins the group of the in-scope header it `#include`s
    (the one it is named after, `FooTest.cpp` -> `Foo.h`, else the most specific). Unmatched tests fall back
    to the normal rule (`test/<dir>` under `cli`). `scripts/test_drift.py` guards this mapping.
  - Too many tiny groups -> lower `--depth`; one giant group -> raise it or narrow `--scope`.
- Our-side `D` files are judged too — e.g. the BGP per-attribute files we collapsed; the replacement
  is in the same packet.
- Widening scope: whole-repo drift is ~2300 files, dominated by generated platform-mapping data
  (`fboss/lib`, `fboss/agent/platforms`) and our build harness (`.github`, `fboss/oss`). Run
  per-area with `--scope` and treat generated/data dirs as inventory-only (judge by filename, don't read).
- Packets are redacted before they are written, so verdict text can be pasted into a public PR. The pattern
  is org-specific: pass `--redact '<regex>'` (default covers this repo's DUT and host names). Check with
  `grep -nE '<your host pattern>' "$OUT"/groups/*.md` — it must print nothing.
- Repos are derived from git remotes, not hardcoded: the upstream repo comes from the `--upstream` remote and
  the public fork is `<owner of the --base remote>/<upstream repo name>`. Override with `--repo` / `--fork`
  (and `--internal-repo` on `verify_report.py`) in a differently-shaped fork.
