#!/usr/bin/env bash

# Rebase a stale upstream facebook/fboss PR onto a target commit (default: the
# latest stable commit) using our auto conflict resolver, so we can build-and-test
# it before the FBOSS team reviews it.  Designed to run in GitHub Actions, but the
# happy path is also runnable locally for debugging.
#
# Usage: rebase_upstream_pr.sh <upstream_pr_number> [rebase_onto] [resume_from_wip]
#   <upstream_pr_number>  PR number in facebook/fboss (required)
#   [rebase_onto]         empty  -> latest stable commit (default)
#                         a name -> upstream branch (e.g. "main")
#                         a sha  -> that upstream commit
#   [resume_from_wip]     "true" -> rebase from the PR's -rebase-wip branch
#                         (manually resolved conflicts) instead of the PR head.
#                         The PR branch is still only updated after a green
#                         build-and-test, same as a normal run.
#
# Requires: GH_TOKEN with read access to facebook/fboss and push access to
# nexthop-ai/fboss (the public fork, used only for fetching the PR branch and, on
# conflicts, pushing a WIP branch for manual resolution). The clean rebase gets our
# NH CI harness overlaid on top and is pushed straight to a convention-compliant
# branch on this checkout (private-fboss) -- build-and-test never touches the
# public fork.  Outputs are written to $GITHUB_OUTPUT when set.  Remotes used:
# upstream -> facebook/fboss, nexthop-ai -> nexthop-ai/fboss.

set -euo pipefail

DEBUG=${DEBUG:-1}
INFO=${INFO:-1}

PR=${1:?"upstream PR number required"}
REBASE_ONTO=${2:-}
RESUME_FROM_WIP=${3:-false}

upstream_repo="facebook/fboss"
fork_repo="nexthop-ai/fboss"
upstream_base_branch="main"
# Branch to source the NH harness files from. The checkout action leaves no
# origin/* remote-tracking refs and a detached HEAD, so use $GITHUB_REF_NAME.
nh_repo_branch=${GITHUB_REF_NAME:-main}

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

# The stable tarball pins an fboss sha1 together with the dependency shas and
# manifests it was validated with; they must be used as a set. Materialize the
# tarball from the given commit into a temp file so the same copy that names
# the rebase target also supplies the dep pins during the overlay.
materialize_stable_tarball() {
  local ref=$1 out
  out=$(mktemp --suffix=.tar.gz)
  git show "$ref:fboss/oss/stable_commits/latest_stable_hashes.tar.gz" >"$out"
  # Some revisions store a pointer file naming the real tarball.
  if ! gzip -t "$out" 2>/dev/null; then
    git show "$ref:fboss/oss/stable_commits/$(cat "$out")" >"$out"
  fi
  echo "$out"
}

# Extract the stable commit SHA from a materialized tarball. Mirrors
# .github/scripts/sync_upstream.sh (lines ~104-123).
get_stable_commit() {
  tar -xzOf "$1" --wildcards '*/fboss-rev.txt' | sed -n 's/^Subproject commit //p'
}

# Materialize our resolver from $nh_repo_branch (the upstream tree doesn't have
# it), run it, then remove the untracked copy so it never lands in a pushed
# commit.
run_conflict_resolver() {
  mkdir -p .github/scripts
  git show "$nh_repo_branch:.github/scripts/nh-fix-merge-conflicts.py" \
    >.github/scripts/nh-fix-merge-conflicts.py
  chmod 755 .github/scripts/nh-fix-merge-conflicts.py
  python3 .github/scripts/nh-fix-merge-conflicts.py || true
  rm -f .github/scripts/nh-fix-merge-conflicts.py
}

# Overlay our internal CI harness onto the clean rebase (bare upstream trees have
# none of it) as one extra commit, so the pushed branch is build-test-ready without
# a second round trip through the public fork.
#
# This rm's/recreates .github, which contains this very script -- that's fine:
# Linux keeps this process's already-open fd on the script pointing at the old
# (now unlinked) inode, so bash keeps executing the original content regardless
# of what `git checkout` writes to that path afterward.
overlay_nh_harness() {
  local p
  # From build/fbcode_builder take only our getdeps fork (S3 cache, fetcher,
  # hashed install dirs); manifests, patches, and CMake helpers stay at the
  # rebase target's versions.
  for p in .github fboss/oss/docker fboss/oss/scripts fboss-sim fboss/oss/stable_commits \
    build/fbcode_builder/getdeps.py build/fbcode_builder/getdeps; do
    rm -rf "$p"
    git checkout "$nh_repo_branch" -- "$p"
  done
  # Restore the manifests and github_hashes shas from the same tarball that
  # named the rebase target, so the dep pins are exactly the set the stable
  # commit was validated with.
  rm -rf build/deps/github_hashes build/fbcode_builder/manifests
  tar xzf "$stable_tarball" --wildcards \
    'build/deps/github_hashes/*' 'build/fbcode_builder/manifests/*'
  # docker-build.py's use_stable_hashes() re-extracts the pins from the tree's
  # tarball at container start; put the same tarball in the tree so that
  # re-extraction can't reintroduce a stale set.
  cp "$stable_tarball" fboss/oss/stable_commits/latest_stable_hashes.tar.gz
  git add -A
  git commit --no-verify -m "CI: build-test upstream PR ${PR} with NH harness (do not merge)"
  # Internal fixes the pure-upstream tree needs but that were never upstreamed.
  # Applied after rebased_sha capture, so they never reach the real PR branch:
  #   d09a2fbf: fake SAI initializes FakePort members; unfixed agents SEGV (#621)
  #   c7d40884: distro_cli docker test self-skips when docker is absent
  local fix
  for fix in d09a2fbfe633fedbac25bd083e75cf2fa8122bad c7d40884e67522873e44206e6ac238c8e76a4751; do
    git cherry-pick -x "$fix" || {
      echo_error "cherry-pick of internal fix $fix failed; resolve or drop it"
      git cherry-pick --abort || true
      exit 1
    }
  done
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

echo_info "PR branch:    $pr_branch (head $expected_oid)"
echo_info "Author:       $author_login -> user '$author_user'"
echo_info "Test branch:  $test_branch (private-fboss)"

git fetch --no-tags nexthop-ai "$pr_branch"
pr_head=$(git rev-parse FETCH_HEAD)

# Resume mode: rebase from the manually resolved wip branch instead of the PR
# head. expected_oid stays the PR head captured above, so the final force-push
# still aborts if someone moved the PR branch while the wip fix was in flight.
if [[ $RESUME_FROM_WIP == true ]]; then
  if ! git fetch --no-tags nexthop-ai "$wip_branch"; then
    echo_error "resume_from_wip requested but '$wip_branch' does not exist on $fork_repo"
    exit 1
  fi
  pr_head=$(git rev-parse FETCH_HEAD)
  echo_info "Resuming from wip branch $wip_branch (head $pr_head)"
fi

# ─── 3. Resolve rebase target ─────────────────────────────────────────────────
if [[ -z $REBASE_ONTO ]]; then
  stable_tarball=$(materialize_stable_tarball \
    "$(git rev-list -1 "upstream/$upstream_base_branch" -- fboss/oss/stable_commits)")
  target_ref=$(get_stable_commit "$stable_tarball")
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
if [[ -n $REBASE_ONTO ]]; then
  # Explicit target: no tarball names it, so take the newest one in the
  # target's own tree — the closest matching set of dep pins.
  stable_tarball=$(materialize_stable_tarball \
    "$(git rev-list -1 "$target" -- fboss/oss/stable_commits)")
fi
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
  echo "$conflicting_files"
  if [[ $RESUME_FROM_WIP == true ]]; then
    # Resume run found the wip branch itself still has conflict markers (the
    # manual resolution was incomplete). Leave the branch exactly as pushed —
    # never rewrite manual work — and let the notify job ask for another pass.
    echo_error "⚠️ wip branch '$wip_branch' still contains conflict markers; leaving it untouched."
  else
    echo_info "⚠️ Conflicts remain. Pushing best-effort branch '$wip_branch' for manual fix."
    git push --force nexthop-ai "HEAD:refs/heads/$wip_branch"
  fi
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

# Log the PR's net diff on the rebase target: the test branch is deleted on
# cleanup, so this is the only record of what the rebase actually produced.
echo_info "Diff applied by the rebase ($target..$rebased_sha):"
git diff --stat "$target" "$rebased_sha"
git diff "$target" "$rebased_sha"

echo_info "Overlaying NH CI harness onto the clean rebase"
overlay_nh_harness

echo_info "Pushing rebase + NH harness to private-fboss:$test_branch"
git push --force origin "HEAD:refs/heads/$test_branch"

emit has_conflicts "false"
emit rebased_sha "$rebased_sha"
echo_info "✅ Rebase complete."
