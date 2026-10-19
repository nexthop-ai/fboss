#!/usr/bin/env python3
"""Three-way drift packets for a fork: what WE changed vs what UPSTREAM changed since the merge-base.

  drift.py --scope PATH [--base origin/main] [--upstream upstream/main] [--grouping auto|dir|cli] --out DIR
  drift.py --render --out DIR        # index.json (+ verdicts.json) -> report.md

Stdlib only. Reads Git and current GitHub PR data.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from github_data import open_upstream_prs

REDACT = re.compile(r"(?!)")  # replaced from --redact in main()
CLI_SCOPE = "fboss/cli/fboss2"
# CLI registration files every command touches; flagged per group because they conflict constantly.
CLI_SHARED = ("CmdListConfig.cpp", "CmdList.cpp", "CmdHandlerImpl.cpp", "CmdArgsLists.cpp", "CmdUtilsCommon.h")
GROUPING, DEPTH = "dir", 2  # set from --grouping / --depth
IDENT = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b|\"[a-z][a-z0-9_-]{7,}\"")


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check).stdout


def name_status(a, b, scope):
    out = {}
    for line in git("diff", "--no-renames", "--name-status", a, b, "--", scope).splitlines():
        st, path = line.split("\t", 1)
        out[path] = st
    return out


def area_of(dir_parts):
    """dir_parts = a command DIRECTORY split on '/', e.g. ['commands','config','vlan'] (no file name).
    config+delete share one key (a feature is both verbs); show keeps its verb; protocol/<name> is one deeper."""
    verb = dir_parts[1]
    depth = 4 if len(dir_parts) > 3 and dir_parts[2] == "protocol" else 3
    area = "/".join(dir_parts[2:depth])
    if verb in ("config", "delete"):
        return area or verb
    return f"{verb}/{area}" if area else verb


def is_test(rel):
    return any(p in ("test", "tests") for p in rel.split("/")[:-1])


def dir_group(rel):
    """Generic grouping: the file's directory, cut to DEPTH levels below scope."""
    parts = rel.split("/")[:-1]
    return "/".join(parts[:DEPTH]) or "root"


def group_of(rel, base, mb, ours_status):
    """rel is path relative to scope. A test joins the group of the first in-scope header it
    #includes (so a test lands next to the code it tests); everything else groups by directory,
    or by CLI feature under --grouping cli."""
    parts = rel.split("/")
    if GROUPING == "cli" and parts[0] == "commands":
        return area_of(parts[:-1])          # drop the file name
    if is_test(rel):
        ref = mb if ours_status == "D" else base
        src = git("show", f"{ref}:{SCOPE}/{rel}", check=False)
        incs = [i for i in re.findall(rf'#include "{re.escape(SCOPE)}/([^"]+)"', src) if not is_test(i)]
        if GROUPING == "cli":
            incs = [i for i in incs if i.startswith("commands/")]
        if incs:
            # the header the test is named after (FooTest.cpp -> Foo.h), else the most specific one
            stem = re.sub(r"_?[Tt]ests?$", "", Path(rel).stem)
            named = [i for i in incs if Path(i).stem == stem]
            return group_of((named or sorted(incs, key=lambda i: -i.count("/")))[0], base, mb, "M")
    if GROUPING == "cli":
        if parts[0] == "test":
            return "/".join(parts[:2]) if len(parts) > 2 else "test"
        return parts[0] if len(parts) > 1 else "root"
    return dir_group(rel)


def idents_introduced(diff_text, mb, upstream, scope):
    added = "\n".join(l[1:] for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    cands = sorted({t.strip('"') for t in IDENT.findall(added)})[:200]
    if not cands:
        return {}
    flags = [f for c in cands for f in ("-e", c)]
    old = set(git("grep", "-how", *flags, mb, "--", scope, check=False).split())
    new = [c for c in cands if c not in old]
    if not new:
        return {}
    flags = [f for c in new for f in ("-e", c)]
    hits = defaultdict(set)
    for line in git("grep", "-ow", *flags, upstream, check=False).splitlines():
        _, path, tok = line.split(":", 2)
        hits[tok].add(path)
    return {c: sorted(hits.get(c, ()))[:5] for c in new}


def path_re(ref):
    """Repo paths quoted in notes: anything under a top-level dir of `ref` with a file extension.
    Not preceded by a path char, so '//neteng/fboss/bgp/x.h' is not clipped to 'fboss/bgp/x.h'."""
    tops = [t for t in git("ls-tree", "--name-only", "-d", ref).split() if not t.startswith(".")]
    return re.compile(rf"(?<![\w/.:])(?:{'|'.join(map(re.escape, tops)) or '(?!)'})/[\w./-]+\.\w+\b")


def remote_repo(remote):
    """owner/name for a git remote, or None."""
    url = git("remote", "get-url", remote, check=False).strip()
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def default_repos(upstream_remote, base_remote):
    """upstream repo from the upstream remote; the public fork is <base owner>/<upstream name>."""
    repo = remote_repo(upstream_remote)
    base = remote_repo(base_remote)
    fork = f"{base.split('/')[0]}/{repo.split('/')[1]}" if repo and base else None
    return repo, fork


def collect(a):
    global SCOPE
    SCOPE = a.scope.strip("/")
    mb = git("merge-base", a.base, a.upstream).strip()
    ours, theirs, net = (name_status(mb, a.base, a.scope), name_status(mb, a.upstream, a.scope),
                         name_status(a.upstream, a.base, a.scope))
    tags = {}
    for p in net:
        tags[p] = "BOTH" if p in ours and p in theirs else "OURS" if p in ours else "THEIRS" if p in theirs else "??"
    assert "??" not in tags.values(), [p for p, t in tags.items() if t == "??"]

    groups = defaultdict(list)
    for p, t in tags.items():
        if t != "THEIRS":
            groups[group_of(p[len(a.scope) + 1:], a.base, mb, ours[p])].append(p)

    out = Path(a.out)
    (out / "groups").mkdir(parents=True, exist_ok=True)
    repo, fork = default_repos(a.upstream.split("/")[0], a.base.split("/")[0])
    repo, fork = a.repo or repo, a.fork or fork
    prdata = open_upstream_prs(fork, repo)
    index = {"merge_base": mb, "base": git("rev-parse", a.base).strip(), "upstream": git("rev-parse", a.upstream).strip(),
             "scope": a.scope, "grouping": GROUPING, "depth": DEPTH, "repo": repo, "fork": fork, "counts": {t: sum(1 for v in tags.values() if v == t) for t in ("OURS", "BOTH", "THEIRS")},
             "theirs": sorted(p for p, t in tags.items() if t == "THEIRS"), "groups": {}}

    for g, files in sorted(groups.items()):
        files.sort()
        both = [f for f in files if tags[f] == "BOTH"]
        our_diff = git("diff", "--no-renames", mb, a.base, "--", *files)
        up_diff = git("diff", "--no-renames", mb, a.upstream, "--", *both) if both else ""
        up_log = git("log", "--format=%h %ad %s", "--date=short", f"{mb}..{a.upstream}", "--", *files)
        dirs = sorted({str(Path(f).parent) for f in files if "/test/" not in f})  # tests joined from elsewhere
        up_added = git("diff", "--no-renames", "--diff-filter=A", "--name-only", mb, a.upstream, "--", *dirs) if dirs else ""
        today = idents_introduced(our_diff, mb, a.upstream, a.scope)
        numstat = git("diff", "--no-renames", "--numstat", mb, a.base, "--", *files).splitlines()
        ins = sum(int(l.split()[0]) for l in numstat if l.split()[0].isdigit())
        dels = sum(int(l.split()[1]) for l in numstat if l.split()[1].isdigit())
        gap_diff = git("diff", "--no-renames", a.upstream, a.base, "--", *files)
        gap_hash = hashlib.sha256(gap_diff.encode()).hexdigest()[:12]
        gap = git("diff", "--no-renames", "--numstat", a.upstream, a.base, "--", *files).splitlines()
        gap_now = sum(int(x) for l in gap for x in l.split()[:2] if x.isdigit())  # lines differing ours vs upstream today
        pr_hits = defaultdict(list)                       # pr -> files of this group it touches
        for f in files:
            for n in prdata["files"].get(f, []):
                pr_hits[n].append(f)
        open_prs = [{"pr": n, "title": prdata["prs"][n]["title"], "covers": len(fs), "files": fs}
                    for n, fs in sorted(pr_hits.items(), key=lambda kv: -len(kv[1]))]
        stats = {"files": len(files), "both": len(both), "open_prs": open_prs, "ours_A": sum(ours[f] == "A" for f in files),
                 "ours_M": sum(ours[f] == "M" for f in files), "ours_D": sum(ours[f] == "D" for f in files),
                 "ins": ins, "dels": dels, "gap_now": gap_now, "gap_hash": gap_hash, "upstream_commits": len(up_log.splitlines()),
                 "upstream_added_files": len(up_added.splitlines()),
                 "touches_shared": sorted(Path(f).name for f in files
                                          if GROUPING == "cli" and Path(f).name in CLI_SHARED),
                 "idents_on_upstream": sum(1 for v in today.values() if v), "idents_new": len(today)}
        slug = g.replace("/", "__")
        head = [f"# {g}", "", "```json", json.dumps(stats, indent=1), "```", "",
                "## Files", *(f"- {tags[f]} {ours[f]} {f}" for f in files), "",
                f"## Open upstream PRs touching these files ({fork} -> {repo})",
                *([f"- #{p['pr']} ({p['covers']}/{len(files)} files) {p['title']}" for p in open_prs] or ["(none)"]), "",
                "## Upstream change (since merge-base)", "Commits touching these files:",
                up_log or "(none)", "", "Files upstream added in these dirs:", up_added or "(none)", "",
                "## Upstream today (identifiers we introduced; where they exist on upstream/main)",
                *([f"- {k}: {', '.join(v) if v else '(absent)'}" for k, v in sorted(today.items())] or ["(none)"]), ""]
        parts = []
        for title, text in (("Gap today (upstream -> ours; what still differs)", gap_diff),
                            ("Our change (merge-base -> ours)", our_diff),
                            ("Upstream change on BOTH files (merge-base -> upstream)", up_diff)):
            if not text.strip():
                continue
            chunks = split_diff(text, a.max_lines)
            for i, c in enumerate(chunks, 1):
                pname = f"{slug}.part{len(parts) + 1}.md"
                (out / "groups" / pname).write_text(REDACT.sub("<REDACTED>", f"# {g} — {title} ({i}/{len(chunks)})\n\n```diff\n{c}\n```\n"))
                parts.append(pname)
                head.append(f"- [{title} {i}/{len(chunks)}]({pname})")
        (out / "groups" / f"{slug}.md").write_text(REDACT.sub("<REDACTED>", "\n".join(head) + "\n"))
        index["groups"][g] = {**stats, "packet": f"groups/{slug}.md", "parts": parts, "file_list": files}

    covered = {f for v in index["groups"].values() for f in v["file_list"]}
    assert covered == {p for p, t in tags.items() if t != "THEIRS"}
    (out / "index.json").write_text(json.dumps(index, indent=1))
    # Collection starts a new audit, even when the Git diff has not changed.
    (out / "verdicts.json").write_text("{}\n")
    print(json.dumps({"merge_base": mb[:10], **index["counts"], "groups": len(groups)}))
    render(a)


def set_grouping(scope, grouping, depth):
    """Set the module grouping mode; validate_report.py calls this with what index.json recorded."""
    global SCOPE, GROUPING, DEPTH
    SCOPE = scope.strip("/")
    GROUPING = ("cli" if SCOPE == CLI_SCOPE else "dir") if grouping == "auto" else grouping
    DEPTH = depth


def split_diff(text, max_lines):
    """Split a multi-file diff on 'diff --git' boundaries into chunks <= max_lines (a single big file stays whole)."""
    files = re.split(r"(?m)^(?=diff --git )", text)
    chunks, cur, n = [], [], 0
    for f in files:
        k = f.count("\n")
        if cur and n + k > max_lines:
            chunks.append("".join(cur)); cur, n = [], 0
        cur.append(f); n += k
    if cur:
        chunks.append("".join(cur))
    return chunks


def gh_slug(heading):
    """GitHub's heading anchor: lowercase, drop all but [a-z0-9 _-], spaces -> hyphens."""
    t = re.sub(r"[^a-z0-9 _-]", "", heading.lower())
    return re.sub(r"\s", "-", t)


def render(a):
    out = Path(a.out)
    index = json.loads((out / "index.json").read_text())
    vfile = out / "verdicts.json"
    verdicts = json.loads(vfile.read_text()) if vfile.exists() else {}
    rank = {"L": 0, "M": 1, "S": 2}
    rows = sorted(index["groups"].items(), key=lambda kv: (rank.get(verdicts.get(kv[0], {}).get("benefit"), 3),
                                                            -rank.get(verdicts.get(kv[0], {}).get("effort"), 3), kv[0]))
    lines = [f"# Drift report — {index['scope']}", "",
             f"merge-base `{index['merge_base'][:10]}` · base `{index['base'][:10]}` · upstream `{index['upstream'][:10]}`  ",
             f"OURS {index['counts']['OURS']} · BOTH {index['counts']['BOTH']} · THEIRS (pending merge, not judged) {index['counts']['THEIRS']}", "",
             f"**Judged: {sum(1 for g in index['groups'] if g in verdicts)} / {len(index['groups'])} groups. "
             f"Still to judge: {', '.join(g for g in sorted(index['groups']) if g not in verdicts) or 'none'}.**", "",
             "> **What this report is.** A source-level inventory of how this tree differs from upstream, "
             "with a suggested action per feature. Nothing here has been compiled, unit-tested or run on "
             "hardware, and upstream acceptance is not implied. Treat each checklist as a proposal to review, "
             "not an approved change. `SUBMITTED` means the cited PRs' diffs were checked to contain the "
             "change, not that they will merge as-is.", "",
             "## How to read a row", "",
             "- **group** — one feature (a directory, or a CLI command family under `--grouping cli`); click for its packet (files, upstream context, raw diffs).",
             "- **files (OURS/BOTH)** — files we changed since the last merge with upstream. OURS = only we touched it; BOTH = upstream changed it too since then (conflicts every sync).",
             "- **gap now** — lines that differ between our copy and upstream's copy today (two-way diff). 0 = identical.",
             "- **open PR** — open PRs from our public fork into the upstream repo that touch this group's files, with how many of the group's files each covers. Non-empty = already submitted; the decision is chase/rebase, not re-send.",
             "- **verdict** — UPSTREAM (send it) · SUBMITTED (already in an open upstream PR; chase or rebase it) · KEEP (fork-only) · DROP (upstream has it, delete ours) · SPLIT (mixed, see reason) · UNSURE (human check). Empty = not judged yet.",
             "- **steps** — the section number below (search for `## 7.`) holding the group's step-by-step instructions (with diff hunks) in **Notes per group** below.",
             "- **effort** S/M/L — how hard to send or delete cleanly. **benefit** S/M/L — how much recurring merge pain it removes. Rows are sorted benefit desc, effort asc: top = do first.",
             "- **THEIRS** (bottom) — files only upstream changed; they arrive with the next sync and are not our drift.", "",
             "## Groups", "",
             "| group | files (OURS/BOTH) | gap now | open PR | verdict | effort | benefit | steps |",
             "|---|---|---|---|---|---|---|---|"]
    numbered = {g: n for n, (g, _) in enumerate((r for r in rows if verdicts.get(r[0], {}).get("notes")), 1)}
    heads = {g: f"{n}. {g} - {verdicts[g]['verdict']} (effort {verdicts[g].get('effort','?')}, "
                f"benefit {verdicts[g].get('benefit','?')})" for g, n in numbered.items()}
    for g, s in rows:
        v = verdicts.get(g, {})
        note_link = f"[§{numbered[g]}](#{gh_slug(heads[g])})" if g in numbered else ""
        prs = " ".join("[#%s](https://github.com/%s/pull/%s) %d/%d" % (p["pr"], index.get("repo", "unknown"), p["pr"], p["covers"], s["files"])
                       for p in s.get("open_prs", [])[:3])
        lines.append("| %s | %d (%d/%d) | %s | %s | %s | %s | %s | %s |" % (
            f"[{g}]({s['packet']})", s["files"], s["files"] - s["both"], s["both"],
            s.get("gap_now", "?"), prs, v.get("verdict", ""), v.get("effort", ""), v.get("benefit", ""), note_link))
    if numbered:
        lines += ["", "---", "", "# Steps per group", "",
                  "Each section says what the feature is, whether an upstream PR already carries it, "
                  "what differs today, and a numbered checklist to run.", "",
                  "In every ```diff block below, `+` is our code and `-` is upstream's "
                  "(the blocks are taken from `git diff upstream/main <base>`).", ""]
        for g, n in numbered.items():
            v, st = verdicts[g], index["groups"][g]
            prs = ", ".join(f"#{p['pr']} ({p['covers']}/{st['files']} files)" for p in st.get("open_prs", [])) or "none"
            lines += [f"## {heads[g]}", "",
                      f"`{st['files']}` files ({st['files'] - st['both']} ours-only, {st['both']} both sides) · "
                      f"gap today `{st.get('gap_now','?')}` lines · open upstream PRs: {prs} · "
                      f"raw diffs: `{st['packet']}`", "",
                      v["notes"].rstrip(), ""]
    lines += ["", "<details><summary>THEIRS — upstream changes pending merge (not drift)</summary>", "",
              *(f"- {p}" for p in index["theirs"]), "", "</details>", ""]
    (out / "report.md").write_text("\n".join(lines))

    # Validate the rendered report and stamp the result into it, so nobody can share an unchecked one.
    val = Path(__file__).with_name("validate_report.py")
    stamp = "> **Not validated** — `validate_report.py` is missing next to `drift.py`."
    validation_status = 1
    if val.exists():
        r = subprocess.run([sys.executable, str(val), str(out), "--base", a.base, "--upstream", a.upstream],
                           capture_output=True, text=True)
        validation_status = r.returncode
        tail = (r.stdout.strip().splitlines() or ["(no output)"])
        if r.returncode == 0:
            stamp = f"> ✅ **Validated against git** on {datetime.date.today().isoformat()} — {tail[0]}"
        else:
            issues = [l.strip() for l in tail if l.strip().startswith("[")]
            stamp = ("> ❌ **VALIDATION FAILED — do not act on this report.** "
                     + "; ".join(issues[:4]) + (f" (+{len(issues) - 4} more)" if len(issues) > 4 else "")
                     + f"  Re-run `validate_report.py {out}` for the full list.")
        print(tail[-1] if tail else "")
    text = (out / "report.md").read_text().replace("## How to read a row", stamp + "\n\n## How to read a row", 1)
    (out / "report.md").write_text(text)
    print(f"wrote {out / 'report.md'}")
    if validation_status:
        raise SystemExit(validation_status)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--upstream", default="upstream/main")
    ap.add_argument("--scope", help="repo path to audit, e.g. fboss/cli/fboss2 or fboss/agent (required to collect)")
    ap.add_argument("--grouping", choices=("auto", "dir", "cli"), default="auto",
                    help=f"dir: by directory (--depth levels); cli: fboss2 command families; auto: cli for {CLI_SCOPE}, else dir")
    ap.add_argument("--depth", type=int, default=2, help="directory levels below --scope per group (dir grouping)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-lines", type=int, default=1500)
    ap.add_argument("--repo", help="upstream GitHub repo (default: from the --upstream remote)")
    ap.add_argument("--fork", help="public fork PRs are opened from (default: <base remote owner>/<upstream repo name>)")
    ap.add_argument("--redact", default=r"\b(gold\d+|wdg\d+|fboss\d{3}|crow\d+)\b|[\w.-]+\.internal\.nexthop\.ai",
                    help="regex for host/DUT names to redact from packets; edit for your org")
    ap.add_argument("--render", action="store_true", help="only re-render report.md from index.json + verdicts.json")
    args = ap.parse_args()
    globals()["REDACT"] = re.compile(args.redact)
    if not args.render:
        if not args.scope:
            ap.error("--scope is required")
        set_grouping(args.scope, args.grouping, args.depth)
    render(args) if args.render else collect(args)
