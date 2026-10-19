#!/usr/bin/env python3
"""Cross-check every factual claim in verdicts.json against real git / GitHub state.

  verify_report.py OUT_DIR [--base origin/main] [--upstream upstream/main]

Checks, per group:
  files    every repo path named in the notes exists on our side, upstream, or is a known deleted file
  commits  every <hex7+> (#NNNN) or bare 7-40 hex sha named is reachable from base or upstream
  prs      every #NNNN named is a real open PR from our fork AND touches at least one of the group's files
  verdict  SUBMITTED requires open PRs; KEEP/DROP/UPSTREAM must not silently ignore one
  evidence every evidence string appears verbatim in the group's packet
  steps    every git path in a `git checkout/rm` step exists on the side it is taken from
Exit 1 if anything fails.
"""
import argparse, json, re, subprocess, sys
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


def load_drift():
    import importlib.util
    spec = importlib.util.spec_from_file_location("drift", Path(__file__).with_name("drift.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def git(*a, check=False):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=check).stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--base", default="origin/main"); ap.add_argument("--upstream", default="upstream/main")
    ap.add_argument("--internal-repo", help="repo that 'internal PR #N' refers to (default: from the base remote)")
    a = ap.parse_args()
    out = Path(a.out)
    index = json.loads((out / "index.json").read_text())
    verdicts = json.loads((out / "verdicts.json").read_text())
    prdata = open_upstream_prs(index.get("fork"), index.get("repo"))
    mb = index["merge_base"]

    ours = set(git("ls-tree", "-r", "--name-only", a.base).split())
    theirs = set(git("ls-tree", "-r", "--name-only", a.upstream).split())
    at_mb = set(git("ls-tree", "-r", "--name-only", mb).split())
    known = ours | theirs | at_mb

    PATH = load_drift().path_re(a.base)
    SHA = re.compile(r"\b([0-9a-f]{7,40})\b")
    PR = re.compile(r"#(\d{3,5})\b")
    CHECKOUT = re.compile(r"git checkout (\S+) -- ([^\n`]+)")

    url = git("remote", "get-url", a.base.split("/")[0]).strip()
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    internal_repo = a.internal_repo or (f"{m.group(1)}/{m.group(2)}" if m else None)

    globals()["PR_DIFFS"] = "\n".join(cited_pr_diffs(
        json.dumps(verdicts), index["repo"], prdata["prs"]
    ).values())

    head = git("rev-parse", "HEAD").strip()
    base_sha = git("rev-parse", a.base).strip()
    worktree_matches_base = head == base_sha
    scope = index["scope"]
    real = "\n".join([git("diff", "--no-renames", a.upstream, a.base, "--", scope),
                       git("diff", "--no-renames", mb, a.base, "--", scope),
                       git("diff", "--no-renames", mb, a.upstream, "--", scope)])
    if not worktree_matches_base:
        print(f"note: worktree is at {head[:10]}, analysed base {a.base} is {base_sha[:10]} "
              f"— on-disk file checks skipped (git checkout {a.base} to enable them)")

    problems, checked = [], {"files": 0, "commits": 0, "prs": 0, "evidence": 0, "steps": 0}
    for g, v in sorted(verdicts.items()):
        if g not in index["groups"]:
            problems.append((g, "stale", f"group not in index.json")); continue
        st = index["groups"][g]
        text = (v.get("notes", "") or "") + "\n" + (v.get("do", "") or "")
        packet = (out / st["packet"]).read_text()
        for pt in st.get("parts", []):
            packet += (out / "groups" / pt).read_text()

        for path in sorted(set(PATH.findall(text))):
            if "gen-cpp2/" in path:      # build-time generated header, never in git
                continue
            checked["files"] += 1
            if path not in known:
                problems.append((g, "file", f"{path} exists on neither side nor at merge-base"))

        for sha in sorted(set(SHA.findall(text))):
            if len(sha) < 7 or not re.search(rf"\b{sha}\b", packet):
                continue                                    # only check shas the packet itself shows
            checked["commits"] += 1
            if not git("cat-file", "-t", sha).strip() == "commit":
                problems.append((g, "commit", f"{sha} is not a commit object"))
            elif not (git("merge-base", "--is-ancestor", sha, a.upstream) == "" and
                      subprocess.run(["git", "merge-base", "--is-ancestor", sha, a.upstream]).returncode == 0):
                problems.append((g, "commit", f"{sha} not reachable from {a.upstream}"))

        group_files = set(st["file_list"])
        internal = set(re.findall(r"internal PR #(\d+)", text))
        for n in sorted(internal):
            checked["internal"] = checked.get("internal", 0) + 1
            if not internal_repo:
                continue
            r = subprocess.run(["gh", "pr", "view", n, "--repo", internal_repo, "--json", "number"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                problems.append((g, "internal", f"internal PR #{n} not found in {internal_repo}"))
        # a PR number is "landed" when a sha quoted in the notes actually carries it in its subject,
        # e.g. `01e49e13c33 2026-09-21 fboss2 ... peer-group commands (#1395)`
        landed = set(internal)
        for sha in set(SHA.findall(text)):
            if len(sha) < 7 or not re.search(rf"\b{sha}\b", packet):
                continue
            subj = git("log", "-1", "--format=%s%n%b", sha)
            landed |= set(re.findall(r"\(#(\d+)\)", subj)) | set(re.findall(r"pull/(\d+)", subj))
        for sha, n in re.findall(r"([0-9a-f]{7,40})\s*\(#(\d+)\)", text):
            checked["landed"] = checked.get("landed", 0) + 1
            body = git("log", "-1", "--format=%s%n%b", sha)
            if not body.strip():
                problems.append((g, "landed", f"{sha} (#{n}): sha not found"))
            elif f"(#{n})" not in body and f"pull/{n}" not in body:
                problems.append((g, "landed", f"{sha} does not belong to PR #{n} (subject: {body.splitlines()[0][:60]})"))
        # only PRs claimed under "Already upstream?" are load-bearing; elsewhere a PR may be
        # mentioned to rule it out ("#1368 does not touch this file")
        m = re.search(r"\*\*Already upstream\?\*\*(.*?)(?:\n\*\*|\Z)", text, re.S)
        claimed = set(re.findall(r"^\s*[-*]\s*`?#(\d{3,5})", m.group(1), re.M)) if m else set()
        for pr in sorted(set(PR.findall(text)) - landed):
            checked["prs"] += 1
            info = prdata["prs"].get(pr)
            if not info:
                problems.append((g, "pr", f"#{pr} cited as open, but it is not an open PR from our fork")); continue
            if pr in claimed and not group_files & set(info["files"]):
                problems.append((g, "pr", f"#{pr} claimed under 'Already upstream?' but touches none of this group's files"))

        listed = {p["pr"] for p in st.get("open_prs", [])}
        if v["verdict"] == "SUBMITTED" and not listed:
            problems.append((g, "verdict", "SUBMITTED but no open PR covers this group"))
        if v["verdict"] in ("UPSTREAM", "DROP") and listed and not PR.search(text):
            problems.append((g, "verdict", f"{v['verdict']} but open PRs {sorted(listed)} exist and notes never mention them"))

        # a SUBMITTED group must account for every file its PRs do NOT cover
        if v["verdict"] == "SUBMITTED":
            covered = set()
            for pr in listed:
                covered |= group_files & set(prdata["prs"].get(pr, {}).get("files", []))
            for path in sorted(group_files - covered):
                checked["leftover"] = checked.get("leftover", 0) + 1
                if Path(path).name not in text:
                    problems.append((g, "leftover", f"SUBMITTED but {path} is in no PR and the notes never mention it"))

        # (a) files the notes name must exist on disk, but only when the worktree matches the analysed base
        if worktree_matches_base:
            for path in sorted(set(PATH.findall(text))):
                if "gen-cpp2/" in path or path not in ours:
                    continue
                checked["ondisk"] = checked.get("ondisk", 0) + 1
                if not Path(path).is_file():
                    problems.append((g, "ondisk", f"{path} is in {a.base} but missing from the working tree"))

        # (b) every -/+ line quoted in a ```diff block must appear in a real diff (scope-wide)
        for block in re.findall(r"```diff\n(.*?)```", text, re.S):
            for line in block.splitlines():
                if not line[:1] in "+-" or line[:3] in ("+++", "---") or not line[1:].strip():
                    continue
                if line.rstrip().endswith("..."):          # deliberately elided
                    continue
                checked["difflines"] = checked.get("difflines", 0) + 1
                txt = line.rstrip()
                if txt in real:
                    continue
                flipped = ("-" if txt[0] == "+" else "+") + txt[1:]
                if PR_DIFFS and (txt in PR_DIFFS or flipped in PR_DIFFS):
                    continue                      # quoted from a cited PR's diff
                body = txt[1:].strip()
                if len(body) >= 8 and any(
                        subprocess.run(["git", "grep", "-qF", "--", body, ref],
                                       capture_output=True).returncode == 0
                        for ref in (a.base, a.upstream)):
                    continue                      # quoted from a file as it stands today
                if flipped in real:
                    problems.append((g, "sign", f"+/- reversed vs the real diff: {txt.strip()[:65]}"))
                else:
                    problems.append((g, "diffline", f"quoted but in no real diff: {txt.strip()[:65]}"))

        for ev in v.get("evidence", []):
            checked["evidence"] += 1
            if not evidence_ok(ev, packet, (a.base, a.upstream)):
                problems.append((g, "evidence", f"not in packet: {ev[:60]}"))

        # bazel targets cited in steps must exist in the matching BUCK file
        for tgt in sorted(set(re.findall(r"(?<![\w:])//([\w/.-]+):([\w-]+)", text))):
            pkg, name = tgt
            checked["targets"] = checked.get("targets", 0) + 1
            # a target may be defined in BUCK or in a .bzl macro loaded by that package
            defs = [f for pat in ("BUCK", "BUILD", "BUILD.bazel", "*.bzl") for f in Path(pkg).glob(pat)]
            if not defs:
                problems.append((g, "target", f"//{pkg}:{name}: no BUCK/BUILD/.bzl in {pkg}"))
            elif not any(f'name = "{name}"' in f.read_text() for f in defs):
                problems.append((g, "target", f"//{pkg}:{name} is defined in none of {[f.name for f in defs]}"))

        for ref, paths in CHECKOUT.findall(text):
            for path in paths.split():
                if not PATH.fullmatch(path):
                    continue
                checked["steps"] += 1
                side = theirs if "upstream" in ref else ours if ref in ("HEAD", a.base, "origin/main") else at_mb
                if path not in side:
                    problems.append((g, "step", f"git checkout {ref} -- {path}: not present in {ref}"))

    print(f"groups: {len(verdicts)}/{len(index['groups'])}   checks: " +
          "  ".join(f"{k}={n}" for k, n in checked.items()))
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for g, kind, msg in problems:
            print(f"  [{kind:8s}] {g}: {msg}")
        sys.exit(1)
    print("all claims verified")

if __name__ == "__main__":
    main()
