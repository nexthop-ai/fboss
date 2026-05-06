#!/bin/bash
# Finds and resolves the merge guard review thread(s) added to a sync PR by
# add_sync_merge_guard.sh. This must run before the actual merge API call,
# because branch protection's "Require conversation resolution before
# merging" rule rejects merges with unresolved review threads.
#
# Usage: resolve_sync_merge_guard.sh <pr_number>

set -euo pipefail

PR_NUMBER="${1:?usage: $0 <pr_number>}"
REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
OWNER="${REPO%/*}"
NAME="${REPO#*/}"

# Marker must match the first line of the body in add_sync_merge_guard.sh.
MARKER="🚦 **Merge guard for sync PR — do not resolve manually**"

threads_json=$(gh api graphql \
  -F owner="$OWNER" -F repo="$NAME" -F pr="$PR_NUMBER" \
  -f query='
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 1) { nodes { body } }
            }
          }
        }
      }
    }
  ')

thread_ids=$(jq -r --arg marker "$MARKER" '
  .data.repository.pullRequest.reviewThreads.nodes[]
  | select(.isResolved == false)
  | select(.comments.nodes[0].body | startswith($marker))
  | .id
' <<<"$threads_json")

if [[ -z $thread_ids ]]; then
  echo "ℹ️ No unresolved merge guard threads found on PR #${PR_NUMBER}"
  exit 0
fi

while IFS= read -r thread_id; do
  [[ -z $thread_id ]] && continue
  echo "Resolving merge guard thread: $thread_id"
  gh api graphql \
    -f query='
      mutation($threadId: ID!) {
        resolveReviewThread(input: { threadId: $threadId }) {
          thread { id isResolved }
        }
      }
    ' \
    -f threadId="$thread_id" \
    >/dev/null
done <<<"$thread_ids"

echo "✅ Resolved merge guard thread(s) on PR #${PR_NUMBER}"
