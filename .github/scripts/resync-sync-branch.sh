#!/usr/bin/env bash
#
# Resync a sync-fboss-upstream-* branch after origin/main has moved ahead.
#
# A sync branch has this structure:
#   HEAD~N   = merge commit (parent1 = our old main, parent2 = upstream stable)
#   HEAD~N-1 ]
#   ...      ] one or more "fix" commits on top of the merge commit
#   HEAD     ]
#
# git cannot rebase a merge commit, so instead we recreate the merge commit
# from scratch on top of the current origin/main (updating the first parent
# while keeping the same upstream stable commit as the second parent), then
# cherry-pick all fix commits on top, in order.
#
# At each stage where conflicts arise, nh-fix-merge-conflicts.py is run to
# auto-resolve CMake/BUCK file-list conflicts.
#
# Usage:
#   .github/scripts/resync-sync-branch.sh [--dry-run]
#
# Exit codes:
#   0 - Success (force-pushed, or already up to date)
#   1 - Fatal error
#   2 - Resynced but unresolved conflicts remain (manual intervention needed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
  --dry-run) DRY_RUN=1 ;;
  *)
    echo "Unknown argument: $arg" >&2
    exit 1
    ;;
  esac
done

info() { echo "💡 INFO:  $*"; }
warn() { echo "⚠️  WARN:  $*"; }
error() { echo "💥 ERROR: $*" >&2; }
die() {
  error "$*"
  exit 1
}

# ─── Conflict tracking ───────────────────────────────────────────────────────
# Every path git reports as unmerged gets recorded here initially. Most merge
# conflicts are resolved by replaying thee fix commits. The final list is
# written to CONFLICT_LIST_FILE, one path per line.
CONFLICT_LIST_FILE="${RESYNC_CONFLICT_LIST:-/tmp/resync-conflicted-files.txt}"
: >"$CONFLICT_LIST_FILE"

conflicted_candidates=()

record_conflicts() {
  local path
  while IFS= read -r path; do
    if [[ -n $path ]]; then
      conflicted_candidates+=("$path")
    fi
  done <<<"$1"
  # Never let a blank line make the loop's last command fail: under `set -e`
  # that would abort the resync just before the push.
  return 0
}

# Compatibility shims so sync-lib.sh functions can call echo_info/echo_debug.
echo_info() { info "$@"; }
echo_debug() { :; }

# shellcheck source=sync-lib.sh
source "${SCRIPT_DIR}/sync-lib.sh"

# ─── Validate we're on a sync branch ─────────────────────────────────────────
current_branch=$(git rev-parse --abbrev-ref HEAD)
[[ $current_branch == sync-fboss-upstream-* ]] ||
  die "Must be on a sync-fboss-upstream-* branch (current: $current_branch)"
info "Branch: $current_branch"

# ─── Find the merge commit by walking back from HEAD ─────────────────────────
# The merge commit is the first commit reachable from HEAD that has 2 parents.
# All commits between HEAD (exclusive) and the merge commit (inclusive) are
# the "fix" commits to be replayed after recreating the merge.
merge_commit=""
depth=0
ref="HEAD"
while true; do
  num_parents=$(git cat-file -p "$ref" | grep -c "^parent ")
  if [[ $num_parents -eq 2 ]]; then
    merge_commit=$(git rev-parse "$ref")
    break
  elif [[ $num_parents -eq 0 ]]; then
    die "Reached a root commit without finding a merge commit"
  fi
  depth=$((depth + 1))
  ref="HEAD~${depth}"
done

[[ -n $merge_commit ]] || die "No merge commit found on this branch"

upstream_commit=$(git rev-parse "${merge_commit}^2")
old_first_parent=$(git rev-parse "${merge_commit}^1")
merge_msg=$(git log --format=%B -1 "$merge_commit")

info "Merge commit     : $merge_commit (HEAD~${depth})"
info "Upstream commit  : $upstream_commit"
info "Old first parent : $old_first_parent"

# Collect fix commits oldest-first (commits above the merge commit).
# If depth == 0, there are no fix commits (HEAD IS the merge commit).
fix_commits=()
if [[ $depth -gt 0 ]]; then
  while IFS= read -r sha; do
    fix_commits+=("$sha")
  done < <(git log --format=%H --reverse "${merge_commit}..HEAD")
fi
info "Fix commits      : ${#fix_commits[@]} commit(s) to replay"
for sha in "${fix_commits[@]}"; do
  info "  $(git log --format='%h %s' -1 "$sha")"
done

# ─── Check if resync is needed ────────────────────────────────────────────────
git fetch origin main
new_first_parent=$(git rev-parse origin/main)
info "New first parent : $new_first_parent (origin/main)"

if [[ $old_first_parent == "$new_first_parent" ]]; then
  info "✅ Already up to date — origin/main has not moved"
  exit 0
fi
info "origin/main moved: $old_first_parent → $new_first_parent"

[[ $DRY_RUN -eq 0 ]] || {
  info "[dry-run] Would resync — exiting"
  exit 0
}

# ─── Clean up any stale in-progress operations ───────────────────────────────
git cherry-pick --abort 2>/dev/null || true
git merge --abort 2>/dev/null || true

# ─── Helper: cherry-pick one commit, auto-resolving conflicts ────────────────
cherry_pick_with_autoresolve() {
  local sha="$1"
  local subject
  subject=$(git log --format=%s -1 "$sha")
  info "Cherry-picking $sha ($subject)..."

  # Disable rerere: if it has a recorded resolution for the same conflict it
  # auto-applies, the result becomes an empty diff, and git drops the commit.
  # Disable hooks via core.hooksPath so a failing pre-commit doesn't block
  # commits that intentionally contain conflict markers.
  local GIT="git -c core.hooksPath=/dev/null -c rerere.enabled=false"

  local ok=true
  $GIT cherry-pick --no-edit "$sha" || ok=false

  if ! $ok; then
    info "⚠️ Cherry-pick conflicts — running nh-fix-merge-conflicts.py..."
    "$SCRIPT_DIR/nh-fix-merge-conflicts.py" || true

    local still_conflicted
    still_conflicted=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
    git add -u # not -A: avoid staging untracked files

    if [[ -n $still_conflicted ]]; then
      warn "Unresolved conflicts committed with markers (manual fix needed):"
      echo "$still_conflicted"
      record_conflicts "$still_conflicted"
      # Return 2 so the log reads clearly; the caller ignores it, since whether
      # these markers survive is settled by the step 3 re-check.
      GIT_EDITOR=true $GIT cherry-pick --continue
      return 2
    fi

    GIT_EDITOR=true $GIT cherry-pick --continue
  fi
  return 0
}

# ─── Step 1: recreate the merge commit on top of origin/main ─────────────────
info "Resetting $current_branch to origin/main..."
git reset --hard origin/main

info "Merging upstream commit $upstream_commit..."
has_merge_conflicts=false
# --no-commit prevents auto-commit even on a clean merge so we can always
# checkout the upstream hash files before committing (see below).
git merge --no-ff --no-commit "$upstream_commit" || has_merge_conflicts=true

# Use fboss/oss/stable_commits from the original merge commit: the sync that
# created this branch already copied the tarball it actually used (the tree at
# $upstream_commit carries the *previous* stable tarball). This
# resolves any merge conflicts under fboss/oss/stable_commits, and must run
# before autoresolve_stable_hashes, which reads the tarballs from the working
# tree.
copy_stable_commits_from_ref "$merge_commit"

if $has_merge_conflicts; then
  info "⚠️ Merge had conflicts — running auto-resolution..."

  autoresolve_stable_hashes

  info "Running nh-fix-merge-conflicts.py..."
  "$SCRIPT_DIR/nh-fix-merge-conflicts.py"

  still_conflicted=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
  if [[ -n $still_conflicted ]]; then
    warn "Still-conflicted after auto-resolution (committing with markers):"
    echo "$still_conflicted"
    record_conflicts "$still_conflicted"
  fi
fi

# Always take build/deps/github_hashes directly from the upstream commit's
# tree.  git's 3-way merge picks ours when only we changed a hash (upstream
# held it steady); autoresolve_stable_hashes has a similar limitation here:
# it reads the tarballs copied from $merge_commit, which for older sync
# branches may predate the current upstream stable values.
git checkout "$upstream_commit" -- build/deps/github_hashes/ 2>/dev/null || true
git add build/deps/github_hashes/ 2>/dev/null || true

# Use `git add -u` (not -A) to avoid staging untracked files (e.g. large
# binaries in the working tree that are not part of the repo).
git add -u
git commit --no-verify -m "$merge_msg"

info "New merge commit : $(git rev-parse HEAD)"

# ─── Step 2: replay all fix commits ──────────────────────────────────────────
for sha in "${fix_commits[@]}"; do
  cherry_pick_with_autoresolve "$sha" || true
done

# ─── Step 3: work out which files are STILL conflicted ───────────────────────
# Re-check each candidate against the tree we are about to push instead of
# trusting the per-stage warnings. Cherry-picks cut both ways: they resolve
# files that conflicted during the merge, and they can leave markers of their
# own. Only the end state is worth reporting or acting on.
remaining_conflicts=()
if [[ ${#conflicted_candidates[@]} -gt 0 ]]; then
  while IFS= read -r path; do
    [[ -f $path ]] || continue
    if grep -qE '^<{7} ' "$path"; then
      remaining_conflicts+=("$path")
    fi
  done < <(printf '%s\n' "${conflicted_candidates[@]}" | sort -u)
fi

if [[ ${#remaining_conflicts[@]} -gt 0 ]]; then
  printf '%s\n' "${remaining_conflicts[@]}" >"$CONFLICT_LIST_FILE"
fi

# ─── Step 4: force-push ───────────────────────────────────────────────────────
info "Force-pushing $current_branch..."
git push --force-with-lease origin "$current_branch"

if [[ ${#remaining_conflicts[@]} -eq 0 ]]; then
  info "✅ Resync complete!"
  exit 0
fi

# Prefix each path with the WARN marker so the failure-path comment, which
# greps for WARN lines, picks up the file names too.
warn "Files still containing conflict markers (${#remaining_conflicts[@]}):"
for path in "${remaining_conflicts[@]}"; do
  warn "  $path"
done
warn "⚠️ Resynced but manual conflict resolution needed in the files above."
exit 2
