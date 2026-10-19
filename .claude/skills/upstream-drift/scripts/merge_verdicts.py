#!/usr/bin/env python3
"""merge_verdicts.py OUT_DIR < judge_lines.jsonl  — merge judge JSON lines into OUT_DIR/verdicts.json, verify evidence."""
import html, json, re, subprocess, sys
from pathlib import Path
from github_data import open_upstream_prs, cited_pr_diffs
PR_DIFFS = ""          # live PR evidence for this invocation


def evidence_ok(ev, packet, refs=("origin/main", "upstream/main")):
    """Valid if quoted from the packet, or if the text is a real line somewhere in the repo.

    Judges verify some claims with their own grep, so accept 'path:NN:content',
    '<sha>:path:NN:content' and raw diff lines by progressively stripping prefixes
    and looking the remaining text up at the given refs."""
    if ev in packet or (PR_DIFFS and ev.rstrip() in PR_DIFFS):
        return True
    cur = re.sub(r"^[+-](?![+-])", "", ev.strip()).strip()
    candidates, seen = [], set()
    for _ in range(4):
        if len(cur) >= 8 and cur not in seen:
            candidates.append(cur); seen.add(cur)
        m = re.match(r"^[^\s:]+:(.*)$", cur, re.S)
        if not m:
            break
        cur = m.group(1).strip()
    for text in candidates:
        for ref in refs:
            if subprocess.run(["git", "grep", "-qF", "--", text, ref], capture_output=True).returncode == 0:
                return True
    return False


out = sys.argv[1]
index = json.load(open(f"{out}/index.json"))
lines = list(sys.stdin)
prdata = open_upstream_prs(index.get("fork"), index.get("repo"))
PR_DIFFS = "\n".join(cited_pr_diffs("\n".join(lines), index["repo"], prdata["prs"]).values())
packets = "\n".join(
    (Path(out) / path).read_text()
    for st in index["groups"].values()
    for path in [st["packet"], *(f"groups/{part}" for part in st.get("parts", []))]
)
try:
    verdicts = json.load(open(f"{out}/verdicts.json"))
except FileNotFoundError:
    verdicts = {}
for line in lines:
    line = line.strip()
    if not line.startswith("{"):
        continue
    d = json.loads(html.unescape(line)); g = d.pop("group")
    if "verdict" not in d:                       # notes-only line: merge do/notes into the existing verdict
        verdicts.setdefault(g, {}).update(d)
        print(f"{g}: notes {len(d.get('notes', ''))} chars")
        continue
    missing = [e for e in d.get("evidence", []) if not evidence_ok(e, packets)]
    d["evidence_verified"] = f"{len(d.get('evidence', [])) - len(missing)}/{len(d.get('evidence', []))}"
    if missing:
        d["evidence_missing"] = missing
    st = index["groups"].get(g, {})
    verdicts[g] = {**verdicts.get(g, {}), **d,
                   "gap_hash": st.get("gap_hash"), "judged_base": index.get("base", "")[:10],
                   "judged_upstream": index.get("upstream", "")[:10],
                   "judged_at": __import__("datetime").date.today().isoformat()}
    print(f"{g}: {d['verdict']} {d['effort']}/{d['benefit']} evidence {d['evidence_verified']}" + (f"  MISSING {len(missing)}" if missing else ""))
json.dump(verdicts, open(f"{out}/verdicts.json", "w"), indent=1)
