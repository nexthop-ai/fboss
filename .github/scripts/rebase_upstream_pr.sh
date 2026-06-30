#!/usr/bin/env bash

# Rebase a stale upstream facebook/fboss PR onto a target commit (default: the
# latest stable commit) using our auto conflict resolver, so we can build-and-test
# it before the FBOSS team reviews it.  Designed to run in GitHub Actions, but the
# happy path is also runnable locally for debugging.
#
# Usage: rebase_upstream_pr.sh <upstream_pr_number> [rebase_onto]
#   <upstream_pr_number>  PR number in facebook/fboss (required)
#   [rebase_onto]         empty  -> latest stable commit (default)
#                         a name -> upstream branch (e.g. "main")
#                         a sha  -> that upstream commit
#
# Requires: GH_TOKEN with read access to facebook/fboss and push access to
# nexthop-ai/fboss (the public fork).  Outputs are written to $GITHUB_OUTPUT when
# set.  Remotes used: upstream -> facebook/fboss, nexthop-ai -> nexthop-ai/fboss.

set -euo pipefail

DEBUG=${DEBUG:-1}
INFO=${INFO:-1}

PR=${1:?"upstream PR number required"}
REBASE_ONTO=${2:-}

upstream_repo="facebook/fboss"
fork_repo="nexthop-ai/fboss"
upstream_base_branch="main"
run_id=${GITHUB_RUN_ID:-local}

# ─── Helpers ──────────────────────────────────────────────────────────────────
echo_debug() { ((DEBUG)) && echo "🐞 DEBUG: $*" || true; }
echo_info() { ((INFO)) && echo "💡 INFO:  $*" || true; }
echo_error() { echo "💥 ERROR:  $*" >&2; }

emit() {
  # emit <key> <value>  — write a workflow output (no-op when run locally)
  [[ -n ${GITHUB_OUTPUT:-} ]] && echo "$1=$2" >>"$GITHUB_OUTPUT" || true
}

rebase_in_progress() {
  [[ -d $(git rev-parse --git-path rebase-merge 2>/dev/null) ]] ||
    [[ -d $(git rev-parse --git-path rebase-apply 2>/dev/null) ]]
}

# Extract the latest stable commit SHA from the tarball on upstream/main.
# Mirrors .github/scripts/sync_upstream.sh (lines ~104-123); kept as a local copy
# to avoid a risky refactor of the live sync script.
get_stable_commit() {
  local ref content
  ref=$(git rev-list -1 "upstream/$upstream_base_branch" -- fboss/oss/stable_commits)
  content=$(git show "$ref:fboss/oss/stable_commits/latest_stable_hashes.tar.gz")
  if [[ $content =~ ^[a-zA-Z0-9_]+\.tar\.gz$ ]]; then
    git show "$ref:fboss/oss/stable_commits/$content" |
      tar -xzO --wildcards '*/fboss-rev.txt' | sed -n 's/^Subproject commit //p'
  else
    echo "$content" | tar -xzO --wildcards '*/fboss-rev.txt' | sed -n 's/^Subproject commit //p'
  fi
}

# Materialize our resolver from origin/main (the upstream tree doesn't have it),
# run it, then remove the untracked copy so it never lands in a pushed commit.
run_conflict_resolver() {
  mkdir -p .github/scripts
  git show origin/main:.github/scripts/nh-fix-merge-conflicts.py \
    >.github/scripts/nh-fix-merge-conflicts.py
  chmod 755 .github/scripts/nh-fix-merge-conflicts.py
  python3 .github/scripts/nh-fix-merge-conflicts.py || true
  rm -f .github/scripts/nh-fix-merge-conflicts.py
}

# ─── 1. Remotes ─────────────────────────────────────────────────────────────
: "${GH_TOKEN:?GH_TOKEN required (read facebook/fboss, push nexthop-ai/fboss)}"
export GH_TOKEN

git remote add upstream "https://github.com/$upstream_repo" 2>/dev/null ||
  git remote set-url upstream "https://github.com/$upstream_repo"
# Token embedded for push auth; it's a registered secret so Actions masks it in logs.
fork_url="https://x-access-token:${GH_TOKEN}@github.com/${fork_repo}.git"
git remote add nexthop-ai "$fork_url" 2>/dev/null ||
  git remote set-url nexthop-ai "$fork_url"

git fetch --no-tags upstream "$upstream_base_branch"

# ─── 2. Resolve PR -> branch + author ─────────────────────────────────────────
echo_info "Looking up upstream PR #$PR in $upstream_repo"
pr_json=$(gh pr view "$PR" --repo "$upstream_repo" \
  --json headRefName,headRefOid,headRepositoryOwner,author)

pr_branch=$(jq -r '.headRefName' <<<"$pr_json")
expected_oid=$(jq -r '.headRefOid' <<<"$pr_json")
head_owner=$(jq -r '.headRepositoryOwner.login' <<<"$pr_json")
author_login=$(jq -r '.author.login' <<<"$pr_json")

if [[ $head_owner != "nexthop-ai" ]]; then
  echo_error "PR #$PR head repo owner is '$head_owner', expected 'nexthop-ai'. Aborting."
  exit 1
fi

# Derive the internal username: drop a trailing -nexthop, lowercase, sanitize.
author_user=${author_login%-nexthop}
# printf (not echo) so a trailing newline isn't turned into a stray '-' by tr.
author_user=$(printf '%s' "$author_user" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_.-' '-')
[[ -z $author_user ]] && author_user="upstream"
test_branch="${author_user}.upstream-test.pr${PR}"
wip_branch="${pr_branch}-rebase-wip"
fork_test_ref="ci/upstream-rebase/pr-${PR}-${run_id}"

echo_info "PR branch:    $pr_branch (head $expected_oid)"
echo_info "Author:       $author_login -> user '$author_user'"
echo_info "Test branch:  $test_branch (private-fboss)"

git fetch --no-tags nexthop-ai "$pr_branch"
pr_head=$(git rev-parse FETCH_HEAD)

# ─── 3. Resolve rebase target ─────────────────────────────────────────────────
if [[ -z $REBASE_ONTO ]]; then
  target_ref=$(get_stable_commit)
  echo_info "Rebase target: latest stable commit $target_ref"
else
  target_ref=$REBASE_ONTO
  echo_info "Rebase target: requested '$target_ref'"
fi
# GitHub allows fetching a reachable SHA or a branch name the same way.
git fetch --no-tags upstream "$target_ref"
target=$(git rev-parse FETCH_HEAD)
echo_info "Rebase target resolves to $target"
emit target "$target"
emit pr_branch "$pr_branch"
emit author_user "$author_user"
emit test_branch "$test_branch"
emit expected_oid "$expected_oid"
emit wip_branch "$wip_branch"

# ─── 4-6. Rebase with auto-resolution ─────────────────────────────────────────
git checkout -B rebase-tmp "$pr_head"
merge_base=$(git merge-base "$target" "$pr_head")
orig_count=$(git rev-list --count "$merge_base..$pr_head")

has_conflicts=false
set +e
git rebase "$target"
rc=$?
set -e

iter=0
while [[ $rc -ne 0 ]] && rebase_in_progress; do
  iter=$((iter + 1))
  if [[ $iter -gt 200 ]]; then
    echo_error "Rebase did not converge after $iter steps; giving up."
    has_conflicts=true
    break
  fi

  run_conflict_resolver

  if git diff --name-only --diff-filter=U | grep -q .; then
    # The resolver couldn't fully resolve this step. Stage everything (including
    # conflict markers) so we can carry the rebase forward and hand a best-effort
    # branch off to a human; flag it so build-test is skipped.
    has_conflicts=true
    git add -A
  fi

  set +e
  GIT_EDITOR=true git rebase --continue
  rc=$?
  if [[ $rc -ne 0 ]] && rebase_in_progress; then
    # "continue" can fail when the resolved patch is now empty; skip it.
    GIT_EDITOR=true git rebase --skip
    rc=$?
  fi
  set -e
done

if rebase_in_progress; then
  echo_error "Rebase stuck mid-operation; aborting."
  git rebase --abort || true
  has_conflicts=true
fi

rebased_sha=$(git rev-parse HEAD)

# Belt-and-suspenders: scan for any residual conflict markers in the tree.
if git grep -lI '^<<<<<<< ' -- . >/dev/null 2>&1; then
  has_conflicts=true
fi

# ─── 7. Push result ───────────────────────────────────────────────────────────
if [[ $has_conflicts == true ]]; then
  conflicting_files=$(git grep -lI '^<<<<<<< ' -- . 2>/dev/null || true)
  echo_info "⚠️ Conflicts remain. Pushing best-effort branch '$wip_branch' for manual fix."
  echo "$conflicting_files"
  git push --force nexthop-ai "HEAD:refs/heads/$wip_branch"
  emit has_conflicts "true"
  {
    echo "conflicting_files<<EOF"
    echo "$conflicting_files"
    echo "EOF"
  } >>"${GITHUB_OUTPUT:-/dev/null}"
  exit 0
fi

new_count=$(git rev-list --count "$target..$rebased_sha")
echo_info "Rebased cleanly: $orig_count commit(s) -> $new_count commit(s) on $target"
emit orig_commit_count "$orig_count"
emit new_commit_count "$new_count"
if [[ $new_count -lt $orig_count ]]; then
  dropped=$((orig_count - new_count))
  echo_error "⚠️ $dropped commit(s) dropped during rebase ($orig_count → $new_count). Expected for already-merged patches; verify no important commits vanished."
  emit dropped_commits "true"
else
  emit dropped_commits "false"
fi

echo_info "Pushing clean rebased commit $rebased_sha to $fork_repo:$fork_test_ref"
git push --force nexthop-ai "HEAD:refs/heads/$fork_test_ref"

emit has_conflicts "false"
emit rebased_sha "$rebased_sha"
emit fork_test_ref "$fork_test_ref"
echo_info "✅ Rebase complete."
