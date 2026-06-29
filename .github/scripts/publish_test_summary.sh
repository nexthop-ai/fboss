#!/usr/bin/env bash
#
# Fetch the integration test log from the DUT, dump it to the console, and
# publish a per-test timing table to the run summary.
#
# Usage: publish_test_summary.sh <DUT>
set -uo pipefail

DUT="${1:?usage: publish_test_summary.sh <DUT>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/fboss2_itest_${DUT}.log"

nh dvc ssh "$DUT" -c 'cat /tmp/fboss2_itest.log' >"$LOG_FILE" 2>/dev/null || true

SIZE=$(wc -c <"$LOG_FILE" 2>/dev/null || echo 0)
LINES=$(wc -l <"$LOG_FILE" 2>/dev/null || echo 0)
echo "Fetched integration test log: ${SIZE} bytes, ${LINES} lines"

# Always dump the full log to the console so it is visible on pass, fail, or
# timeout without having to ssh back into the DUT after the fact.
echo "::group::[${DUT}] Full integration test log"
if [ -s "$LOG_FILE" ]; then
  cat "$LOG_FILE"
else
  echo "(log file is empty or could not be fetched from DUT)"
fi
echo "::endgroup::"

if [ ! -s "$LOG_FILE" ]; then
  {
    echo "## Integration Test Results (${DUT})"
    echo ""
    echo "_No test log available to summarize._"
  } >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
  exit 0
fi

python3 "${SCRIPT_DIR}/parse_test_timing.py" "$LOG_FILE" "$DUT"
