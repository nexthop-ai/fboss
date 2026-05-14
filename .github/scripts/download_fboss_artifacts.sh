#!/usr/bin/env bash
# Download fboss2_integration_test artifact from the PR Validation workflow
# for the given commit SHA (HEAD_SHA).
#
# Usage: download_fboss_artifacts.sh <HEAD_SHA>
#
# Expects GH_TOKEN (or GITHUB_TOKEN via gh) to be set in the environment.

set -euo pipefail

HEAD_SHA="${1:-}"
if [[ -z ${HEAD_SHA} ]]; then
  echo "::error::HEAD_SHA argument is required" >&2
  exit 1
fi

# Find the PR Validation run ID matching this HEAD_SHA.
TMP_RUNS="$(mktemp)"
if ! gh run list --workflow="PR Validation" --json headSha,databaseId \
  -q ".[] | select(.headSha == \"${HEAD_SHA}\") | .databaseId" \
  >"${TMP_RUNS}" 2>/dev/null; then
  echo "::error::Failed to list PR Validation runs for commit ${HEAD_SHA}" >&2
  cat "${TMP_RUNS}" || true
  rm -f "${TMP_RUNS}"
  exit 1
fi

RUN_ID="$(head -1 "${TMP_RUNS}" | tr -d '[:space:]')"
rm -f "${TMP_RUNS}"

if [[ -z ${RUN_ID} ]]; then
  echo "::error::No PR Validation run found for commit ${HEAD_SHA}" >&2
  exit 1
fi

echo "Downloading fboss2_integration_test artifact from PR Validation run: ${RUN_ID} (commit: ${HEAD_SHA})"
if ! gh run download "${RUN_ID}" -n fboss2_integration_test --dir ./; then
  echo "::error::Failed to download fboss2_integration_test artifact for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi
echo "Downloading fboss2-dev artifact from PR Validation run: ${RUN_ID} (commit: ${HEAD_SHA})"
if ! gh run download "${RUN_ID}" -n fboss2-dev --dir ./; then
  echo "::error::Failed to download fboss2-dev artifact for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi
if [[ ! -f "./fboss2_integration_test" ]]; then
  echo "::error::fboss2_integration_test artifact not found after download for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi
if [[ ! -f "./fboss2-dev" ]]; then
  echo "::error::fboss2-dev artifact not found after download for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi

echo "Successfully downloaded fboss2_integration_test and fboss2-dev artifact for commit ${HEAD_SHA}."
