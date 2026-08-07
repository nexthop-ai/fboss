#!/usr/bin/env bash
# Build + test fboss-sim on a workstation (fake-SAI only):
#   1. Build the FBOSS docker image if missing.
#   2. Start the FBOSS_build_${USER} container if missing.
#   3. Ensure a clean fake-SAI state (revert any real-SAI manifest edits,
#      drop sai_impl, clear stale fboss build/install dirs).
#   4. Fake-SAI build: get-deps, then fboss_fake_agent_targets +
#      fboss2_targets with SAI_IMPL=fake.
#   5. Package + start the fboss-sim runtime container, wait for the agent.
#   6. Run fboss2_integration_test.
#
# This never runs the real-SAI build — fake-SAI is all the simulator needs.
#
# Run from the repo root — internal paths (./fboss/..., fboss-sim/...) are
# resolved against the current working directory, not this script's location.
#
# Usage:
#   .claude/skills/fboss-sim/fboss-sim-build-and-test.sh \
#       [--skip-test] [--keep-runtime] [--no-cleanup-build]
#
# Flags:
#   --skip-test         Build everything but don't run fboss2_integration_test.
#   --keep-runtime      Don't stop/remove fboss_sim_runtime_${USER} at exit.
#   --no-cleanup-build  Don't stop/remove FBOSS_build_${USER} at exit.

set -euo pipefail

SKIP_TEST=0
KEEP_RUNTIME=0
NO_CLEANUP_BUILD=0
while [[ $# -gt 0 ]]; do
  case "$1" in
  --skip-test)
    SKIP_TEST=1
    shift
    ;;
  --keep-runtime)
    KEEP_RUNTIME=1
    shift
    ;;
  --no-cleanup-build)
    NO_CLEANUP_BUILD=1
    shift
    ;;
  -h | --help)
    sed -n '2,24p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown flag: $1" >&2
    exit 2
    ;;
  esac
done

IMAGE="fboss_image_${USER}"
BUILD_CTR="FBOSS_build_${USER}"
SIM_CTR="fboss_sim_runtime_${USER}"
SIM_NET="fboss_sim_net_${USER}"

log() { echo -e "\n=== $* ===" >&2; }

image_exists() { docker image inspect "$IMAGE:latest" >/dev/null 2>&1; }
container_exists() { docker ps -a --format '{{.Names}}' | grep -qx "$BUILD_CTR"; }
container_running() { docker ps --format '{{.Names}}' | grep -qx "$BUILD_CTR"; }

cleanup_runtime() {
  log "Cleanup fboss-sim runtime container and image"
  docker stop "$SIM_CTR" 2>/dev/null || true
  docker rm "$SIM_CTR" 2>/dev/null || true
  docker rmi "${SIM_CTR}:latest" 2>/dev/null || true
  docker network rm "$SIM_NET" 2>/dev/null || true
}
cleanup_build() {
  log "Cleanup FBOSS build container"
  docker stop "$BUILD_CTR" 2>/dev/null || true
  docker rm "$BUILD_CTR" 2>/dev/null || true
}
on_exit() {
  rc=$?
  [[ $KEEP_RUNTIME -eq 0 ]] && cleanup_runtime
  [[ $NO_CLEANUP_BUILD -eq 0 ]] && cleanup_build
  exit $rc
}
trap on_exit EXIT

# --- Stage 1: image -----------------------------------------------------------
if image_exists; then
  log "FBOSS docker image $IMAGE:latest already present — skipping build"
else
  log "Build FBOSS Docker image"
  ./fboss/oss/scripts/nhfboss-docker-build.py
  docker image prune -f
fi

# --- Stage 2: build container -------------------------------------------------
if container_running; then
  log "Build container $BUILD_CTR already running"
elif container_exists; then
  log "Starting existing build container $BUILD_CTR"
  docker start "$BUILD_CTR" >/dev/null
else
  log "Creating + starting build container $BUILD_CTR"
  ./fboss/oss/scripts/nhfboss-docker-enter.py
fi

# --- Stage 3: ensure clean fake-SAI state ------------------------------------
# Idempotent prep: if a real-SAI build was ever run in this workspace,
# build-helper.py left edited manifests, a sai_impl manifest, and SAI-specific
# build artifacts behind. Undo all of that so the fake-SAI build is clean. On a
# fresh checkout these are no-ops.
log "Ensure clean fake-SAI state"
sudo rm -rf .build_dir/build/fboss .build_dir/installed/fboss .build_dir/installed/sai_impl-*
git checkout build/fbcode_builder/manifests/libsai build/fbcode_builder/manifests/fboss
rm -f build/fbcode_builder/manifests/sai_impl

# --- Stage 4: fake-SAI build --------------------------------------------------
log "Fetch dependencies (fake SAI)"
docker exec "$BUILD_CTR" ./fboss/oss/scripts/nhfboss-get-deps.sh

log "Build FBOSS with Fake SAI (fboss_fake_agent_targets)"
docker exec -e SAI_IMPL=fake "$BUILD_CTR" \
  ./fboss/oss/scripts/nhfboss-build.sh --cmake-target fboss_fake_agent_targets

# fsdb is packaged and enabled unconditionally by the runtime image (bgpd
# publishes its config/RIB state to it), so the packager's binary check fails
# without it. Matches the CI step's target list.
log "Build FBOSS with Fake SAI (fboss2_targets + fsdb)"
docker exec -e SAI_IMPL=fake "$BUILD_CTR" \
  ./fboss/oss/scripts/nhfboss-build.sh --cmake-target fboss2_targets --cmake-target fsdb

# --- Stage 5: fboss-sim runtime ----------------------------------------------
# Two-phase, as CI does: ldd must resolve CentOS libs, so collect runs inside
# the build container; the docker build runs on the host, where the daemon is.
# Collecting on an Ubuntu host silently packages host libs and the agent then
# dies with undefined-symbol errors.
log "Collect fboss-sim artifacts (inside the build container)"
docker exec "$BUILD_CTR" python3 fboss-sim/scripts/fboss-sim-docker-package.py --collect-only

log "Build fboss-sim runtime image (host)"
python3 fboss-sim/scripts/fboss-sim-docker-package.py --build-only

log "Start fboss-sim runtime container"
python3 fboss-sim/scripts/fboss-sim-docker-run.py

log "Wait for agent services to be ready"
ready=0
for i in $(seq 1 5); do
  elapsed=$(((i - 1) * 2))
  if docker exec "$SIM_CTR" /opt/fboss/bin/fboss2 show interface 2>/dev/null; then
    echo "✓ Agent ready after ${elapsed}s"
    ready=1
    break
  fi
  echo "  [${elapsed}s] not ready yet, retrying..."
  sleep 2
done
if [[ $ready -ne 1 ]]; then
  echo "❌ Agent not ready after 10s" >&2
  docker exec "$SIM_CTR" tail -n 50 /var/facebook/logs/fboss/wedge_agent.log || true
  exit 1
fi

# --- Stage 6: integration test ------------------------------------------------
if [[ $SKIP_TEST -eq 1 ]]; then
  log "Skipping fboss2_integration_test (--skip-test)"
else
  log "Run fboss2 integration test"
  docker exec "$SIM_CTR" /opt/fboss/bin/fboss2_integration_test
fi
