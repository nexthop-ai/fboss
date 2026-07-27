#!/usr/bin/env bash
# Shared helpers for sync_upstream.sh and resync-sync-branch.sh.
# Source this file; do not execute it directly.
#
# Callers must define echo_info() and echo_debug() before sourcing, e.g.:
#   echo_info()  { echo "💡 INFO:  $*"; }
#   echo_debug() { :; }   # or a real debug logger

# Copy fboss/oss/stable_commits from the given ref over whatever the merge
# brought in.
#
# Upstream publishes the tarball naming a commit only after that commit, so
# taking the directory from the merged tree leaves latest_stable_hashes.tar.gz
# one stable behind.
#
# Pass the ref whose latest_stable_hashes.tar.gz the sync actually used.
copy_stable_commits_from_ref() {
  local ref=$1
  echo_info "Copying fboss/oss/stable_commits from ref: $ref"

  # Remove the directory first so snapshots rotated out at $ref do not linger.
  git rm -r -q -f fboss/oss/stable_commits 2>/dev/null || true
  git checkout "$ref" -- fboss/oss/stable_commits
  git add fboss/oss/stable_commits 2>/dev/null || true
}

# Resolve stable hash conflicts that arise when merging upstream.
#
# Reads the stable-hash tarballs from the working tree, so
# copy_stable_commits_from_ref must have run first. This resolves
# any merge conflicts in that directory as a side effect).
autoresolve_stable_hashes() {
  echo_info "Auto-resolving stable hash conflicts from the working tree"

  # Accept upstream versions of stable hashes
  git checkout --theirs build/deps/github_hashes/*/*-rev.txt 2>/dev/null || true

  # Extract the tarball from the working tree (populated by
  # copy_stable_commits_from_ref).
  local temp_dir
  temp_dir=$(mktemp -d)
  tar xf fboss/oss/stable_commits/latest_stable_hashes.tar.gz -C "$temp_dir"

  # Remove any hashes that were present in the previous tarball but dropped
  # from the latest one.
  if [[ -e fboss/oss/stable_commits/previous_stable_hashes.tar.gz ]]; then
    local prev_dir
    prev_dir=$(mktemp -d)
    tar xf fboss/oss/stable_commits/previous_stable_hashes.tar.gz -C "$prev_dir"

    comm -23 \
      <(find "$prev_dir/build/deps/github_hashes" -type f 2>/dev/null |
        sed "s|$prev_dir/||" | sort) \
      <(find "$temp_dir/build/deps/github_hashes" -type f 2>/dev/null |
        sed "s|$temp_dir/||" | sort) |
      while read -r removed_file; do
        if [[ -f $removed_file ]]; then
          echo_debug "Removing file no longer in stable hashes: $removed_file"
          git rm -f "$removed_file" 2>/dev/null || true
        fi
      done

    rm -rf "$prev_dir"
  fi

  # Sync files from tarball
  rsync -rc --ignore-existing "$temp_dir/build/deps/github_hashes/" \
    build/deps/github_hashes/ || true
  rsync -rc --existing "$temp_dir/build/deps/github_hashes/" \
    build/deps/github_hashes/ || true

  rm -rf "$temp_dir"

  git add build/deps/github_hashes 2>/dev/null || true
}
