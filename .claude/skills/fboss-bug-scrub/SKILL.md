---
name: fboss-bug-scrub
title: FBOSS CLI Bug Scrub
description: Load when the user wants to scrub, triage, or rank the open FBOSS CLI Jira backlog — "bug scrub", "which FBOSS CLI bugs should we work on this week", "rank the stars-ai-triage-auto heavy hitters", "refresh the triage spreadsheet". Skip for triaging one failure (stars-triage), Jira CRUD (jira-expert), or QPN dashboard questions (qpn).
---

# FBOSS CLI Bug Scrub

Produces a ranked CSV (and optionally a Google Sheet) of open FBOSS CLI bugs
from four Jira sources, for a shallow first pass the team then edits by hand.
Goal: the top 10 are what to work on this week; the long tail is labeled so it
can be closed WONTFIX if it stays quiet. Do not root-cause every ticket.

## Sources

| Cat | Where | Include? |
|---|---|---|
| 1 | Epic NOS-346 — Project Mosaic CLI loose ends | yes |
| 2 | Epic NOS-7785 — "FBOSS Problems" (not CLI-specific) | yes, flag CLI vs not |
| 3 | Epic NOS-5388 — "FBOSS is not a NOS" (won't fix) | **no** — pull only to check nothing leaks in |
| 4 | STARS auto-triage tickets hit by FBOSS `package=cli` tests | yes, heavy hitters first |

Status filter for everything: `status in (New, Reopened, Backlog)`.

## Run it

```bash
export no_proxy=127.0.0.1,localhost,.internal.nexthop.ai,.nexthop.ai
OUT=$(mktemp -d)
fboss/.claude/skills/fboss-bug-scrub/scripts/fetch.sh "$OUT"      # Jira via acli + QPN via curl
# write $OUT/notes.json ({key: note}) and $OUT/order.json ([keys, best first]) — see Ranking
python3 fboss/.claude/skills/fboss-bug-scrub/scripts/build_csv.py "$OUT"   # -> $OUT/fboss_cli_bug_scrub.csv
```

`fetch.sh` needs `acli` authenticated (`acli jira auth status`) and reachability
to `qpn.sw.internal.nexthop.ai`. It writes `j1.json j2.json j3.json`
(epic children), `j4all.json` (all open `stars-ai-triage-auto`), `top{7,30,90}.json`
(QPN heavy hitters), `cat4.keys`, and `meta/<KEY>.json` (created/components/parent).

## Category 4 is defined by QPN, not by the label

`https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs?os=fboss&package=cli&days=90&source=t_recs&limit=200`
is the authority for "hit by CLI tests": it gives `hit_count`, `unique_tests`,
`unique_testbeds`, `trend`, `first_seen/last_seen` and the Jira status. Cat 4 =
(open STARS tickets ∩ QPN 90d) ∪ (open STARS tickets whose description mentions
`fboss2` or `cli/fboss2`). Then **add any QPN ticket with status New/Reopened
that the label query missed** — real heavy hitters have shown up with the label
`stars-ai-triage` (no `-auto`) or no label at all (NOS-15884, NOS-14705 in Sept 2026).
QPN tickets whose status is Done/WONTFIX/Blocked/In Review are excluded by the
status rule; mention them to the user as a watch list rather than dropping silently.

Agent/led_service crashes that are not CLI code still count: if STARS filed the
failure under `package=cli` it hurts the CLI pass rate, which is the metric.

## Ranking (what `order.json` should encode)

1. Heavy hitters by **7-day** hits, worsening trend first. 30/90-day columns
   are for spotting tickets that were loud in the past month and silent this
   week — rank those mid-list with a "verify fixed, then close" note, don't drop them.
2. Config-session correctness (commit/rollback/reload) and CLI-triggered agent
   crashes — Mosaic-visible, usually P2, often assigned to the CLI team.
3. CLI validation gaps (accepts values the platform lacks, misleading errors) and
   operator-visible wrong output (`show ...` empty/zero).
4. Remaining STARS tickets by hits; then cat 2 CLI-related by priority; then cat 2
   non-CLI by priority (BMC/uBOOT/SAI/rackmon — note "out of scope").
5. Cat 1 spec commands ("Implement fboss2 config …", ~95 of them) last: feature
   gaps, not bugs. FSW/RSW-labeled first. Note says confirm with the requester
   whether still needed before Mosaic closes.

Group siblings in notes (same test, same crash family, e.g. uncaught
`SaiApiError` on the oper-delta thread) so one fix is recognised as closing several.

Notes column: 1–3 sentences, why it matters or doesn't. Long tail default is
generated: "opened N weeks ago, H hits in 90d; candidate for WONTFIX if quiet."
Only hand-write notes for roughly the top 60; `build_csv.py` fills the rest.

## Upload to Google Sheets

`gws` prints a keyring line before JSON — always `| tail -n +2`. Write the whole
grid in one call; `USER_ENTERED` is required for the `HYPERLINK` Jira links:

```bash
gws sheets spreadsheets values update \
  --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"triage!A1\",\"valueInputOption\":\"USER_ENTERED\"}" \
  --json "$(cat $OUT/body.json)" 2>&1 | tail -n +2
```

`build_csv.py` also emits `body.json` (CSV as `{"values": [...]}` with the
Jira ID turned into a `HYPERLINK` formula). Freeze/bold row 1, wrap columns
Title/Notes and add a basic filter with one `spreadsheets batchUpdate`
(sheetId from `spreadsheets get`). Check the sheet is empty first with a
`values get`; never overwrite a sheet the team has edited without asking.

## Gotchas

- **acli `workitem search --fields` only accepts** `key,summary,status,priority,
  reporter,assignee,labels,description` (+issuetype). `created`, `components`,
  `parent`, custom fields → one `workitem view KEY --fields ... --json` per ticket
  (`fetch.sh` does this with `xargs -P 8`).
- acli JQL has no `childIssuesOf()`. Epic children here are all direct
  `parent = NOS-xxx`; that matched the MCP `childIssuesOf` count exactly.
- The Atlassian MCP `searchJiraIssuesUsingJql` result overflows the tool limit
  above ~40 issues and its `nextPageToken` expires within a minute. Use acli.
- Descriptions come back as ADF JSON. Flatten with
  `jq '[.. | .text? // empty] | join(" ")'`; STARS descriptions start with a
  `Summary` paragraph that is enough for a note.
- Jira "NOS" custom field (`customfield_10388`) is FBOSS on most STARS tickets but
  not all — don't filter on it.
- STARS ticket titles name the test; the crash is in the summary text. Two
  tickets on the same test (e.g. NOS-16533 / NOS-16529) are often first and
  second crash of one incident.
