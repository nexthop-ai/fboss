#!/usr/bin/env bash
# Download fboss_cli_bins.tar.zst artifact from the PR Validation workflow
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

# Find the PR Validation run ID matching this HEAD_SHA. Use `--commit` so the
# filter is applied server-side; otherwise `gh run list`'s default 20-result
# page means older runs silently drop off and the lookup fails.
TMP_RUNS="$(mktemp)"
if ! gh run list --workflow="PR Validation" --commit "${HEAD_SHA}" \
  --json databaseId -q '.[].databaseId' \
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

echo "Downloading fboss_cli_bins artifact from PR Validation run: ${RUN_ID} (commit: ${HEAD_SHA})"
if ! gh run download "${RUN_ID}" -n fboss_cli_bins --dir ./; then
  echo "::error::Failed to download fboss_cli_bins artifact for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi
if [[ ! -f "./fboss_cli_bins.tar.zst" ]]; then
  echo "::error::fboss_cli_bins.tar.zst not found after download for run ${RUN_ID} (commit: ${HEAD_SHA})" >&2
  exit 1
fi

echo "Successfully downloaded fboss_cli_bins.tar.zst for commit ${HEAD_SHA}."
