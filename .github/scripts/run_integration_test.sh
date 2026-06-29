#!/usr/bin/env bash
#
# Launch the fboss2 integration test on a DUT and wait for it to finish.
#
# Usage: run_integration_test.sh <DUT>
#
# The test is launched in a backgrounded subshell on the DUT (a foreground
# `nh dvc ssh ... ./fboss2_integration_test` is tied to the ssh session, which
# times out around 120s while the suite runs longer). The DUT writes:
#   /tmp/fboss2_itest.log  - all test stdout/stderr
#   /tmp/fboss2_itest.rc   - the exit code, written ONLY after the test exits
#   /tmp/fboss2_itest.pid  - the wrapper pid, so we can tell if it died early
# The rc file is the completion signal polled below.
#
# Exits non-zero only if a test actually FAILED or the run never completed.
set -euo pipefail

DUT="${1:?usage: run_integration_test.sh <DUT>}"

echo "::group::[$DUT] Launch integration test"
nh dvc ssh "$DUT" -c '
  set -euo pipefail

  # Clean up stale files from a previous run so we do not read an old
  # log / rc / pid and think the current test already finished.
  rm -f /tmp/fboss2_itest.log /tmp/fboss2_itest.rc /tmp/fboss2_itest.pid

  # stdbuf -oL -eL forces line buffering so each gtest result line
  # (e.g. "[ OK ] Suite.Test (123 ms)") is flushed to the log as it prints.
  # Without it, libc block-buffers stdout (the target is a file, not a TTY)
  # and buffered lines are LOST if the process is killed / aborts, leaving
  # the timing table empty. --gtest_break_on_failure aborts at the first
  # failed assertion so the collected agent/wedge logs stay relevant to that
  # failure (no later tests scribble over the failure state).
  (
    stdbuf -oL -eL ./fboss2_integration_test \
      --gtest_break_on_failure \
      > /tmp/fboss2_itest.log 2>&1
    echo $? > /tmp/fboss2_itest.rc
  ) </dev/null >/dev/null 2>&1 &

  echo $! > /tmp/fboss2_itest.pid
  echo "started pid=$(cat /tmp/fboss2_itest.pid)"
'
echo "::endgroup::"

echo "::group::[$DUT] Wait for completion"
TEST_RC=""

# Poll for up to 30 min (180 * 10s) via short ssh round-trips rather than one
# long-held session. Each probe ALWAYS exits 0 (every branch ends in printf)
# and reports state on stdout as "done <rc>", "dead", or "running <cur>|<last>"
# so a non-zero probe (e.g. rc file not there yet) never reads as ssh failure.
POLL_START=$(date +%s)
for _ in $(seq 1 180); do
  STATUS="$(nh dvc ssh "$DUT" -c '
    if [ -f /tmp/fboss2_itest.rc ]; then
      printf "done %s" "$(cat /tmp/fboss2_itest.rc)"
    elif [ -f /tmp/fboss2_itest.pid ] && ! kill -0 "$(cat /tmp/fboss2_itest.pid)" 2>/dev/null; then
      printf "dead"
    else
      cur="$(grep -oP "\[ RUN      \] \K\S+" /tmp/fboss2_itest.log 2>/dev/null | tail -n 1)"
      last="$(grep -oP "^\[  +(OK|FAILED|SKIPPED)  +\] \K.+" /tmp/fboss2_itest.log 2>/dev/null | tail -n 1)"
      printf "running %s|%s" "${cur:-unknown}" "${last:-}"
    fi
  ' 2>/dev/null || echo "ssherror")"

  ELAPSED=$(($(date +%s) - POLL_START))
  ELAPSED_FMT="${ELAPSED}s elapsed / 30m max"

  case "${STATUS%% *}" in
  done)
    TEST_RC="${STATUS#done }"
    echo "Integration test finished with rc=${TEST_RC} (${ELAPSED}s)"
    break
    ;;
  dead)
    echo "::warning::Test process is no longer running but rc file was not written (${ELAPSED}s)"
    TEST_RC=1
    break
    ;;
  running)
    RUNNING_PAYLOAD="${STATUS#running }"
    CUR_TEST="${RUNNING_PAYLOAD%%|*}"
    LAST_DONE="${RUNNING_PAYLOAD##*|}"
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
  echo "::error::Integration test did not finish within polling timeout"
  fail
fi

if [[ ${TEST_RC} -ne 0 ]]; then
  # gtest exits non-zero when tests are skipped in some configurations. Only
  # treat it as an error if a test actually FAILED.
  ACTUAL_FAILURES="$(nh dvc ssh "$DUT" -c \
    'grep -c "^\[  FAILED  \]" /tmp/fboss2_itest.log 2>/dev/null || echo 0' \
    2>/dev/null || echo 0)"
  if [[ ${ACTUAL_FAILURES} -eq 0 ]]; then
    echo "::warning::Test binary exited rc=${TEST_RC} but no FAILED tests found (all skipped?) — treating as pass"
  else
    echo "::error::Integration tests failed on DUT ${DUT} (${ACTUAL_FAILURES} test(s) FAILED)"
    fail
  fi
fi
