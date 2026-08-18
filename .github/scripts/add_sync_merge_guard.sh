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

# The thread must be created inside a review and that review must then be
# submitted: addPullRequestReviewThread only ever adds to a *pending* review,
# and a pending review is invisible to everyone but its author and does not
# count towards "Require conversation resolution before merging".
REVIEW_ID=$(gh api graphql \
  -f query='
    mutation($pullRequestId: ID!) {
      addPullRequestReview(input: { pullRequestId: $pullRequestId }) {
        pullRequestReview { id }
      }
    }
  ' \
  -f pullRequestId="$PR_NODE_ID" \
  --jq '.data.addPullRequestReview.pullRequestReview.id')

if [[ -z $REVIEW_ID || $REVIEW_ID == "null" ]]; then
  echo "❌ Could not create a pending review on PR #${PR_NUMBER}"
  exit 1
fi

# Don't leave a dangling pending review behind if a later step fails.
submitted=0
cleanup() {
  if [[ $submitted -eq 1 ]]; then
    return 0
  fi
  gh api graphql \
    -f query='
      mutation($pullRequestReviewId: ID!) {
        deletePullRequestReview(input: { pullRequestReviewId: $pullRequestReviewId }) {
          pullRequestReview { id }
        }
      }
    ' \
    -f pullRequestReviewId="$REVIEW_ID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

gh api graphql \
  -f query='
    mutation($pullRequestReviewId: ID!, $body: String!, $path: String!) {
      addPullRequestReviewThread(input: {
        pullRequestReviewId: $pullRequestReviewId,
        body: $body,
        path: $path,
        subjectType: FILE
      }) {
        thread { id }
      }
    }
  ' \
  -f pullRequestReviewId="$REVIEW_ID" \
  -f body="$BODY" \
  -f path="$FILE_PATH" \
  >/dev/null

gh api graphql \
  -f query='
    mutation($pullRequestReviewId: ID!) {
      submitPullRequestReview(input: {
        pullRequestReviewId: $pullRequestReviewId,
        event: COMMENT
      }) {
        pullRequestReview { id state }
      }
    }
  ' \
  -f pullRequestReviewId="$REVIEW_ID" \
  >/dev/null
submitted=1

echo "✅ Added merge guard review thread on PR #${PR_NUMBER} (anchored to ${FILE_PATH})"
