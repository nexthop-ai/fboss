#!/bin/bash
# Create cFBOSS veth pairs based on /etc/fboss/cfboss/port_map.json.
# For each entry, creates `<veth>` <-> `<veth>_peer` pair and brings both up.
# Runs once via systemd oneshot before fboss_init.service.
set -euo pipefail

PORT_MAP=/etc/fboss/cfboss/port_map.json
if [ ! -f "$PORT_MAP" ]; then
  echo "fboss-create-veths: $PORT_MAP not present, nothing to do" >&2
  exit 0
fi

# The parse must fail loudly: a parse failure (or missing jq) exiting 0 here
# would let the agent boot with zero veths — silent dataplane loss reported
# as success.
if ! veths_raw=$(jq -r '.ports[].veth' "$PORT_MAP"); then
  echo "fboss-create-veths: FATAL: failed to parse $PORT_MAP" >&2
  exit 1
fi
if [ -z "$veths_raw" ]; then
  echo "fboss-create-veths: FATAL: no veths found in $PORT_MAP" >&2
  exit 1
fi
mapfile -t veths <<<"$veths_raw"

for v in "${veths[@]}"; do
  peer="${v}_peer"
  if ip link show "$v" >/dev/null 2>&1; then
    echo "fboss-create-veths: $v already exists, skipping"
    continue
  fi
  # A lingering peer without its veth (crash/manual partial cleanup) would
  # make the `ip link add` below fail and abort the unit; delete it first so
  # the bootstrap self-heals from partial state.
  ip link del "$peer" 2>/dev/null || true
  echo "fboss-create-veths: creating $v <-> $peer"
  ip link add "$v" type veth peer name "$peer"
  ip link set "$v" up
  ip link set "$peer" up
done

echo "fboss-create-veths: done"
