---
name: fboss-bug-scrub
title: FBOSS CLI Bug Scrub
description: Load when the user wants to scrub, triage, or rank the open FBOSS CLI Jira backlog — "bug scrub", "which FBOSS CLI bugs should we work on this week", "rank the stars-ai-triage-auto heavy hitters", "refresh the triage spreadsheet". Skip for triaging one failure (stars-triage), Jira CRUD (jira-expert), or QPN dashboard questions (qpn).
---

# FBOSS CLI Bug Scrub

Produces a ranked CSV of open FBOSS CLI bugs from four Jira sources and writes it
to the FBOSS CLI Jira triage Google Sheet (mandatory every run), for a shallow
first pass the team then edits by hand.
Goal: the top 10 are what to work on this week; the long tail is labeled so it
can be closed WONTFIX if it stays quiet. Do not root-cause every ticket.

## Configuration

Fixed per-run inputs — no need to look them up again.

| What | Value |
|---|---|
| Triage spreadsheet | `1H8FpXlmZm2ABpr2kKCg_0Ji4n6RiujrXg4ztrBGmLMc` ("FBOSS CLI Jira triage") |
| Tab / sheetId | `triage` / `1684313274` |
| Frozen snapshots | `sept7` `sept16` `sept23` — history, never write to them |

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
python3 fboss/.claude/skills/fboss-bug-scrub/scripts/fixcheck.py "$OUT"   # -> $OUT/fixcheck.csv
# then, always: update the triage tab (see below) and report the watch list
```

`fetch.sh` needs `acli` authenticated (`acli jira auth status`) and reachability
to `qpn.sw.internal.nexthop.ai`; `fixcheck.py` additionally needs `gh`
authenticated against `nexthop-ai/private-fboss`. It writes `j1.json j2.json j3.json`
(epic children), `j4all.json` (all open `stars-ai-triage-auto`), `top{7,30,90}.json`
(QPN heavy hitters), `cat4.keys`, `platforms.jsonl` (per-model hit breakdown),
`platform_pairs/` (one file per ticket, model+testbed pairs), and `meta/<KEY>.json`
(created/components/parent).

## Category 4 is defined by QPN, not by the label

`https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs?os=fboss&package=cli&days=90&source=t_recs&limit=200`
is the authority for "hit by CLI tests": it gives `hit_count`, `unique_tests`,
`unique_testbeds`, `trend`, `first_seen/last_seen` and the Jira status. Cat 4 =
(open STARS tickets ∩ QPN 90d) ∪ (open STARS tickets whose description mentions
`fboss2` or `cli/fboss2`). Then **add any QPN ticket with status New/Reopened
that the label query missed** — real heavy hitters have shown up with the label
`stars-ai-triage` (no `-auto`) or no label at all (NOS-15884, NOS-14705 in Sept 2026).
QPN tickets whose status is Done/WONTFIX/Blocked/In Review are excluded by the
status rule; mention them to the user as a watch list rather than dropping
silently, and run the fix check over that watch list (below) — for those, the
question is not "who owns this" but "did the fix stop the hits".

Agent/led_service crashes that are not CLI code still count: if STARS filed the
failure under `package=cli` it hurts the CLI pass rate, which is the metric.

## Per-platform hit breakdown

`hit_count` alone hides whether a bug is single-platform or fleet-wide, which is
the first thing the team asks. QPN exposes it per ticket:

```bash
curl -sf "https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs/timeline?ticket_id=NOS-16533&group_by=model&os=fboss&package=cli&days=90&source=t_recs"
# -> {"groups":[...],"points":[{"time":...,"counts":{"NH-CW800-F":12,...}}, ...]}
```

Sum `points[].counts` per group for the per-platform hit count; the total
reconciles exactly with `top-bugs`' `hit_count` for the same window. (`model=<name>`
also filters `/top-bugs`, one request per platform, but the timeline returns the
whole breakdown in one request per ticket — `fetch.sh` uses it for the 90-day
window and writes `platforms.jsonl` as `{key, days, totals:{model: n}}`.)
`groups` includes an `other` bucket for models outside the top N — keep it, but
don't count it as a platform.

`build_csv.py` renders that into a single **Platforms 90d** column, keyed by the
testbed codename prefix rather than the raw model name: `"fris 668, wdg 514,
crow 99, other 21"`. Wedge BACT/CACT both map to `wdg` and are merged; `other` is
the bucket for models outside the top N. Only tickets that appear in QPN get a
value; cat 1/2 rows (no QPN hits) stay blank. One column, not two — 7d/90d side
by side made the sheet too wide, and prefixes beat full names for width too.

The model→prefix map is derived on each run, not hardcoded: `/top-bugs/hits` pairs
every event's `model` with its `testbed`, so `fetch.sh` writes those pairs under
`platform_pairs/` (one file per ticket — concurrent appends of >4KB lines are not
atomic) and `build_csv.py` takes the most common testbed prefix per model (falling
back to the full name for a model it never saw). Current derived map:
Minipack3→fboss, NH-4010-F→gold, NH-4215-F→stlr, NH-4220-F→blkt, NH-BW800-F→crow,
NH-CW800-F→fris, Wedge800BACT/CACT→wdg.

## Fingerprints: verify the rules, don't trust the hit count

Every STARS ticket carries a fingerprint id. It lives in the STARS comment titles
(ADF `expand` nodes → `attrs.title`, "STARS Backfill Summary — N matches,
fingerprint F"), so a `.text`-only flatten misses it — grep the raw ticket JSON
for `fingerprint (\d+)`. Then fetch the actual rules:

```bash
export no_proxy=127.0.0.1,localhost,.internal.nexthop.ai,.nexthop.ai
curl -sf https://stars.sw.internal.nexthop.ai/v1/fingerprint/<ID>
```

The response gives `regex_rules` (the real matchers), `created_by`, `created_at`,
`state`, `hit_count`, `last_hit_time` and `recent_events`. Judge a fingerprint by
`regex_rules`, **not** by its hit count:

- **Good** — a `classname` plus a specific `log` symbol or a stack-trace regex
  (mangled `_ZN…` symbols). E.g. fp3700 = `FunctionStateUpdate::onError …
  {0,300} … SwSwitch::handlePendingUpdates`; fp4377 = classname
  `^TunnelIpInIpTest$` + `SaiTunnelManager17addP2MPTunnelTerm` +
  `sai_tunnel_term_table_entry`.
- **Bad / weak** — `log`-only with no `classname` (fp3988 = `SaiStore.{0,10}
  checkUnexpectedUnclaimedWarmbootHandles`), a literal `xml`/`reason` harness
  string with no test/class scope, or a hardcoded value (fp3509 = `Port
  'eth1/1/5' not found in getAllPortInfo`). The generic harness strings are the
  tell: `Agent did not become ready within 180 seconds` (fp3538), `Agent crashed
  during test: … dumped core (status=6/ABRT)` (fp3930).

Two traps that will mislead you:

- The `reason:` / `job:` line in a STARS comment is the **test-harness** message,
  not the fingerprint rule. A stack-trace fingerprint still shows `reason: …
  Agent did not become ready within 180 seconds`.
- A large backfill match count is **not** evidence of a bad fingerprint — a
  specific stack-trace regex legitimately matches thousands of occurrences of one
  crash. Judge by rule scope; never by the count.

The ticket description appendix also carries `Model metadata: <llm>` (which model
triaged it — gemini-3.8-flash, claude-opus-5, claude-sonnet-5, …) and
`Fingerprinting / counting notes:` (the scope the model chose, e.g. "Error-only
umbrella scope (no classname)"). `created_by` is only the actor (`mabel` /
`stars-triage-bot`), not the LLM. The Sept 16 2026 change nh#31627 discouraged
symptom trackers, so fingerprints created before then are more often weak.

Flag weak ones in the sheet's notes column: fp id, actor/LLM, the raw
`regex_rules`, the defect, and "re-fingerprint".

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

## Verify the fixes landed

The status rule keeps New/Reopened/Backlog, so everything with a fix in flight
(`In Merge`) or already closed (`Done`/`WONTFIX`/`Duplicate`) falls out of the CSV
into the watch list. That watch list is not "ignore" — it holds the two most
useful answers of the run: a ticket whose fix landed and whose hits went to zero
can be closed, and a ticket whose fix landed and whose hits **did not** stop is
still burning testbeds and belongs at the top of the sheet.

```bash
python3 fboss/.claude/skills/fboss-bug-scrub/scripts/fixcheck.py "$OUT"   # -> $OUT/fixcheck.csv
```

For every QPN ticket whose Jira status is not New/Reopened/Backlog it fetches the
daily hit series and the merged PR(s) and prints a verdict:

| Verdict | Meaning |
|---|---|
| `FIXED - quiet Nd, stopped Md after merge <day> (#PR)` | hit rate went to zero right after the fix landed — close it |
| `STILL FIRING - H hits/7d; fix #PR merged <day> did not take` | a fix has been merged for longer than the grace period and hits continue — escalate, and rank it at the top |
| `firing, but merge <day> is only Nd old (TIDE lag)` | too soon: a new image has to be marked stable in TIDE first |
| `quiet Nd - stopped Md after merge ... later than the TIDE lag` | quiet, but the tail was longer than the lag — worth a glance |
| `quiet Nd since <day>, Xd BEFORE the merge ... the fix is not what stopped it` | hits stopped before the fix landed; something else changed |
| `quiet Nd - <status>, no merged PR to attribute it to` | quiet but never fixed (`In Review`, `Blocked`, ...) |
| `no CLI hits in Nd` | nothing in this window |
| `ERROR - QPN fetch failed (...)`, `ERROR - gh failed (...)` | the fetch failed, so the verdict is *unknown* — never read it as "no hits". The script warns on stderr and exits 1 |

Two endpoints, both with a wrinkle:

- **Hits.** `GET /api/v1/stars/top-bugs/timeline?ticket_id=<KEY>&bucket=day&days=30&os=fboss&package=cli&source=t_recs`
  returns a *flat* `[{"time","count"}]` array of zero-filled daily counts — a
  different shape from `group_by=model`, which returns `{"groups","points"}`.
  Use `bucket=`, not `group_by=`: `group_by=day` is a 400 (`group_by` only takes
  `testbed|model|testname|branch|topology`). `after=`/`before=` are documented on
  this endpoint but do not filter in practice — a 90d window with `after=<merge>`
  still returns all 90 days, so slice the series client-side.
- **Merge date.** `gh pr list --repo nexthop-ai/private-fboss --state merged
  --search "<KEY> in:title"` — the PR title carries the Jira key (that is the
  link the Jira changelog shows). Take the newest merge, but keep them all: a
  ticket can have several, and naming an earlier one that did not take is the
  point. Match on a `\bKEY\b` word boundary, or `NOS-16533` also hits `NOS-165330`.
  The Jira changelog itself is not reachable from `acli` (`changelog` comes back
  null even with `--fields '*all'`), which is why the merge date comes from `gh`.

The grace period (default 2 days, `FIXCHECK_GRACE`) is the TIDE stable-image lag:
hits keep landing for a day or so after the merge because the fleet is still
running the previous image. NOS-17718 merged 2026-09-25, still hit on 09-26, zero
from 09-27 → `FIXED`. Anything still hitting after `merge + grace` is a fix that
did not take. Window and grace are separate knobs: `FIXCHECK_DAYS` (default 30) is
the timeline window the series covers, `FIXCHECK_GRACE` (default 2) is the lag —
setting `FIXCHECK_DAYS=4` to get a 4-day grace silently gets you a 4-day window
and a grace of 2.

**A fix that did not take comes back on the same ticket, not a new one.** STARS
does not file a second ticket for a failure it already knows: a match is
attributed to the ticket that owns the fingerprint — that is what lets the
regression-reopen gate act on the *existing* key (`nhtools/stars/stars/core/
regression_gate.py` decides "whether a fingerprint match should reopen a closed
ticket"), and a closed ticket keeps its series (NOS-16889 is `UNREPRODUCIBLE` and
still carries 3447 hits over 90d). Production (`STARS_REGRESSION_REOPEN=1`) runs
that gate: a match landing on a build that does not contain the ticket's fix
transitions the ticket back to `Reopened`, and an `UNREPRODUCIBLE` closure reopens
outright. So a still-broken fix normally reappears in the CSV on the next run —
the status rule keeps `New`/`Reopened` — and this pass is the same judgement made
from the hit *series* rather than from a single match event. It also covers what
the gate leaves alone: `WONTFIX` and `Duplicate` (deliberately comment-only
there), and the tickets that are quiet but not closed (`In Review`, `Blocked`).

## Update the triage tab (every run)

Mandatory every run — the sheet is the deliverable, the CSV is an
intermediate. `gws` prints a keyring line before JSON — always `| tail -n +2`.

**Read the tab first.** The expected pre-write state is exactly what the previous
run wrote: the grid in A–R, the generated fingerprint column in S, and nothing in
T or beyond. Overwriting A–S is the run, so that state is expected. Two things
mean the team has touched the tab: anything in T or later, or a cell in S that
is not one of last run's verdicts (each row's S cell is blank or a verdict naming
that row's ticket). If you see either, stop and ask before overwriting. The
`sept*` tabs are the frozen history: never write to them.

```bash
SHEET=1H8FpXlmZm2ABpr2kKCg_0Ji4n6RiujrXg4ztrBGmLMc
gws sheets spreadsheets values get \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"triage!A1:Z\"}" 2>&1 | tail -n +2
```

Nothing downstream clears the tab for you: `values update` writes only the cells
it is handed and leaves the rest untouched. The grid is a different height every
run (237 rows last time), so without an explicit clear a shorter run leaves the
previous run's tail rows in A–R *and* in S, where they still read as current and
now sit outside the `A1:S<n>` filter. Once the read-check has passed, clear A–S
from row 2 down before writing:

```bash
gws sheets spreadsheets values clear \
  --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"triage!A2:S\"}" 2>&1 | tail -n +2
```

Write the whole grid in one call; `USER_ENTERED` is required for the `HYPERLINK`
Jira links in column A:

```bash
gws sheets spreadsheets values update \
  --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"triage!A1\",\"valueInputOption\":\"USER_ENTERED\"}" \
  --json "$(cat $OUT/body.json)" 2>&1 | tail -n +2     # -> triage!A1:R<n>
```

Then the fingerprint column. Build `$OUT/s_body.json` as
`{"values": [["Triage / fingerprint notes"], [verdict], ...]}` aligned 1:1 with the
CSV rows (header first, then one cell per row, blank where there is no verdict) and
write `triage!S1`. Regenerate it every run — the previous column is not carried
over, and the row order changes every run.

```bash
gws sheets spreadsheets values update \
  --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"triage!S1\",\"valueInputOption\":\"USER_ENTERED\"}" \
  --json "$(cat $OUT/s_body.json)" 2>&1 | tail -n +2
```

Then format, all in one `spreadsheets batchUpdate` on sheetId `1684313274`: freeze
and bold row 1; wrap + top-align P–S; widths P 130 / Q 380 / R 520 / S 520; basic
filter over `A1:S<n>`.

Finally read `triage!A1:S<n>` back and assert every verdict sits on its own
ticket's row — an off-by-one silently puts every note on the wrong row.

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
- Fingerprint ids and backfill counts live in the STARS comment titles
  (`attrs.title` of ADF `expand` nodes), not in `.text`; `jq '[.. | .text?]'`
  finds neither — grep the raw JSON for `fingerprint (\d+)`. Per-test crashes are
  filed under the test class, so a `TunnelIpInIpTest` ticket can carry either a
  stack-trace fingerprint or a bare "Agent did not become ready within 180
  seconds" one — check `regex_rules` to tell them apart.
