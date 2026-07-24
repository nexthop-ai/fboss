#!/usr/bin/env bash
#
# Fetch the run_test.py --log-bundle zip from the DUT into ./log_bundle/ so
# the workflow can upload it as a build artifact. The bundle contains the
# full runner output, the agent/service logs (wedge_agent.log, qsfp, ...),
# result CSVs, dmesg, and /var/log/messages for the whole run.
#
# Best-effort: a missing bundle (e.g. the runner crashed before bundling)
# logs a warning and exits 0 -- artifact upload uses if-no-files-found: ignore.
#
# Usage: collect_log_bundle.sh <DUT>
set -uo pipefail

DUT="${1:?usage: collect_log_bundle.sh <DUT>}"

# nh dvc ssh echoes the remote output with an extra trailing newline (the
# remote output is already newline-terminated and the CLI appends its own),
# so the last line of the local stream is blank. Drop empty lines before
# taking the last one, or BUNDLE_PATH captures the blank and the existing
# bundle is reported as missing.
BUNDLE_PATH="$(nh dvc ssh "$DUT" -c \
  'ls -t /opt/fboss/logs/run_test/*.zip 2>/dev/null | head -n 1' \
  2>/dev/null | grep . | tail -n 1)"

if [[ -z ${BUNDLE_PATH} || ${BUNDLE_PATH} != /opt/fboss/logs/run_test/*.zip ]]; then
  echo "::warning::[$DUT] no log bundle found on DUT, skipping"
  exit 0
fi

mkdir -p log_bundle
if nh dvc scp "$DUT":"${BUNDLE_PATH}" log_bundle/; then
  echo "Fetched $(basename "${BUNDLE_PATH}") ($(du -h log_bundle/* | cut -f1))"
else
  echo "::warning::[$DUT] failed to fetch log bundle ${BUNDLE_PATH}"
fi
