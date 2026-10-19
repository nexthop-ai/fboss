#!/usr/bin/env python3
"""Validate a rendered report.md against git, independently of the JSON it was rendered from.

  validate_report.py OUT_DIR [--base origin/main] [--upstream upstream/main]

Re-derives the groups, tags and gap sizes straight from git (same logic as drift.py, run again),
parses report.md, and checks the report against that. Assumes nothing from index.json except the
scope it declares. Exits 1 on any mismatch.
"""
import argparse, hashlib, importlib.util, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
from github_data import open_upstream_prs, cited_pr_diffs


def load_drift():
    spec = importlib.util.spec_from_file_location("drift", Path(__file__).with_name("drift.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--base", default="origin/main")
    ap.add_argument("--upstream", default="upstream/main")
    a = ap.parse_args()
    out = Path(a.out)
    report = (out / "report.md").read_text()
    d = load_drift()
    index = json.loads((out / "index.json").read_text())
    scope = index["scope"]
    d.set_grouping(scope, index.get("grouping", "auto"), index.get("depth", 2))
    prs = open_upstream_prs(index.get("fork"), index.get("repo"))["prs"]
    pr_diffs = cited_pr_diffs(report, index["repo"], prs)

    problems, checks = [], defaultdict(int)
    def bad(kind, msg): problems.append((kind, msg))

    # ---- 1. header shas and OURS/BOTH/THEIRS, recomputed from git -------------------------------
    mb = git("merge-base", a.base, a.upstream).strip()
    ours_ns = d.name_status(mb, a.base, scope)
    theirs_ns = d.name_status(mb, a.upstream, scope)
    net_ns = d.name_status(a.upstream, a.base, scope)
    tags = {p: ("BOTH" if p in ours_ns and p in theirs_ns else
                "OURS" if p in ours_ns else "THEIRS" if p in theirs_ns else "??") for p in net_ns}
    counts = {t: sum(1 for v in tags.values() if v == t) for t in ("OURS", "BOTH", "THEIRS")}

    m = re.search(r"merge-base `(\w+)` · base `(\w+)` · upstream `(\w+)`", report)
    if not m:
        bad("header", "report has no merge-base/base/upstream line")
    else:
        checks["header"] += 3
        for label, shown, real in (("merge-base", m.group(1), mb),
                                   ("base", m.group(2), git("rev-parse", a.base).strip()),
                                   ("upstream", m.group(3), git("rev-parse", a.upstream).strip())):
            if not real.startswith(shown):
                bad("header", f"{label} in report is {shown}, git says {real[:10]}")

    m = re.search(r"OURS (\d+) · BOTH (\d+) · THEIRS[^0-9]*(\d+)", report)
    if not m:
        bad("header", "report has no OURS/BOTH/THEIRS line")
    else:
        for label, shown, real in zip(("OURS", "BOTH", "THEIRS"), map(int, m.groups()),
                                      (counts["OURS"], counts["BOTH"], counts["THEIRS"])):
            checks["counts"] += 1
            if shown != real:
                bad("counts", f"{label}: report says {shown}, git says {real}")

    # ---- 2. groups and per-row numbers, recomputed ----------------------------------------------
    groups = defaultdict(list)
    for p, t in tags.items():
        if t != "THEIRS":
            groups[d.group_of(p[len(scope) + 1:], a.base, mb, ours_ns[p])].append(p)

    rows = {}
    for line in report.splitlines():
        m = re.match(r"\| \[([^\]]+)\]\([^)]*\)[^|]*\| (\d+) \((\d+)/(\d+)\) \| (\d+) \|(.*?)\| (\w*) \|", line)
        if m:
            rows[m.group(1)] = dict(files=int(m.group(2)), ours=int(m.group(3)), both=int(m.group(4)),
                                    gap=int(m.group(5)), prs=set(re.findall(r"/pull/(\d+)", m.group(6))),
                                    verdict=m.group(7))

    if set(rows) != set(groups):
        bad("groups", f"report rows {sorted(set(rows) - set(groups))} not in git; "
                      f"missing from report: {sorted(set(groups) - set(rows))}")
    for g, files in groups.items():
        if g not in rows:
            continue
        checks["rows"] += 1
        both = sum(1 for f in files if tags[f] == "BOTH")
        gap_txt = git("diff", "--no-renames", a.upstream, a.base, "--", *sorted(files))
        gap = sum(int(x) for l in git("diff", "--no-renames", "--numstat", a.upstream, a.base, "--",
                                      *sorted(files)).splitlines() for x in l.split()[:2] if x.isdigit())
        r = rows[g]
        if (r["files"], r["both"], r["ours"]) != (len(files), both, len(files) - both):
            bad("rows", f"{g}: report {r['files']} files ({r['ours']}/{r['both']}), "
                        f"git {len(files)} ({len(files) - both}/{both})")
        if r["gap"] != gap:
            bad("rows", f"{g}: report gap {r['gap']}, git {gap}")

        # verdict freshness: the stored fingerprint must match the diff as it is right now
        stored = json.loads((out / "verdicts.json").read_text()).get(g, {}).get("gap_hash")
        checks["fresh"] += 1
        if stored and stored != hashlib.sha256(gap_txt.encode()).hexdigest()[:12]:
            bad("stale", f"{g}: verdict was judged against a different diff — re-judge it")

    # ---- 3. sections: one per row, numbering intact, links resolve ------------------------------
    secs = re.findall(r"^## (\d+)\. (\S+) - (\w+)", report, re.M)
    if [int(n) for n, _, _ in secs] != list(range(1, len(secs) + 1)):
        bad("sections", f"section numbers are not 1..{len(secs)}: {[n for n, _, _ in secs]}")
    for n, g, verdict in secs:
        checks["sections"] += 1
        if g not in rows:
            bad("sections", f"§{n} is about {g}, which has no table row")
        elif rows[g]["verdict"] != verdict:
            bad("sections", f"{g}: table says {rows[g]['verdict']}, §{n} says {verdict}")
    def slug(h): return re.sub(r"\s", "-", re.sub(r"[^a-z0-9 _-]", "", h.lower()))
    heads = {slug(h) for h in re.findall(r"^## (.+)$", report, re.M)}
    for href in set(re.findall(r"\[§\d+\]\(#([^)]+)\)", report)):
        checks["links"] += 1
        if href not in heads:
            bad("links", f"§ link #{href} matches no heading")

    # ---- 4. every claim inside the sections ------------------------------------------------------
    pr_corpus = {l.rstrip() for diff in pr_diffs.values() for l in diff.splitlines()}
    real = "\n".join([git("diff", "--no-renames", a.upstream, a.base, "--", scope),
                      git("diff", "--no-renames", mb, a.base, "--", scope),
                      git("diff", "--no-renames", mb, a.upstream, "--", scope)])
    reall = {l.rstrip() for l in real.splitlines()}
    known = set(git("ls-tree", "-r", "--name-only", a.base).split()) | \
            set(git("ls-tree", "-r", "--name-only", a.upstream).split()) | \
            set(git("ls-tree", "-r", "--name-only", mb).split())
    PATH = d.path_re(a.base)

    body = report.split("# Steps per group", 1)[-1]
    for sec in re.split(r"\n(?=## \d+\. )", body):
        g = re.match(r"## \d+\. (\S+) ", sec)
        if not g:
            continue
        g = g.group(1)
        for path in set(PATH.findall(sec)):
            if "gen-cpp2/" in path:
                continue
            checks["paths"] += 1
            if path not in known:
                bad("path", f"{g}: {path} is in neither tree nor the merge-base")
        for sha in set(re.findall(r"\b([0-9a-f]{9,40})\b", sec)):
            checks["objects"] += 1
            kind = git("cat-file", "-t", sha).strip()
            if not kind:                      # neither a commit nor a blob/tree -> invented
                bad("object", f"{g}: {sha} is not a git object")
            elif kind == "commit" and subprocess.run(
                    ["git", "merge-base", "--is-ancestor", sha, a.upstream]).returncode != 0 \
                    and subprocess.run(
                    ["git", "merge-base", "--is-ancestor", sha, a.base]).returncode != 0:
                bad("commit", f"{g}: {sha} is a commit but is on neither {a.base} nor {a.upstream}")
        landed = set()
        for sha in set(re.findall(r"\b([0-9a-f]{9,40})\b", sec)):
            subj = git("log", "-1", "--format=%s%n%b", sha)
            landed |= set(re.findall(r"\(#(\d+)\)", subj)) | set(re.findall(r"pull/(\d+)", subj))
        landed |= set(re.findall(r"internal PR #(\d+)", sec))
        claimed = re.search(r"\*\*Already upstream\?\*\*(.*?)(?:\n\*\*|\Z)", sec, re.S)
        for pr in set(re.findall(r"^\s*[-*]\s*`?#(\d{3,5})",
                                 claimed.group(1) if claimed else "", re.M)) - landed:
            checks["prs"] += 1
            if pr not in prs:
                bad("pr", f"{g}: #{pr} claimed under 'Already upstream?' is not an open fork PR")
        for block in re.findall(r"```diff\n(.*?)```", sec, re.S):
            for line in block.splitlines():
                t = line.rstrip()
                if t[:1] not in "+-" or t[:3] in ("+++", "---") or not t[1:].strip() or t.endswith("..."):
                    continue
                checks["difflines"] += 1
                if t in reall:
                    continue
                flip = ("-" if t[0] == "+" else "+") + t[1:]
                if t in pr_corpus or flip in pr_corpus:
                    continue          # quoted from a cited PR's diff, which is legitimate evidence
                body = t[1:].strip()
                if len(body) >= 8 and any(
                        subprocess.run(["git", "grep", "-qF", "--", body, ref],
                                       capture_output=True).returncode == 0
                        for ref in (a.base, a.upstream)):
                    continue          # quoted from a file as it stands, not from a diff
                bad("diffline", f"{g}: {'sign reversed' if flip in reall else 'not in any real diff'}"
                                f": {t.strip()[:60]}")

    # ---- 5. SUBMITTED means the PRs CONTAIN the change, not merely touch the files --------------
    IDENT = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b|\b[a-z]+(?:[A-Z][a-z0-9]+)+\b")

    for g, r in sorted(rows.items()):
        if r["verdict"] != "SUBMITTED" or not r["prs"]:
            continue
        for n in sorted(r["prs"] - set(prs)):
            bad("pr", f"{g}: #{n} is not a current open fork PR")
        files = sorted(groups.get(g, []))
        if not files:
            continue
        added = "\n".join(l for l in git("diff", "--no-renames", a.upstream, a.base, "--", *files
                                          ).splitlines() if l.startswith("+") and not l.startswith("+++"))
        ours_syms = {t for t in IDENT.findall(added) if len(t) >= 8}
        if not ours_syms:
            continue
        pr_added = set()
        for n in sorted(r["prs"]):
            pr_added |= {l for l in pr_diffs.get(n, "").splitlines() if l.startswith("+")}
        pr_text = "\n".join(pr_added)
        missing = sorted(t for t in ours_syms if t not in pr_text)
        checks["coverage"] += len(ours_syms)
        if missing:
            sec = re.search(rf"^## \d+\. {re.escape(g)} .*?(?=\n## |\Z)", report, re.S | re.M)
            body = sec.group(0) if sec else ""
            unnamed = [t for t in missing if t not in body]
            if unnamed:
                bad("coverage", f"{g}: SUBMITTED, but PRs {sorted(r['prs'])} add none of "
                                f"{unnamed[:6]}{'...' if len(unnamed) > 6 else ''} "
                                f"({len(missing)} of {len(ours_syms)} symbols uncovered, "
                                f"{len(unnamed)} not even mentioned in the section)")

    print(f"validated {out/'report.md'} against git: " + "  ".join(f"{k}={v}" for k, v in sorted(checks.items())))
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for kind, msg in problems:
            print(f"  [{kind:9s}] {msg}")
        sys.exit(1)
    print("report matches git on every checked claim")


if __name__ == "__main__":
    main()
