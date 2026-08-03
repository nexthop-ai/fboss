#!/bin/bash
# Set up sccache for distributed compilation with Bazel.
#
# Creates compiler wrapper scripts that route compilation through sccache,
# and writes a .bazel.d/sccache.bazelrc file with the necessary Bazel flags.
# The main .bazelrc imports this file via try-import.
#
# Configuration: set SCCACHE_SCHEDULER_HOST and SCCACHE_AUTH_TOKEN in
# fboss/oss/scripts/fboss-build.env (see fboss-build.env.example).
#
# Usage:
#   fboss/oss/scripts/bazel-sccache-setup.sh
#   bazel build //fboss/...  # sccache is picked up via .bazelrc try-import

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
BAZEL_D="$REPO_ROOT/.bazel.d"
mkdir -p "$BAZEL_D"
SCCACHE_RC="$BAZEL_D/sccache.bazelrc"
# Clean up legacy .bazelrc.sccache if it exists
rm -f "$REPO_ROOT/.bazelrc.sccache"

# Source site-specific configuration if present.  Guard with `|| true`: the env
# file ends with a best-effort SAI-tarball download helper that can legitimately
# fail (e.g. transient S3 / cache issues), and under `set -e` that failure would
# otherwise abort sccache setup entirely -- leaving the build on a stale
# sccache.bazelrc and skipping the server start/poll below.  Variable
# assignments that run before any failure still take effect.
ENV_FILE="$SCRIPT_DIR/fboss-build.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE" || true
fi

# Make sure if OOM that the build gets the short end of the stick.
echo 1000 >/proc/self/oom_score_adj

# Detect if distributed sccache is available.
# SCCACHE_SCHEDULER_HOST can be set in fboss-build.env or the environment.
SCCACHE_SCHEDULER_HOST="${SCCACHE_SCHEDULER_HOST:-}"
if [ -z "$SCCACHE_SCHEDULER_HOST" ]; then
  rm -f "$SCCACHE_RC"
  exit 0
fi
if ! timeout 1 bash -c ">/dev/tcp/$SCCACHE_SCHEDULER_HOST/10600" 2>/dev/null; then
  echo "No sccache scheduler found at $SCCACHE_SCHEDULER_HOST, skipping sccache"
  rm -f "$SCCACHE_RC"
  exit 0
fi

# Generate sccache-dist.toml from environment variables.
SCCACHE_CONF="$BAZEL_D/sccache-dist.toml"
cat >"$SCCACHE_CONF" <<TOML
[dist]
scheduler_url = "http://${SCCACHE_SCHEDULER_HOST}:10600"
${SCCACHE_EXTRA_DIST_CONFIG:-}
[dist.auth]
type = "token"
token = "${SCCACHE_AUTH_TOKEN:-}"
TOML
export SCCACHE_CONF
export SCCACHE_ERROR_LOG="/tmp/sccache.log"
export SCCACHE_LOG=info
# Keep the local sccache server alive. In remote_only mode the local server
# only dispatches jobs to the remote farm, so during long remote compiles and
# Bazel's analysis / dep-fetch / thrift-gen phases it sees no new activity and,
# with sccache's 600s default, shuts itself down. The next wave of --jobs
# clients then stampedes to restart it, racing on the server port (thousands of
# "Address in use" errors) and failing compile actions. 0 = never auto-shutdown.
# (The cmake build bumps this to 2700 for the same reason; see nhfboss-common.sh.)
export SCCACHE_IDLE_TIMEOUT=0

# Strip the varying absolute prefixes (Bazel execroot, getdeps install root) from
# the sccache key. Read by the server at start-up, so export before start; only
# existing absolute paths (relative/missing => server refuses to start).
SCCACHE_BASEDIRS=""
EXECROOT="$(bazel info execution_root 2>/dev/null || true)"
GETDEPS_INSTALL_DIR="${GETDEPS_INSTALL_DIR:-/var/FBOSS/tmp_bld_dir/installed}"
for d in "$EXECROOT" "$GETDEPS_INSTALL_DIR"; do
  case "$d" in
  /*) [ -d "$d" ] && SCCACHE_BASEDIRS="${SCCACHE_BASEDIRS:+$SCCACHE_BASEDIRS:}$d" ;;
  esac
done
export SCCACHE_BASEDIRS

# If sccache is already running in distributed mode with the right config, skip
# restart.  --dist-status reports {"SchedulerStatus":[...]} when the server is
# up and connected to the scheduler (and {"...":"Disabled"} otherwise), so grep
# for SchedulerStatus.  Getting this wrong means we tear down and restart a
# perfectly good warm server on every build, reopening the cold-start race.
# Restart on basedirs change: the server reads them only at start-up.
BASEDIRS_SENTINEL="$BAZEL_D/sccache-basedirs"
STORED_BASEDIRS="$(cat "$BASEDIRS_SENTINEL" 2>/dev/null || true)"
if [ -f "$SCCACHE_RC" ] && [ "$STORED_BASEDIRS" = "$SCCACHE_BASEDIRS" ] && SCCACHE_CONF="$SCCACHE_CONF" sccache --dist-status 2>/dev/null | grep -q SchedulerStatus; then
  echo "sccache distributed compilation already active"
  exit 0
fi

echo "Using distributed sccache: $SCCACHE_SCHEDULER_HOST"

# Point sccache's result cache at an S3-compatible bucket, configured via
# SCCACHE_ENDPOINT et al in fboss-build.env (see fboss-build.env.example).
# Without this the server falls back to local-disk storage, which on
# ephemeral CI runners starts empty every run -- 0% hit rate while the cmake
# path (nhfboss-common.sh, sourced from the same fboss-build.env values) gets
# ~100% from S3. The server reads storage config at start-up, so export
# before --start-server below.
if [ -n "${SCCACHE_ENDPOINT:-}" ] && timeout 1 bash -c ">/dev/tcp/${SCCACHE_ENDPOINT%%:*}/${SCCACHE_ENDPOINT##*:}" 2>/dev/null; then
  export SCCACHE_BUCKET SCCACHE_ENDPOINT SCCACHE_S3_KEY_PREFIX SCCACHE_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  echo "Using sccache bucket: $SCCACHE_ENDPOINT/$SCCACHE_BUCKET/$SCCACHE_S3_KEY_PREFIX"
fi

# Stop any existing sccache server before reconfiguring.
sccache --stop-server >/dev/null 2>&1 || true

# Explicitly start the local sccache server and wait until it is actually
# reachable and connected to the distributed scheduler before handing off to
# Bazel.  --start-server returns before the server has finished bootstrapping
# its dist client (it requests an mTLS cert from each remote server first), so
# without this poll Bazel can fire its first wave of --jobs compiler wrappers
# against a not-yet-ready server.  They then stampede to start their own
# servers, collide on the server port ("Address in use"), and -- since
# remote_only has no local fallback -- fail those compile actions outright.
sccache --start-server >/dev/null 2>&1 || true

# Poll --dist-status until it reports SchedulerStatus (server up and distributed
# compilation enabled).  Bail after ~30s rather than handing Bazel a server that
# is down or stuck in local-only ("Disabled") mode.
deadline=$((SECONDS + 30))
until SCCACHE_CONF="$SCCACHE_CONF" sccache --dist-status 2>/dev/null | grep -q SchedulerStatus; do
  if [ "$SECONDS" -ge "$deadline" ]; then
    echo "ERROR: sccache server not reachable / distributed sccache not working" >&2
    sccache --stop-server >/dev/null 2>&1 || true
    rm -f "$SCCACHE_RC"
    exit 1
  fi
  sleep 0.2
done

# Calculate parallelism. With distributed sccache, compilation runs on
# remote servers so local RAM is mainly used for preprocessing and linking.
# Match the cmake build's approach: nproc * 20 compile jobs.
NPROC=$(nproc)
JOBS=$((NPROC * 20))
[ "$JOBS" -lt 4 ] && JOBS=4

# Read machine RAM in MB for Bazel's resource pool.
# .bazelrc declares each CppLink action needs 6000 MB via
# --modify_execution_info; Bazel uses SERVER_RAM_MB to decide how many
# links to run concurrently (floor(RAM / 6000)).
SERVER_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')

# Write .bazelrc.sccache that overrides the compiler settings.
# The main .bazelrc uses try-import to pick this up.
cat >"$SCCACHE_RC" <<EOF
# Auto-generated by bazel-sccache-setup.sh -- do not edit
# Overrides compiler to use sccache for distributed compilation.
build --repo_env=CC=$SCRIPT_DIR/sccache-clang
build --repo_env=CXX=$SCRIPT_DIR/sccache-clang++
build --action_env=SCCACHE_CONF=$SCCACHE_CONF
build --action_env=SCCACHE_ERROR_LOG=/tmp/sccache.log
build --action_env=SCCACHE_LOG=info
# Never let the local sccache server auto-shut-down (see export above): a client
# that has to restart it should bring up a long-lived server, not a 600s one.
build --action_env=SCCACHE_IDLE_TIMEOUT=0
build --jobs=$JOBS
# Tell Bazel we have many more CPUs than physically present, since sccache
# dispatches compilation to remote servers. Without this, Bazel caps
# concurrent actions at HOST_CPUS regardless of --jobs.
build --local_resources=cpu=$JOBS
# Override the default memory pool with actual machine RAM. Combined with
# --modify_execution_info=CppLink=+resources:memory:6000 in .bazelrc,
# this lets Bazel schedule floor($SERVER_RAM_MB / 6000) concurrent link
# jobs natively -- no flock wrapper needed.
build --local_resources=memory=$SERVER_RAM_MB
EOF

# Emit -ffile-prefix-map for stable basedirs so cached objects are byte-identical
# across build roots. Skip --action_env and the per-user Bazel execroot: both put a
# per-user path in the Bazel action key and break CI/dev cache sharing. The server
# already read SCCACHE_BASEDIRS at start-up.
if [ -n "$SCCACHE_BASEDIRS" ]; then
  IFS=':' read -ra basedirs <<<"$SCCACHE_BASEDIRS"
  for d in "${basedirs[@]}"; do
    [ "$d" = "$EXECROOT" ] && continue
    echo "build --copt=-ffile-prefix-map=$d=." >>"$SCCACHE_RC"
    echo "build --host_copt=-ffile-prefix-map=$d=." >>"$SCCACHE_RC"
  done
fi

# Record basedirs for the change check above.
printf '%s' "$SCCACHE_BASEDIRS" >"$BASEDIRS_SENTINEL"

# Start the Bazel server (if not already running) so we can set its
# oom_score_adj. All processes Bazel forks (genrules, local actions) inherit
# the value from the server, so this ensures they get killed first on OOM.
BAZEL_SERVER_PID=$(bazel info server_pid 2>/dev/null)
if [ -n "$BAZEL_SERVER_PID" ]; then
  echo 1000 >/proc/$BAZEL_SERVER_PID/oom_score_adj
fi

echo "sccache distributed compilation enabled with --jobs=$JOBS"
