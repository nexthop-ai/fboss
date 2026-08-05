#!/usr/bin/env bash
# Shared helpers for sync_upstream.sh, resync-sync-branch.sh, and
# rebase_upstream_pr.sh. Source this file; do not execute it directly.
#
# Provides default echo_debug/echo_info/echo_error logging helpers. A caller
# may define its own before sourcing to override (e.g. resync-sync-branch.sh
# routes echo_info through its own info() function) -- the declare -F guards
# below only install a default when the caller hasn't already defined one.
if ! declare -F echo_debug >/dev/null; then
  DEBUG=${DEBUG:-1}
  echo_debug() { ((DEBUG)) && echo "🐞 DEBUG: $*" || true; }
fi
if ! declare -F echo_info >/dev/null; then
  INFO=${INFO:-1}
  echo_info() { ((INFO)) && echo "💡 INFO:  $*" || true; }
fi
if ! declare -F echo_error >/dev/null; then
  echo_error() { echo "💥 ERROR:  $*" >&2; }
fi

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

# The stable tarball pins an fboss sha1 together with the dependency shas and
# manifests it was validated with; they must be used as a set. Materialize the
# tarball from the given commit into a temp file so the same copy that names
# the rebase/build target also supplies the dep pins during the overlay.
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

# Extract the stable commit SHA from a materialized tarball.
get_stable_commit() {
  tar -xzOf "$1" --wildcards '*/fboss-rev.txt' | sed -n 's/^Subproject commit //p'
}

# Overlay our internal CI harness onto a bare upstream tree (which has none of
# it) as one extra commit, so the branch is build-test-ready with the cmake
# harness. Then cherry-pick internal-only fixes the pure-upstream tree needs
# to pass tests but that were never upstreamed.
#
# Usage: overlay_nh_harness <harness_ref> <stable_tarball> <commit_msg>
#   <harness_ref>    ref to take the harness files from (e.g. origin/main)
#   <stable_tarball> tarball from materialize_stable_tarball, supplying the
#                    dep pins validated with the build target
#   <commit_msg>     message for the do-not-merge harness commit
#
# May rm/recreate .github, which can contain the calling script -- that's
# fine: Linux keeps the process's open fd on the old inode, so bash keeps
# executing the original content.
overlay_nh_harness() {
  local harness_ref=$1 stable_tarball=$2 commit_msg=$3
  local p
  # From build/fbcode_builder take only our getdeps fork (S3 cache, fetcher,
  # hashed install dirs); manifests, patches, and CMake helpers stay at the
  # build target's versions.
  for p in .github fboss/oss/docker fboss/oss/scripts fboss-sim fboss/oss/stable_commits \
    build/fbcode_builder/getdeps.py build/fbcode_builder/getdeps; do
    rm -rf "$p"
    git checkout "$harness_ref" -- "$p"
  done
  # Restore the manifests and github_hashes shas from the same tarball that
  # named the build target, so the dep pins are exactly the set the stable
  # commit was validated with.
  rm -rf build/deps/github_hashes build/fbcode_builder/manifests
  tar xzf "$stable_tarball" --wildcards \
    'build/deps/github_hashes/*' 'build/fbcode_builder/manifests/*'
  # docker-build.py's use_stable_hashes() re-extracts the pins from the tree's
  # tarball at container start; put the same tarball in the tree so that
  # re-extraction can't reintroduce a stale set.
  cp "$stable_tarball" fboss/oss/stable_commits/latest_stable_hashes.tar.gz
  git add -A
  git commit --no-verify -m "$commit_msg"
  # Internal fixes, applied on top so they can be dropped before anything is
  # pushed to a real upstream PR branch:
  #   d09a2fbf: fake SAI initializes FakePort members; unfixed agents SEGV (#621)
  #   c7d40884: distro_cli docker test self-skips when docker is absent
  local fix
  for fix in d09a2fbfe633fedbac25bd083e75cf2fa8122bad c7d40884e67522873e44206e6ac238c8e76a4751; do
    git cherry-pick -x "$fix" || {
      echo_error "cherry-pick of internal fix $fix failed; resolve or drop it"
      git cherry-pick --abort || true
      return 1
    }
  done
}
