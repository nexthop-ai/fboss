#!/usr/bin/env bash
#
# Launch the fboss2 integration tests on a DUT via run_test.py and wait for
# them to finish.
#
# Usage: run_integration_test.sh <DUT> [config]
#
# The suite is driven by /opt/fboss/bin/run_test.py fboss2_integration (the
# same entry point Meta uses), which runs each gtest case as a separate
# binary invocation, manages agent cold boots between tests, and aggregates
# results into tr.xml under the invoking user's home. Nothing here reads that
# file; pass/fail is taken from the runner log below.
#
# The runner is launched in a backgrounded subshell on the DUT (a foreground
# `nh dvc ssh` session times out around 120s while the suite runs longer).
# The DUT writes:
#   /tmp/fboss2_itest.log  - all runner stdout/stderr
#   /tmp/fboss2_itest.rc   - the exit code, written ONLY after the runner exits
#   /tmp/fboss2_itest.pid  - the wrapper pid, so we can tell if it died early
# The rc file is the completion signal polled below.
#
# NOTE: run_test.py always exits 0 for gtest suites (pass/fail lives in the
# result files, matching Meta's netcastle flow), so a zero rc only means the
# runner completed. Pass/fail is decided from the summary counts in the log.
#
# Exits non-zero only if a test actually FAILED / timed out, the runner
# crashed, or the run never completed.
set -euo pipefail

DUT="${1:?usage: run_integration_test.sh <DUT> [config]}"
# The device's own materialized config by default; the runner snapshots and
# restores it around the run. Pass e.g.
# /opt/fboss/share/link_test_configs/montblanc.materialized_JSON to run with
# a specific lab config instead.
CONFIG="${2:-/etc/coop/agent.conf}"

echo "::group::[$DUT] Launch integration test runner"
nh dvc ssh "$DUT" -c '
  set -euo pipefail

  # Clean up stale files from a previous run so we do not read an old
  # log / rc / pid and think the current run already finished. sudo because a
  # file left behind by a root-owned run cannot be removed from sticky /tmp by
  # an unprivileged user.
  sudo rm -f /tmp/fboss2_itest.log /tmp/fboss2_itest.rc /tmp/fboss2_itest.pid

  # The preinstalled agents log to /var/facebook/logs/fboss (StandardOutput=
  # append: in their systemd units), which run_test.py --log-bundle does not
  # sweep -- it only collects /opt/fboss/logs. Symlink the agent logs into
  # /opt/fboss/logs so the runner sweep (shutil.copy2, which follows symlinks)
  # pulls their contents into the bundle. Best-effort: a missing file or link
  # failure is not fatal.
  sudo mkdir -p /opt/fboss/logs
  for agent_log in /var/facebook/logs/fboss/*.log; do
    if [ -e "$agent_log" ]; then
      sudo ln -sf "$agent_log" /opt/fboss/logs/ || true
    fi
  done

  # The runner needs root: it writes its run directory under /opt/fboss/logs
  # (root-owned) and restarts the agent services between test cases.
  # sudo comes before stdbuf so libstdbuf survives -- sudo strips LD_PRELOAD,
  # so `stdbuf sudo ...` would silently lose line buffering.
  # stdbuf -oL -eL forces line buffering so each runner progress line
  # (e.g. "########## Coldboot test results (5/107): ...") is flushed to the
  # log as it prints. Without it, libc block-buffers stdout (the target is a
  # file, not a TTY) and buffered lines are LOST if the process is killed.
  # LD_LIBRARY_PATH points at the directory the workflow copied the PR-built
  # libraries into, so the PR-built test binary can resolve them (run_test.py
  # prepends /opt/fboss/lib{,64} but preserves the inherited value). It is an
  # absolute path rather than $HOME because the copy and the run do not
  # necessarily authenticate as the same user.
  (
    sudo stdbuf -oL -eL env LD_LIBRARY_PATH="/opt/fboss/pr_lib:${LD_LIBRARY_PATH:-}" \
      python3 /opt/fboss/bin/run_test.py fboss2_integration \
      --log-bundle \
      --config '"$CONFIG"' \
      > /tmp/fboss2_itest.log 2>&1
    echo $? > /tmp/fboss2_itest.rc
  ) </dev/null >/dev/null 2>&1 &

  echo $! > /tmp/fboss2_itest.pid
  echo "started pid=$(cat /tmp/fboss2_itest.pid)"
'
echo "::endgroup::"

echo "::group::[$DUT] Wait for completion"
TEST_RC=""

# Poll for up to 45 min (270 * 10s) via short ssh round-trips rather than one
# long-held session. Each probe ALWAYS exits 0 (every branch ends in printf)
# and reports state on stdout as "done <rc>", "dead", or "running <cur>|<last>"
# so a non-zero probe (e.g. rc file not there yet) never reads as ssh failure.
POLL_START=$(date +%s)
for _ in $(seq 1 270); do
  STATUS="$(nh dvc ssh "$DUT" -c '
    if [ -f /tmp/fboss2_itest.rc ]; then
      printf "done %s" "$(cat /tmp/fboss2_itest.rc)"
    elif [ -f /tmp/fboss2_itest.pid ] && ! kill -0 "$(cat /tmp/fboss2_itest.pid)" 2>/dev/null; then
      printf "dead"
    else
      cur="$(grep -oP "^########## Running test: \K\S+" /tmp/fboss2_itest.log 2>/dev/null | tail -n 1)"
      last="$(grep -oP "^########## Coldboot test results \(\d+/\d+\): \K.+" /tmp/fboss2_itest.log 2>/dev/null | tail -n 1)"
      printf "running %s|%s" "${cur:-starting}" "${last:-}"
    fi
  ' 2>/dev/null || echo "ssherror")"

  ELAPSED=$(($(date +%s) - POLL_START))
  ELAPSED_FMT="${ELAPSED}s elapsed / 45m max"

  # First word is the state (done|dead|running|ssherror); read's last
  # variable absorbs the rest of the line, so payloads with spaces
  # (e.g. "[ OK ] Suite.Test (123 ms)") survive intact instead of needing a
  # second round of prefix-stripping.
  read -r STATUS_KIND STATUS_PAYLOAD <<<"$STATUS"

  case "${STATUS_KIND}" in
  done)
    TEST_RC="${STATUS_PAYLOAD}"
    echo "Integration test runner finished with rc=${TEST_RC} (${ELAPSED}s)"
    break
    ;;
  dead)
    echo "::warning::Runner process is no longer running but rc file was not written (${ELAPSED}s)"
    TEST_RC=1
    break
    ;;
  running)
    CUR_TEST="${STATUS_PAYLOAD%%|*}"
    LAST_DONE="${STATUS_PAYLOAD#*|}"
    if [[ -n $LAST_DONE ]]; then
      echo "[${ELAPSED_FMT}] running: ${CUR_TEST} | last done: ${LAST_DONE}"
    else
      echo "[${ELAPSED_FMT}] running: ${CUR_TEST}"
    fi
    ;;
  *)
    echo "[${ELAPSED_FMT}] transient SSH error while polling DUT, will retry"
    ;;
  esac
  sleep 10
done
echo "::endgroup::"

# Agent diagnostics are dumped by the always()-run collect_agent_logs.sh step,
# so a failure here only needs to flag + exit.
fail() {
  echo "::error::[$DUT] see 'Collect wedge agent logs' step for diagnostics"
  exit 1
}

if [[ -z ${TEST_RC} ]]; then
  echo "::error::Integration test run did not finish within polling timeout"
  fail
fi

if [[ ${TEST_RC} -ne 0 ]]; then
  echo "::error::run_test.py exited rc=${TEST_RC} (runner crash — it exits 0 even when tests fail)"
  fail
fi

# The runner completed; pass/fail comes from its final summary block:
#   Summary:
#      PASSED : 90
#      FAILED : 0
#      TIMEOUT : 0
#      SKIPPED : 17
# A missing summary means the runner never reached reporting (e.g. test
# binary not found), which must not read as a pass.
SUMMARY="$(nh dvc ssh "$DUT" -c '
  grep -oP "^\s+(FAILED|TIMEOUT) : \K[0-9]+" /tmp/fboss2_itest.log 2>/dev/null | paste -sd+ - | bc
' 2>/dev/null || echo "")"

if [[ -z ${SUMMARY} ]]; then
  echo "::error::Runner exited rc=0 but no result summary found in log — treating as failure"
  fail
fi

if [[ ${SUMMARY} -ne 0 ]]; then
  echo "::error::Integration tests failed on DUT ${DUT} (${SUMMARY} test(s) FAILED or timed out)"
  fail
fi

echo "All tests passed (or skipped) on ${DUT}"
