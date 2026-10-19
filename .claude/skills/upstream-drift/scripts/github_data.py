"""Read current GitHub evidence. No responses are persisted or reused across runs."""
import json
import re
import subprocess
from collections import defaultdict


def gh(*args):
    return subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=True
    ).stdout


def open_upstream_prs(fork, repo):
    """Fetch open fork PRs and their current file lists; fail on incomplete data."""
    if not repo or not fork:
        raise ValueError("The audit needs an upstream repo and public fork")
    raw = gh(
        "api", "--paginate", f"repos/{repo}/pulls?state=open&per_page=100", "--jq",
        '.[] | {number, title, branch: .head.ref, repo: (.head.repo.full_name // "")}',
    )
    prs, files = {}, defaultdict(list)
    for line in raw.splitlines():
        pr = json.loads(line)
        if pr["repo"] != fork:
            continue
        n = str(pr["number"])
        paths = gh(
            "api", "--paginate", f"repos/{repo}/pulls/{n}/files?per_page=100",
            "--jq", ".[].filename",
        ).splitlines()
        prs[n] = {"title": pr["title"], "branch": pr["branch"], "files": paths}
        for path in paths:
            files[path].append(n)
    return {"prs": prs, "files": dict(files)}


def cited_pr_diffs(text, repo, open_prs):
    """Fetch each cited open PR once for this invocation, before checking evidence."""
    cited = set(re.findall(r"#(\d{3,5})\b|/pull/(\d+)\b", text))
    numbers = {a or b for a, b in cited} & set(open_prs)
    return {
        n: gh("pr", "diff", n, "--repo", repo)
        for n in sorted(numbers, key=int)
    }
