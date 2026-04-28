---
name: upstream-pr
description: Send an internal Nexthop FBOSS PR upstream to facebook/fboss. Identifies the head branch from the internal PR, creates an upstream branch from upstream/main on the public fork (nexthop-ai/fboss), cherry-picks the PR's commits, runs `nh-fix-merge-conflicts.py` for the cmake/BUCK file-list conflicts and resolves the rest by hand, transiently cherry-picks `bazel-build` for build+test, drops it via rebase, sanitizes commit + PR text (NOS-XXXX prefixes, DUT names, internal stack lists), pushes to `nexthop-ai`, opens the upstream PR with the `[Nexthop]` (or `[Nexthop][fboss2-dev]`) prefix, then updates the tracking spreadsheet, comments back on the internal PR, and flips its `Upstream required` flag to No so internal automation doesn't try to re-upstream.
when_to_use: |
  User asks to upstream an internal FBOSS PR — typical phrasings:
  "upstream PR #N", "send PR N upstream", "publish PR N to facebook/fboss".
  Bail out early if the PR already has an upstream counterpart
  (check spreadsheet column M *and* `gh pr list --repo facebook/fboss
  --label nexthop` — column M is sometimes unpopulated even when the
  upstream PR exists).
argument-hint: [internal-PR-number]
---

# Upstreaming an internal FBOSS PR

## 0. Inputs

- **Internal PR number** (e.g. `743`). The only required argument.
- Repo layout (must already be set up; verify with `git remote -v`):
  - `origin` → `nexthop-ai/private-fboss` (private repo — internal PRs)
  - `nexthop-ai` → `nexthop-ai/fboss` (public fork of facebook/fboss)
  - `upstream` → `facebook/fboss` (the canonical upstream)
  Internal PRs target `origin/main`. Upstream PRs are pushed to
  `nexthop-ai` and opened against `facebook/fboss:main`.

## 1. Pre-flight bail-out checks

The most expensive failure mode is doing the full rebase + build only
to discover an upstream PR already exists. Two checks, both required:

### 1a. Tracking spreadsheet column M

The FBOSS team tracks CLI work in a shared sheet (see also
[add-config-cli/SKILL.md §0a](../add-config-cli/SKILL.md)). Each
internal PR may span multiple rows. `gws` is authenticated under the
user's account and emits a keyring-backend line before its JSON payload
— strip with `tail -n +2`.

```bash
SHEET=1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs
PR=743
gws sheets spreadsheets values get \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!C1:N1064\"}" \
    2>&1 | tail -n +2 | python3 -c "
import sys, json
data = json.load(sys.stdin).get('values', [])
hits = []
for i, row in enumerate(data, 1):
    n = row[11] if len(row) > 11 else ''
    m = row[10] if len(row) > 10 else ''
    if '$PR' in n:
        hits.append((i, row[4] if len(row) > 4 else '', m, n))
print(f'Found {len(hits)} rows referencing $PR')
for r in hits:
    print(f'  row {r[0]}: G={r[1]!r} M={r[2]!r} N={r[3]!r}')
"
```

If column M is non-empty for any of those rows → upstream PR already
exists. Stop, surface the existing upstream PR to the user.

Save the row range (`<min>:<max>`) — it's contiguous and you'll write
back to it in §9.

### 1b. Open/closed Nexthop PRs upstream

Column M can be unpopulated even when the upstream PR exists (recent
example: PR #741 → upstream #1105 was open for a week with column M
still empty). Always also keyword-scan the upstream PR list:

```bash
gh pr list --repo facebook/fboss --label nexthop --state all --limit 50 \
    --json number,title,headRefName,state,createdAt
```

Match by branch name (the upstream branch name will be the internal
head branch with the `<user>.` prefix dropped, e.g. `benoit.copp-cpuqueues`
→ `copp-cpuqueues`) or by title keyword. If anything matches, stop.

### 1c. Working tree clean + remotes fresh + infra branches present

```bash
git status --porcelain        # only untracked files OK; no M/D/A
git fetch upstream
git fetch origin
git fetch nexthop-ai
git ls-remote nexthop-ai bazel-build
git ls-remote origin benoit.blaze
git show origin/main:.github/scripts/nh-fix-merge-conflicts.py >/dev/null
```

`bazel-build` lives on `nexthop-ai`, **not** `origin` (it's
upstream-bound infra). `benoit.blaze` lives on `origin` (Nexthop-only
overrides for the build env). The merge-conflict script is checked in
on `origin/main` but *must not* be committed onto our upstream branch.

## 2. Identify head branch + commit range

```bash
gh pr view $PR --repo nexthop-ai/private-fboss \
    --json number,title,headRefName,baseRefName,body,labels,commits
```

Capture:
- `headRefName` — e.g. `benoit.copp-cpuqueues`
- `baseRefName` — often *another internal branch*, not `main` (the
  internal PR is stacked). For #743 the base was
  `benoit.loadbalancer-config` (PR #741).
- `commits[].oid` — the commit SHA(s) we'll cherry-pick. Most PRs
  are single-commit; occasionally there are multiple.

Upstream branch name = head with `<user>.` stripped:
`benoit.copp-cpuqueues` → `copp-cpuqueues`.

Cherry-pick range = `<baseRefName>..<headRefName>` — **not**
`origin/main..<headRefName>`. The latter would over-pick the parent
PRs in the stack (which often already have their own upstream PRs).

Save the original commit SHA(s) (`$ORIG_SHAS`) — needed in §3 if any
cherry-pick conflicts force the editor open.

## 3. Branch + cherry-pick + conflict resolution

```bash
BRANCH=copp-cpuqueues   # head with user prefix dropped
git checkout -b $BRANCH upstream/main
git cherry-pick origin/<baseRefName>..origin/<headRefName>
```

For NOS-6184..6188 (PR #743 onto upstream/main, parent PR #741 not yet
upstream-merged) the typical conflicts are:

| File(s) | Type | Resolver |
|---|---|---|
| `cmake/CliFboss2*.cmake` | source-list | auto-script |
| `fboss/cli/fboss2/BUCK` and `test/*/BUCK` | source-list | auto-script |
| `fboss/cli/fboss2/CmdListConfig.cpp` includes | source-list | auto-script |
| `fboss/cli/fboss2/CmdListConfig.cpp` registrations | logic | manual |
| `fboss/cli/fboss2/utils/CmdUtilsCommon.h` enum | logic | manual |

### 3a. Run the auto-resolver

```bash
mkdir -p .github/scripts
git show origin/main:.github/scripts/nh-fix-merge-conflicts.py >.github/scripts/nh-fix-merge-conflicts.py
chmod 755 .github/scripts/nh-fix-merge-conflicts.py
./.github/scripts/nh-fix-merge-conflicts.py
```

The script handles conflicts where every line in every conflict region
is a file path (cmake source lists, BUCK `srcs=`/`headers=`, the
include block at the top of `CmdListConfig.cpp`). It takes the union,
drops files that don't exist on disk (so the parent-stack registrations
that aren't here yet vanish cleanly), sorts, and stages each fully
resolved file.

Conflicts that mix file paths with non-path lines get reported as
`✗ Skipped conflict at line N (not all file paths)` and need manual
resolution.

### 3b. Manual resolution

For each remaining conflict, *keep only the change introduced by the
PR being upstreamed*. Drop entries that came along because they were
already in the parent-stack context. Two patterns:

- **`CmdListConfig.cpp` command-tree registration block** — keep the
  `{...}` entry for the new family, drop the parent-PR's entry. Watch
  the surrounding entry boundaries: the old code may end with
  `{"config",` opening the next entry, and your replacement may use
  the multi-line `{` form. Don't leave a stray `{"config",`.

- **`CmdUtilsCommon.h` `ObjectArgTypeId` enum** — keep only the new
  enum values introduced by this PR. Drop ones from earlier PRs in the
  stack that aren't yet upstream.

After every conflict is resolved:

```bash
git add -u
GIT_EDITOR=true git cherry-pick --continue
```

`GIT_EDITOR=true` makes the cherry-pick accept whatever's in the editor
without prompting. **This is when commit-message mangling happens** —
see §3c.

### 3c. Restore the original commit message after a conflicted continue

`git cherry-pick --continue` runs the editor with `--cleanup=strip` and
silently deletes lines starting with `#`. Internal commit bodies often
use Markdown-ish headings like `# Summary` and `# Test Plan`, which get
clipped. There's no `--cleanup` flag on cherry-pick to disable this.

After every conflicted `--continue`, immediately restore:

```bash
git commit --amend -n -C <orig-sha>   # -C copies message + authorship verbatim
```

`-n` skips pre-commit so we don't reformat the original code at this
stage. Compare with the original to confirm:

```bash
diff <(git log -1 --format="%B" <orig-sha>) <(git log -1 --format="%B")
```

If the original commit body had no `#`-prefixed lines (PR #743's case),
you'll get an empty diff and no fix is needed — but check, don't
assume. Clean (non-conflicted) cherry-picks don't go through the editor
and don't trip this.

### 3d. Clean up

```bash
rm .github/scripts/nh-fix-merge-conflicts.py
rmdir .github/scripts 2>/dev/null
```

`.github/scripts/nh-fix-merge-conflicts.py` exists on `origin/main`
but **not** on `upstream/main` — committing it upstream would leak it.

## 4. Bazel cherry-pick for build/test

The OSS upstream tree builds with cmake + BUCK; Bazel exists on the
`bazel-build` branch but isn't merged. Bring it in transiently:

```bash
git cherry-pick bazel-build
git show origin/benoit.blaze:fboss/oss/scripts/build-helper.py >fboss/oss/scripts/build-helper.py
git show origin/benoit.blaze:fboss/oss/scripts/fboss-build.env >fboss/oss/scripts/fboss-build.env
git add fboss/oss/scripts/build-helper.py
git commit --amend --no-edit
```

Notes:
- `fboss/oss/scripts/fboss-build.env` is **in `.gitignore`** — it lands
  in the working tree but `git status` won't show it. That's fine; it
  has to be on disk for `bazel.sh` to pick it up.
- Pre-commit's `ruff-format` will reformat `build-helper.py` on the
  amend. The commit aborts; re-`git add` and `git commit --amend
  --no-edit` once more to absorb the formatter's changes.

## 5. Build + test

For fboss2-dev CLI work (the typical case — confirmed if §1a found
spreadsheet rows for the PR):

```bash
./fboss/oss/scripts/bazel.sh build //fboss/cli/...
./fboss/oss/scripts/bazel.sh test //fboss/cli/...
```

For non-CLI work, build/test `//fboss/...` instead.

If anything fails, fix it and commit each fix as a *temporary* commit
on top of the bazel-build commit. We'll absorb them in §6.

Use `run_in_background` for `bazel.sh build` (~2 minutes cold,
seconds-to-tens-of-seconds warm with sccache) so you can do other prep
work in parallel.

## 6. Drop bazel-build, fold any fixups into the PR commit

Branch state at this point:
```
HEAD     fixup-N (temp; possibly zero of these)
         …
         fixup-1
         bazel-build (cherry-picked + amended)
         <PR commit, conflict-resolved>
upstream/main
```

If there are no fixups (clean §5), the simplest move is a hard-reset
to the PR commit's SHA:

```bash
git reset --hard <PR-commit-SHA>
```

If there are fixups, an interactive rebase: drop `bazel-build`, mark
each fixup as `fixup` under the PR commit:

```bash
git rebase -i upstream/main
# todo:
# pick   <PR-commit>
# fixup  <fixup-1>
# fixup  <fixup-2>
# (delete the bazel-build line)
```

End state: exactly one commit on top of `upstream/main`.

## 7. Sanitize commit message + assemble upstream PR body

The internal commit subject typically starts with one or more JIRA
ticket numbers (`NOS-XXXX[,NOS-YYYY,...]: <subject>`); occasionally
`NO-NOS:` or `NO-DEVX:`. Drop the prefix entirely.

In the body and PR description, scrub:

| Pattern | Replacement |
|---|---|
| `NOS-[0-9]+`, `NO-NOS`, `NO-DEVX` | drop |
| `goldXXX` | `NH-4010-F` |
| `wdgXXX` | `Wedge800` |
| `fbossXXX` | (look up via Glean) |
| `/tmp/fboss2_it_nos<NNN>` | `fboss2_integration_test` |
| `*.internal.nexthop.ai`, `*.k8s.us-west-1.nexthop.ai` | drop the host or the surrounding line |
| `bucket.internal.nexthop.ai`, `bazel-remote.k8s.us-west-1.nexthop.ai` | drop |
| Meta production device names (e.g. `rsw001_p001_m002_qzr1`, `fsw002...`) | role description (`RSW device`, `FSW device`) |

Even though the upstream is Meta's own repo, prefer the device *role*
(`RSW`, `FSW`, `RTSW`, `SSW`, ...) over the specific hostname — the
hostname leaks deployment-topology details and isn't what reviewers
need to evaluate the change.

Acceptable to leave alone:
- Author email `Benoit Sigoure <benoit@nexthop.ai>` — appears on every
  existing upstream Nexthop PR.

For the PR description (Markdown), additionally drop:
- The trailing `This PR is part of a stack: * #647 …` block (internal
  PR numbers).
- The `# Upstream required` checklist section (internal template
  artifact, irrelevant upstream).
- Any `Co-Authored-By:` trailer if upstream Nexthop PRs don't
  carry it (check `gh pr view <existing-nexthop-PR> --repo
  facebook/fboss --json commits`).

Apply:

```bash
git commit --amend --file=/tmp/upstream_commit_msg.txt
```

Tripwire check (the patch goes through `format-patch` so the only
expected match is the `From:` author header line):

```bash
git format-patch upstream/main --stdout > /tmp/full_patch.txt
grep -ciE 'NOS-[0-9]+|gold[0-9]+|fboss[0-9]{3}|wdg[0-9]+|nexthop\.ai|nexthop-internal|internal\.nexthop|k8s\.us-west|jira' /tmp/full_patch.txt
grep  -iE 'NOS-[0-9]+|gold[0-9]+|fboss[0-9]{3}|wdg[0-9]+|nexthop\.ai|nexthop-internal|internal\.nexthop|k8s\.us-west|jira' /tmp/full_patch.txt
```

The match count should be `1` (the `From:` line). Read each match to
confirm.

## 8. Push + open upstream PR

Push to `nexthop-ai` (the public fork). **Not** `origin` (the private
repo).

```bash
git push -u nexthop-ai $BRANCH
```

Title prefix:
- `[Nexthop][fboss2-dev]` if the PR appears in column N of the
  tracking spreadsheet — i.e. it's fboss2-dev CLI work.
- `[Nexthop]` for everything else (distro, platform manager, agent
  fixes, etc.).

```bash
gh pr create --repo facebook/fboss --base main \
    --head nexthop-ai:$BRANCH \
    --title '[Nexthop][fboss2-dev] <sanitized subject>' \
    --body-file /tmp/upstream_pr_body.md
```

`--head nexthop-ai:$BRANCH` is mandatory — without the `nexthop-ai:`
prefix `gh` looks for the branch on the upstream repo and 404s.

Capture the new PR number in `UPSTREAM_PR`.

## 9. Post-PR housekeeping

Three things, all required.

### 9a. Spreadsheet column M

For every row in the contiguous range that has the internal PR number
in column N, write a `HYPERLINK` formula in column M:

```bash
SHEET=1M8ZmQlmr028ks3WqalfSsmeYGNLc3sgC1OowICAPIJs
N=<row-count>          # max - min + 1
MIN=<spreadsheet-row-min>; MAX=<spreadsheet-row-max>
FORMULA="=HYPERLINK(\"https://github.com/facebook/fboss/pull/$UPSTREAM_PR\",\"#$UPSTREAM_PR\")"
python3 -c "import json; print(json.dumps({'values': [['$FORMULA']]*$N}))" > /tmp/m_body.json
gws sheets spreadsheets values update \
    --params "{\"spreadsheetId\":\"$SHEET\",\"range\":\"config-commands!M$MIN:M$MAX\",\"valueInputOption\":\"USER_ENTERED\"}" \
    --json "$(cat /tmp/m_body.json)" 2>&1 | tail -n +2
```

`USER_ENTERED` is mandatory — without it the cell shows the literal
formula text.

### 9b. Comment on the internal PR

```bash
gh pr comment $PR --repo nexthop-ai/private-fboss \
    --body "Upstream PR: https://github.com/facebook/fboss/pull/$UPSTREAM_PR"
```

### 9c. Disable internal upstream automation

Internal PRs labeled `Upstream Required` get auto-upstreamed by an
internal workflow on merge. Since we're upstreaming by hand, flip the
flag and remove the label so we don't get a duplicate.

Fetch the body, edit the checklist block, push it back, drop the label:

```bash
gh pr view $PR --repo nexthop-ai/private-fboss --json body \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['body'])" \
    > /tmp/internal_pr_body.txt
# Edit /tmp/internal_pr_body.txt: replace the "# Upstream required"
# block to set Yes -> [ ], No -> [x], and remove the
# "PR title is free of sensitive information" sub-checkbox section
# entirely (it's a Yes-only annex).
gh pr edit $PR --repo nexthop-ai/private-fboss \
    --remove-label "Upstream Required" \
    --body-file /tmp/internal_pr_body.txt
```

Verify:

```bash
gh pr view $PR --repo nexthop-ai/private-fboss --json labels   # should be []
```

## 10. Pitfalls observed

- **PR #741 had upstream PR #1105 already open** but column M was
  empty. The §1a spreadsheet check alone would have missed it — we
  caught it via §1b's `gh pr list --label nexthop` keyword scan. Always
  run both.
- **Cherry-picking `origin/main..<head>` over-picks the stack.** Use
  the PR's actual base branch as the lower bound (`origin/<baseRefName>..<head>`),
  otherwise you get parent-stack commits that are already upstream
  (or trying to be).
- **`fboss-build.env` is gitignored.** After overlaying it from
  `benoit.blaze`, `git status` shows nothing — that's fine, the file
  exists on disk and `bazel.sh` picks it up. Don't try to `git add` it.
- **Pre-commit reformats `build-helper.py` during the bazel-build
  amend.** The amend appears to fail; re-stage and re-amend.
- **`git cherry-pick --continue` strips `#`-prefixed lines.** Restore
  with `git commit --amend -n -C <orig-sha>`. Diff against the
  original after every conflicted `--continue`.
- **The `nh-fix-merge-conflicts.py` script must not be committed
  upstream.** It exists on `origin/main` only. Delete after running.
- **`gh pr create --head <branch>` 404s without the fork prefix.**
  Always pass `--head nexthop-ai:$BRANCH`.
- **Spreadsheet `valueInputOption` defaults to `RAW`.** A HYPERLINK
  formula written without `USER_ENTERED` shows up as literal text in
  the cell, not a link.
- **Don't forget `--remove-label "Upstream Required"`.** The body
  edit alone won't stop the internal workflow — the label is the
  trigger.
- **`gws` prefixes JSON output with a keyring-backend banner.** Pipe
  through `tail -n +2` before parsing or `python3` blows up on the
  first line.
- **The `From:` author header in `git format-patch` output is not a
  leak.** It's the standard email-format patch header; every existing
  upstream Nexthop PR has the same `<user>@nexthop.ai` author.
