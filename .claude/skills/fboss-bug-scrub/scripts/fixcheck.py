#!/usr/bin/env python3
"""Verify that a merged fix actually stopped the hits for a QPN ticket.

The status rule keeps New/Reopened/Backlog tickets only, so everything that has
a fix in flight (In Merge) or is already closed (Done/WONTFIX/Duplicate) falls
out of the CSV into the watch list. This is the pass that tells you what to do
with that watch list: for each such ticket, did the hit rate go to zero once the
PR merged, or is it still burning testbeds?

Hits come from QPN's daily timeline; the merge date comes from the merged PR
whose title carries the Jira key (the same convention the Jira link uses, e.g.
"nexthop-ai/private-fboss#2250: NOS-17718: ...").

A fetch that fails is never reported as data: QPN or `gh` errors become
`ERROR - ...` verdicts (so a ticket that is still firing cannot read as clean
just because QPN was down), a warning goes to stderr, and the script exits 1.

Usage: fixcheck.py <outdir> [--days N] [--grace N]
Writes <outdir>/fixcheck.csv and prints a summary table.

Env: FIXCHECK_DAYS (default 30), FIXCHECK_GRACE (default 2).
"""

import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

QPN = "https://qpn.sw.internal.nexthop.ai/api/v1/stars/top-bugs"
REPO = "nexthop-ai/private-fboss"
OPEN = {"NEW", "New", "Reopened", "Backlog"}
DONE = {"Done", "WONTFIX", "Duplicate", "UNREPRODUCIBLE", "Blocked", "In Review"}

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
for i, a in enumerate(sys.argv):
    if a == "--days":
        os.environ["FIXCHECK_DAYS"] = sys.argv[i + 1]
    if a == "--grace":
        os.environ["FIXCHECK_GRACE"] = sys.argv[i + 1]
DAYS = int(os.environ.get("FIXCHECK_DAYS", "30"))
GRACE = int(os.environ.get("FIXCHECK_GRACE", "2"))
TODAY = dt.date.today()


class FetchError(Exception):
    """A fetch that failed. Never degrades into an empty result."""


def get(url):
    """JSON from QPN, or raise FetchError."""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except Exception as e:
        raise FetchError(f"{type(e).__name__}: {e}") from e


def daily(key):
    """[(date, count)] for the last DAYS days, zero-filled, oldest first.

    Raises FetchError when QPN is unreachable or answers with something other
    than the flat daily array, so the caller reports it rather than calling a
    failed fetch "no CLI hits".
    """
    d = get(
        f"{QPN}/timeline?ticket_id={key}&bucket=day&days={DAYS}"
        f"&os=fboss&package=cli&source=t_recs"
    )
    if not isinstance(d, list):
        raise FetchError(f"unexpected timeline shape: {type(d).__name__}")
    return [(p["time"][:10], p.get("count", 0)) for p in d]


def merged_prs(key):
    """[(number, mergedAt, title)] for merged PRs whose title carries the key.

    Raises FetchError when `gh` cannot run or fails (unauthenticated, rate
    limited, ...) — every ticket would otherwise read "no merged PR", which is
    exactly the wrong conclusion for a ticket that is still firing.
    """
    try:
        cp = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPO,
                "--state",
                "merged",
                "--search",
                f"{key} in:title",
                "--json",
                "number,title,mergedAt",
                "--limit",
                "20",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        raise FetchError(f"gh did not run: {type(e).__name__}: {e}") from e
    if cp.returncode != 0:
        err = cp.stderr.strip().splitlines()
        raise FetchError(f"gh exit {cp.returncode}: {err[-1] if err else ''}".strip())
    try:
        prs = json.loads(cp.stdout or "[]")
    except ValueError as e:
        raise FetchError(f"gh returned non-JSON: {e}") from e
    pat = re.compile(r"\b" + re.escape(key) + r"\b")
    return sorted(
        [
            (p["number"], p["mergedAt"], p["title"])
            for p in prs
            if pat.search(p.get("title", ""))
        ],
        key=lambda x: x[1],
    )


def days_ago(iso):
    return (TODAY - dt.date.fromisoformat(iso[:10])).days


def _quiet_verdict(status, last, quiet, prs):
    """No hits for GRACE days: did they stop when the fix landed?"""
    newest = prs[-1] if prs else None
    if not newest:
        return f"quiet {quiet}d - {status}, no merged PR to attribute it to"
    mday = newest[1][:10]
    tail = (dt.date.fromisoformat(last) - dt.date.fromisoformat(mday)).days
    if tail < 0:
        return (
            f"quiet {quiet}d since {last}, {-tail}d BEFORE the merge {mday} "
            f"(#{newest[0]}) - the fix is not what stopped it"
        )
    if tail <= GRACE:
        return (
            f"FIXED - quiet {quiet}d, stopped {tail}d after merge {mday} (#{newest[0]})"
        )
    return (
        f"quiet {quiet}d - stopped {tail}d after merge {mday} "
        f"(#{newest[0]}), later than the TIDE lag"
    )


def verdict(status, series, prs, hits7):
    """One-line verdict for a ticket on the watch list.

    The question is not "did the fix work" in the abstract but "is this still
    burning testbeds". So: no hits in the last GRACE days means quiet, whatever
    the Jira status says; hits in the last GRACE days means still firing, and
    the merge date only decides whether that is expected (TIDE stable-image lag)
    or a fix that did not take.
    """
    if isinstance(series, FetchError):
        return f"ERROR - QPN fetch failed ({series})"
    if isinstance(prs, FetchError):
        return f"ERROR - gh failed ({prs})"
    hits = [d for d, c in series if c > 0]
    if not hits:
        # Valid but all-zero series: the ticket is in the window and nothing
        # hit. Falling through would reach _quiet_verdict with last=None and
        # crash on the date arithmetic (and "quiet since <no date>" would be a
        # lie anyway).
        return f"no CLI hits in {DAYS}d"
    last = hits[-1]
    quiet = days_ago(last)
    newest = prs[-1] if prs else None

    if quiet >= GRACE:
        return _quiet_verdict(status, last, quiet, prs)

    if not newest:
        return f"STILL FIRING - {hits7} hits/7d, no merged PR ({status})"
    old = [p for p in prs if days_ago(p[1][:10]) >= GRACE]
    if old:
        return (
            f"STILL FIRING - {hits7} hits/7d; fix #{old[-1][0]} merged "
            f"{old[-1][1][:10]} did not take"
        )
    mday = newest[1][:10]
    return f"firing, but merge {mday} is only {days_ago(mday)}d old (TIDE lag)"


def main():
    top = {}
    for d in (7, 30, 90):
        f = os.path.join(OUT, f"top{d}.json")
        if not os.path.exists(f):
            continue
        with open(f) as fh:
            for it in json.load(fh).get("items", []):
                top.setdefault(it["ticket_id"], {})[d] = it
    watch = {k: v for k, v in top.items() if v[max(v)]["jira"]["status"] not in OPEN}
    print(f"{len(top)} QPN tickets, {len(watch)} on the watch list (non-open)")

    def one(k):
        try:
            series = daily(k)
        except FetchError as e:
            series = e
        try:
            prs = merged_prs(k)
        except FetchError as e:
            prs = e
        return k, series, prs

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(one, sorted(watch)))

    rows = []
    errors = 0
    for k, series, prs in res:
        v = watch[k]
        it = v[max(v)]
        qpn_failed = isinstance(series, FetchError)
        gh_failed = isinstance(prs, FetchError)
        errors += qpn_failed or gh_failed
        # A failed fetch must not read as a clean verdict: the verdict carries
        # the ERROR and the timeline-derived columns go blank instead of
        # reporting "no hits". (Hits 7d/30d still come from top{7,30}.json,
        # which fetch.sh pulled from a different endpoint.)
        series_ = [] if qpn_failed else series
        prs_ = [] if gh_failed else prs
        hits7 = v[7]["hit_count"] if 7 in v else sum(c for _, c in series_[-7:])
        # A ticket seen only in top90.json has v[max(v)] == the 90-day item, so
        # its hit_count is the 90-day number, not this column's. The zero-filled
        # daily series is the correct fallback, the same way hits7 uses
        # series[-7:].
        hits30 = v[30]["hit_count"] if 30 in v else sum(c for _, c in series_[-30:])
        verd = verdict(it["jira"]["status"], series, prs, hits7)
        hits = [d for d, c in series_ if c > 0]
        rows.append(
            {
                "Jira ID": k,
                "Status": it["jira"]["status"],
                "Hits 7d": hits7,
                "Hits 30d": hits30,
                "Last hit": hits[-1] if hits else "",
                "Quiet (days)": days_ago(hits[-1]) if hits else "",
                "Latest PR merged": f"#{prs_[-1][0]} {prs_[-1][1][:10]}"
                if prs_
                else "",
                "Verdict": verd,
                "Title": it["jira"]["summary"],
            }
        )

    def rank(r):
        if r["Verdict"].startswith("ERROR"):
            return (-1, 0)  # unknown verdict: never bury a failed fetch
        for i, prefix in enumerate(("STILL FIRING", "firing,", "quiet", "FIXED")):
            if r["Verdict"].startswith(prefix):
                return (i, -r["Hits 7d"])
        return (9, 0)

    rows.sort(key=rank)

    cols = list(rows[0].keys()) if rows else []
    with open(os.path.join(OUT, "fixcheck.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(
            f"{r['Jira ID']:<12} {r['Status']:<16} h7={r['Hits 7d']:<5} "
            f"last={r['Last hit'] or '-':<11} {r['Verdict']}"
        )
    print(f"-> {os.path.join(OUT, 'fixcheck.csv')}")
    if errors:
        print(
            f"WARNING: {errors} ticket(s) had a failed fetch - see the "
            f"ERROR verdicts (not a clean 'no hits')",
            file=sys.stderr,
        )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
