#!/usr/bin/env bash
# Shared helpers for sync_upstream.sh and resync-sync-branch.sh.
# Source this file; do not execute it directly.
#
# Callers must define echo_info() and echo_debug() before sourcing, e.g.:
#   echo_info()  { echo "💡 INFO:  $*"; }
#   echo_debug() { :; }   # or a real debug logger

# Resolve stable hash conflicts that arise when merging upstream.
# Takes the upstream ref that last changed fboss/oss/stable_commits.
#
# Mirrors (and is the canonical source for) the logic in sync_upstream.sh.
autoresolve_stable_hashes() {
  local ref=$1
  echo_info "Auto-resolving stable hash conflicts using ref: $ref"

  # Remove files marked "deleted by them" (UD status)
  git status --porcelain=v1 fboss/oss/stable_commits 2>/dev/null |
    awk '$1=="UD" {print $2}' |
    xargs --no-run-if-empty git rm -- 2>/dev/null || true

  # Accept upstream versions of stable hashes
  git checkout --theirs fboss/oss/stable_commits \
    build/deps/github_hashes/*/*-rev.txt 2>/dev/null || true

  # Extract the tarball from the ref (not the working tree) so we get the
  # correct pinned versions that correspond to the stable commit.
  local temp_dir
  temp_dir=$(mktemp -d)

  local tarball_content
  tarball_content=$(git show "$ref:fboss/oss/stable_commits/latest_stable_hashes.tar.gz")
  if [[ $tarball_content =~ ^[a-zA-Z0-9_]+\.tar\.gz$ ]]; then
    echo_debug "latest_stable_hashes.tar.gz is a symlink to $tarball_content"
    git show "$ref:fboss/oss/stable_commits/$tarball_content" | tar xzf - -C "$temp_dir"
  else
    echo_debug "latest_stable_hashes.tar.gz is an actual tarball"
    echo "$tarball_content" | tar xzf - -C "$temp_dir"
  fi

  # Remove any hashes that were present in the previous tarball but dropped
  # from the latest one.
  local prev_tarball_content
  prev_tarball_content=$(git show "$ref:fboss/oss/stable_commits/previous_stable_hashes.tar.gz" 2>/dev/null) || true
  if [[ -n $prev_tarball_content ]]; then
    local prev_dir
    prev_dir=$(mktemp -d)
    if [[ $prev_tarball_content =~ ^[a-zA-Z0-9_]+\.tar\.gz$ ]]; then
      git show "$ref:fboss/oss/stable_commits/$prev_tarball_content" | tar xzf - -C "$prev_dir"
    else
      echo "$prev_tarball_content" | tar xzf - -C "$prev_dir"
    fi

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
