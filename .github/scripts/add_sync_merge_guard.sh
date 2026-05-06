#!/bin/bash
# Adds an unresolved review thread to a sync PR so it cannot be merged via
# the green button. The /merge command (nh-pr-merge-command.yml) is
# responsible for resolving this thread before merging the PR.
#
# This relies on the "Require conversation resolution before merging" branch
# protection rule being enabled on main.
#
# Usage: add_sync_merge_guard.sh <pr_url_or_number>

set -euo pipefail

PR_REF="${1:?usage: $0 <pr_url_or_number>}"
PR_NUMBER="${PR_REF##*/}"

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"

PR_NODE_ID=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}" --jq '.node_id')
FILE_PATH=$(gh api "repos/${REPO}/pulls/${PR_NUMBER}/files" --jq '.[0].filename')

if [[ -z $FILE_PATH || $FILE_PATH == "null" ]]; then
  echo "❌ Could not determine a file path on PR #${PR_NUMBER} to anchor the merge guard thread"
  exit 1
fi

# Marker on the first line is used by nh-pr-merge-command.yml to find and
# resolve this thread. Do not change without updating the merge workflow.
read -r -d '' BODY <<'EOF' || true
🚦 **Merge guard for sync PR — do not resolve manually**

This PR must be merged using the `/merge` command. Do not resolve this conversation manually.
EOF

gh api graphql \
  -f query='
    mutation($pullRequestId: ID!, $body: String!, $path: String!) {
      addPullRequestReviewThread(input: {
        pullRequestId: $pullRequestId,
        body: $body,
        path: $path,
        subjectType: FILE
      }) {
        thread { id }
      }
    }
  ' \
  -f pullRequestId="$PR_NODE_ID" \
  -f body="$BODY" \
  -f path="$FILE_PATH" \
  >/dev/null

echo "✅ Added merge guard review thread on PR #${PR_NUMBER} (anchored to ${FILE_PATH})"
