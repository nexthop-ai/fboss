#!/usr/bin/env bash
#
# Dump agent diagnostics from the DUT: a single source for pass, fail, and
# timeout. wedge_agent.log tail + service state + journalctl in one ssh.
#
# Usage: collect_agent_logs.sh <DUT>
set -uo pipefail

DUT="${1:?usage: collect_agent_logs.sh <DUT>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Per-failed-test agent log slices: run_test.py keeps running (and cold
# booting) after a failure, so the fixed-size tail below can miss the failing
# test's window. The slicer targets it via the NH_TEST_START/END timestamps.
echo "::group::[${DUT}] wedge_agent.log slices for failed tests"
if nh dvc scp "${SCRIPT_DIR}/slice_agent_logs.py" "$DUT":/tmp/ 2>/dev/null; then
  nh dvc ssh "$DUT" -c 'sudo python3 /tmp/slice_agent_logs.py' 2>/dev/null || true
else
  echo "could not copy slicer to DUT, skipping"
fi
echo "::endgroup::"

echo "::group::[${DUT}] agent diagnostics"
nh dvc ssh "$DUT" -c '
  echo "=== systemctl status fboss_sw_agent ==="
  sudo systemctl --no-pager -l status fboss_sw_agent || true

  echo "=== systemctl status fboss_hw_agent@0 ==="
  sudo systemctl --no-pager -l status fboss_hw_agent@0 || true

  echo "=== tail -n 5000 /var/facebook/logs/fboss/wedge_agent.log ==="
  sudo tail -n 5000 /var/facebook/logs/fboss/wedge_agent.log || true

  echo "=== crash markers from wedge_agent.log ==="
  sudo grep -E "CHECK failed|Failed to|Terminated due to|SaiApiError" \
    /var/facebook/logs/fboss/wedge_agent.log | tail -n 100 || true

  echo "=== journalctl fboss_hw_agent@0 ==="
  sudo journalctl -u fboss_hw_agent@0 --no-pager -n 200 || true

  echo "=== journalctl fboss_sw_agent ==="
  sudo journalctl -u fboss_sw_agent --no-pager -n 200 || true
' 2>/dev/null || true
echo "::endgroup::"
