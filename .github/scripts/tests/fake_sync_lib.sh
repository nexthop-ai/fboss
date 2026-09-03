# shellcheck shell=bash
# Stub sync-lib.sh for the rebase_upstream_pr.py test suite: replaces the
# stable-tarball / conflict-resolver / harness-overlay machinery. Installed
# by the Sandbox fixture next to the script under test, which sources it.

echo_info() { echo "INFO: $*"; }
echo_error() { echo "ERROR: $*" >&2; }
echo_debug() { :; }
materialize_stable_tarball() { echo /dev/null; }
get_stable_commit() {
  echo "get_stable_commit should be unused (tests pass --onto)" >&2
  exit 1
}
run_conflict_resolver() { :; }
overlay_nh_harness() { git commit -q --allow-empty -m "$3"; }
