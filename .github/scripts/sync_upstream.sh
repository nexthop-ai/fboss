#!/usr/bin/env bash

# Sync script for private-fboss to pull latest stable commit from upstream facebook/fboss
# This script is designed to run in GitHub Actions
# Exit codes:
#   0 - Success (synced and pushed to main, or created PR, or no changes needed)
#   1 - Error occurred

set -euo pipefail

base_branch="main"
upstream_base_branch="main"
upstream_repo="facebook/fboss"

# shellcheck source=sync-lib.sh
source "${BASH_SOURCE%/*}/sync-lib.sh"

# Setup upstream remote and fetch
setup_upstream_and_fetch() {
  local url=$1 branch=$2
  git remote add upstream "$url" 2>/dev/null || git remote set-url upstream "$url"
  git fetch upstream "$branch"
  git fetch origin "$base_branch"
}

# ─── Main Script ──────────────────────────────────────────────────────────────

TIMESTAMP=$(date '+%Y-%m-%d-%H-%M')
sync_branch="sync-fboss-upstream-${TIMESTAMP}"

echo_info "Starting upstream sync"
echo_info "Base branch: $base_branch"
echo_info "Sync branch: $sync_branch"

# Setup upstream and fetch
setup_upstream_and_fetch "https://github.com/$upstream_repo" "$upstream_base_branch"

# Find the commit that last changed fboss/oss/stable_commits
stable_commits_ref=$(git rev-list -1 upstream/$upstream_base_branch -- fboss/oss/stable_commits)
echo_info "Stable commits ref: $stable_commits_ref"

# Extract the stable commit SHA1 from the tarball
tarball_content=$(git show "$stable_commits_ref:fboss/oss/stable_commits/latest_stable_hashes.tar.gz")

if [[ $tarball_content =~ ^[a-zA-Z0-9_]+\.tar\.gz$ ]]; then
  echo_debug "latest_stable_hashes.tar.gz is a symlink to $tarball_content"
  stable_commit=$(git show "$stable_commits_ref:fboss/oss/stable_commits/$tarball_content" |
    tar -xzO --wildcards '*/fboss-rev.txt' |
    sed -n 's/^Subproject commit //p')
else
  echo_debug "latest_stable_hashes.tar.gz is an actual tarball"
  stable_commit=$(echo "$tarball_content" |
    tar -xzO --wildcards '*/fboss-rev.txt' |
    sed -n 's/^Subproject commit //p')
fi

echo_info "Stable commit to sync to: $stable_commit"

# Check if we're already at this commit or ahead
if git merge-base --is-ancestor "$stable_commit" HEAD; then
  echo_info "✅ Already up to date with stable commit $stable_commit"
  exit 0
fi

# Create sync branch from current main
git checkout -B "$sync_branch" "origin/$base_branch"

# Attempt merge
prev_sha1=$(git rev-parse HEAD)
has_conflicts=false

commit_msg="Sync with upstream stable commit $stable_commit"

if git merge "$stable_commit" -m "$commit_msg"; then
  cur_sha1=$(git rev-parse HEAD)
  if [[ $prev_sha1 == "$cur_sha1" ]]; then
    echo_info "✅ No new changes to merge from upstream"
    git checkout "$base_branch"
    git branch -d "$sync_branch" 2>/dev/null || true
    exit 0
  fi
  echo_info "✅ Merge successful with no conflicts"

  # Overwrite fboss/oss/stable_commits with the version this sync actually
  # used
  copy_stable_commits_from_ref "$stable_commits_ref"
  if ! git diff --cached --quiet; then
    git commit --amend --no-edit --no-verify
  fi
else
  echo_info "⚠️ Merge conflicts detected, attempting auto-resolution..."

  # Overwrite fboss/oss/stable_commits with the version this sync actually
  # used
  copy_stable_commits_from_ref "$stable_commits_ref"
  autoresolve_stable_hashes

  # Auto-resolve file list conflicts in CMake and BUCK files
  echo_info "Auto-resolving file list conflicts in CMake and BUCK files..."
  .github/scripts/nh-fix-merge-conflicts.py

  # Check if there are still unresolved conflicts after auto-resolution
  remaining_conflicts=$(git diff --name-only --diff-filter=U)
  if [[ -n $remaining_conflicts ]]; then
    has_conflicts=true
    echo_info "⚠️ Some conflicts remain unresolved:"
    echo "$remaining_conflicts"
  fi

  git add -A
  git commit --no-verify -m "$commit_msg"
fi

# Output variables for the workflow
echo "sync_branch=$sync_branch" >>"$GITHUB_OUTPUT"
echo "stable_commit=$stable_commit" >>"$GITHUB_OUTPUT"
# HEAD here is the merge commit produced by `git merge "$stable_commit"` (or the
# auto-resolve commit). This is what `push-to-main` will publish, and what any
# pre-merge gate (e.g. monobuild + smoke) needs to validate. `stable_commit` is
# only one parent of this merge and is not sufficient to test on its own.
# Capture into a variable first so `set -e` aborts on `git rev-parse` failure
# (which it doesn't do for command substitution embedded in `echo "x=$(...)"`).
submodule_commit=$(git rev-parse HEAD)
echo "submodule_commit=$submodule_commit" >>"$GITHUB_OUTPUT"

if [[ $has_conflicts == "false" ]]; then
  echo_info "🚀 No conflicts - will push directly to $base_branch"
  echo "push_direct=true" >>"$GITHUB_OUTPUT"
else
  echo_info "📝 Conflicts present - will create PR for manual resolution"
  echo "push_direct=false" >>"$GITHUB_OUTPUT"
  # Output conflicting files for PR body
  echo "conflicting_files<<EOF" >>"$GITHUB_OUTPUT"
  echo "$remaining_conflicts" >>"$GITHUB_OUTPUT"
  echo "EOF" >>"$GITHUB_OUTPUT"
fi

echo_info "✅ Sync script completed successfully"
