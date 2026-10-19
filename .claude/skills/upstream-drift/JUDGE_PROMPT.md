Task: judge drift groups and write report notes. Read-only. You are given OUT (a directory), BATCH (a letter) and a list of groups.

For group G open OUT/groups/<G with "/" replaced by "__">.md and EVERY linked .partN.md it lists at the bottom. The part titled "Gap today (upstream -> ours; what still differs)" is the current two-way diff: your primary source. "Our change" and "Upstream change" show how each side got there. The header section "Open upstream PRs touching these files" lists PRs from nexthop-ai/fboss already open against facebook/fboss and how many of this group's files each touches.

Context: this repo is a private fork of an upstream open-source repo (the packet header names both). Files are tagged OURS (only we changed since merge-base) or BOTH (both sides changed); our A/M/D is relative to the merge-base.

Decide, in this order:
1. Is the drift in this group already inside an open upstream PR? The packet header lists PRs that TOUCH these files — that is a hint, never proof. Before writing SUBMITTED you MUST read the PR's actual diff (`gh pr diff <N> --repo <upstream repo>`) and confirm it ADDS the code our gap diff adds. A PR that edits the same file for an unrelated reason covers nothing.
   - every symbol our gap diff introduces (class, function, test fixture, CLI token, config key) must appear in the PR's added lines, or be named in your notes as a leftover
   - verdict = SUBMITTED only when the PRs carry the whole change; otherwise SPLIT, and list exactly what is still unsubmitted
   - never promise "the diff disappears when it lands" unless you checked every hunk
2. Otherwise: UPSTREAM (generic, send it), KEEP (internal-only: name the internal dependency — platform, service, lab host, policy), DROP (upstream has an equivalent: name the upstream file/commit, compare behavior, give a validation step; missing any -> UNSURE), SPLIT (mixed: name each part and its action), UNSURE (say what a human checks).
- A commit merely touching the same files is a clue, not proof. Never judge THEIRS files.
- effort S/M/L = how hard to send/rebase/delete cleanly. benefit S/M/L = recurring merge pain removed (BOTH files conflict every sync).

Output ONE JSON line per group:
{"group": "...", "verdict": "SUBMITTED|UPSTREAM|KEEP|DROP|SPLIT|UNSURE", "effort": "S|M|L", "benefit": "S|M|L",
 "open_prs": ["1559", ...], "do": "<one plain line: the action>",
 "notes": "<markdown>", "evidence": ["<verbatim line from a packet or part file>", ...]}

notes format. Written for an engineer who has never seen this code and has 10 minutes. Plain English, short lines, no jargon like "superset"/"line-for-line", no arrows. Use exactly these headings:

**What this is:** one sentence: which feature (CLI command, agent component, library, ...) / files, and what we did to them.

**Already upstream?** `#NNNN <title>` for each open PR that covers these files, saying which files it covers; or "No open PR".

**What differs (ours vs upstream):** numbered, one line each: `file` — ours does X, upstream does Y. (behavior|cosmetic). Merge identical mechanical edits into one line.

**Steps:** numbered checklist someone can execute top to bottom. Every step starts with a verb and names the exact file(s), PR number, or command. Use real commands where they apply, e.g.
  - `git checkout upstream/main -- <path from the packet>`  (take upstream's copy)
  - `git rm <path from the packet>`  (delete ours)
  - `gh pr view <N> --repo <upstream repo>` / "rebase #1559 onto upstream/main via the rebase-upstream-pr workflow"
  - "open upstream PR with files: a, b, c (use the upstream-pr skill on internal PR #N if known)"
  - `./fboss/oss/scripts/bazel.sh test --test_output=errors //<package>:<target> --test_filter='<Suite>*'`  (only targets that exist in that package's BUCK; the verifier checks)
  For SPLIT, the steps list each part in order: first what to drop, then what to rebase/chase, then what to send new.
  For SUBMITTED: step 1 is the PR to chase, step 2 is what to do locally when it lands.
  For KEEP: one step: "nothing; leave as is" plus why in five words.

  Use a ```diff fence ONLY for lines that already exist somewhere real (the gap diff, a PR diff, or a file
  as it stands today) — the validator checks every one of them. For an edit you are PROPOSING that does not
  exist yet (a line to add to BUCK, a reordering), use a ```suggestion fence instead; it is exempt.
  Every step that changes code shows the change: quote the relevant hunk from the Gap-today diff in a ```diff block (at most ~8 lines, the `-`/`+` lines that matter, `...` to elide), or for a whole-file take/delete say "whole file, N lines" and name the function(s) it holds. The reader must see what they are deleting or keeping without opening the diff. If a step is "take upstream's file", show the 2-3 lines that will change as a result.

**Check first:** one concrete verification before step 1, or "nothing".

Name commits as `abc1234 (#NNNN)` when the packet shows them. A bare `#NNNN` always means a PR in the UPSTREAM repo; when you mean one in this internal repo write `internal PR #NNNN`. Every file/commit/identifier/evidence string must appear verbatim in a packet or part file. Do not invent files, PRs or commands that the packet does not support.

WRITE the JSON lines to OUT/.judge_<BATCH>.jsonl with the Write tool (one line per group, no code fences), then reply with only the line count.
