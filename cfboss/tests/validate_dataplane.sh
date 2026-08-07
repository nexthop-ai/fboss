#!/usr/bin/env bash
# cFBOSS fake-SAI + kernel-dataplane validation suite. Drives a running cFBOSS
# container via docker exec through the checks below. Non-zero exit if any
# check fails.
#   1. cross-netns ping (peer -> cFBOSS interface, v4+v6)
#   2. transit ping (peer -> cFBOSS kernel-forwarded -> peer, TTL decremented)
#   3. discovery-protocol (LLDP) frame injection surfaces in the agent
#   4. kernel veth admin-down propagates to the agent's port view
#   5. agent-CLI admin-down drops the kernel veth and stays view-consistent
#   6. resolved FIB mirrored into the kernel route table + interface IPs on veths
#   7. veth flap re-programming: routes/IP purged on link-down, re-driven on up
#
# Usage: validate_dataplane.sh [container-name]   (default: cfboss-${USER})
set -u
CTR="${1:-cfboss-${USER}}"
FB=/opt/fboss/bin/fboss2
dex() { docker exec "$CTR" bash -c "$*"; }
pass=0
fail=0
ok() {
  echo "  PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "  FAIL: $1"
  fail=$((fail + 1))
}
portrow() { dex "$FB show port" 2>/dev/null | grep -E "[[:space:]]$1[[:space:]]"; }
# retry <attempts> <sleep_s> <cmd...>: run cmd (a shell function returning 0 on
# success) until it succeeds or attempts are exhausted. Every check below polls
# through this, since each depends on async observer reconciliation completing.
retry() {
  local n=$1 s=$2
  shift 2
  local _
  for _ in $(seq 1 "$n"); do
    if "$@"; then
      return 0
    fi
    sleep "$s"
  done
  return 1
}

echo "== cFBOSS dataplane validation on '$CTR' =="
for _ in $(seq 1 60); do
  dex "$FB show port" 2>/dev/null | grep -q eth1/1/1 && break
  sleep 5
done
dex "$FB show port" 2>/dev/null | grep -q eth1/1/1 || {
  echo "FATAL: agent not ready"
  exit 1
}

# topology: peer netns on ports 1 and 2 (idempotent)
dex '
sysctl -w net.ipv4.ip_forward=1 >/dev/null; sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null
setup() { ns=$1; i=$2
  ip netns add "$ns" 2>/dev/null || true
  ip link show "fboss_p${i}_peer" >/dev/null 2>&1 && ip link set "fboss_p${i}_peer" netns "$ns"
  ip netns exec "$ns" ip link set lo up
  ip netns exec "$ns" ip link set "fboss_p${i}_peer" up
  ip netns exec "$ns" ip addr add "10.0.${i}.2/30" dev "fboss_p${i}_peer" 2>/dev/null || true
  ip netns exec "$ns" ip -6 addr add "fd00:0:${i}::2/64" dev "fboss_p${i}_peer" 2>/dev/null || true
}
setup cns1 1; setup cns2 2
ip netns exec cns1 ip route add 10.0.2.0/30 via 10.0.1.1 2>/dev/null || true
ip netns exec cns2 ip route add 10.0.1.0/30 via 10.0.2.1 2>/dev/null || true
ip netns exec cns1 ip -6 route add fd00:0:2::/64 via fd00:0:1::1 2>/dev/null || true
ip netns exec cns2 ip -6 route add fd00:0:1::/64 via fd00:0:2::1 2>/dev/null || true
' || {
  echo "FATAL: topology setup failed"
  exit 1
}

# 1. cross-netns ping (retry: depends on async observer reconciliation)
check1() {
  dex "ip netns exec cns1 ping  -c3 -W2 10.0.1.1" | grep -q '0% packet loss' &&
    dex "ip netns exec cns1 ping6 -c3 -W2 fd00:0:1::1" | grep -q '0% packet loss'
}
if retry 12 5 check1; then
  ok "cross-netns ping peer->cFBOSS (v4+v6)"
else bad "cross-netns ping peer->cFBOSS"; fi

# 2. transit ping (kernel forwards; TTL 64->63). Retry: same async dependency.
# t2/ttl are set as globals by check2 so the result message can read them.
check2() {
  t2=$(dex "ip netns exec cns1 ping -c3 -W2 10.0.2.2")
  ttl=$(echo "$t2" | grep -oE 'ttl=[0-9]+' | head -1 | cut -d= -f2)
  echo "$t2" | grep -q '0% packet loss' && [ "${ttl:-0}" = 63 ]
}
if retry 12 5 check2; then
  ok "transit ping cns1->cns2 kernel-forwarded (ttl=$ttl)"
else bad "transit ping cns1->cns2 (ttl=${ttl:-none})"; fi

# 3. LLDP injection surfaces in agent. The frame is (re)injected on every
# retry attempt — injecting only once could race the agent's LLDP RX path
# coming up. The discriminating token is the injected neighbor Port-ID
# ("cfbtest"), which can only appear in the agent's view if the frame
# actually traversed the veth into the agent.
inject_lldp() {
  dex 'ip netns exec cns1 python3 - fboss_p1_peer <<PY
import socket,sys,struct
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x88cc)); s.bind((sys.argv[1],0))
src=b"\x02\x00\x00\x00\x00\x11"
tlv=lambda t,v: struct.pack("!H",(t<<9)|len(v))+v
f=b"\x01\x80\xc2\x00\x00\x0e"+src+b"\x88\xcc"+tlv(1,b"\x04"+src)+tlv(2,b"\x07cfbtest")+tlv(3,struct.pack("!H",120))+tlv(0,b"")
s.send(f.ljust(64,b"\x00"))
PY'
}
check3() {
  inject_lldp
  dex "$FB show lldp" 2>/dev/null | grep -q 'cfbtest'
}
if retry 12 5 check3; then
  ok "LLDP neighbor cfbtest surfaced in agent view"
else bad "LLDP frame did not surface (no cfbtest neighbor)"; fi

# 4. kernel veth down -> agent port view Down. Precondition: the port must
# be Up before the toggle, otherwise the Down assertion would pass vacuously.
pre4() { portrow eth1/5/1 | grep -qw Up; }
up4=0
retry 12 3 pre4 && up4=1
dex "ip link set fboss_p5 down"
check4() { portrow eth1/5/1 | grep -qw Down; }
if [ "$up4" = 1 ] && retry 12 3 check4; then
  ok "kernel veth down -> agent eth1/5/1 Down"
else bad "kernel veth down not propagated (pre_up=$up4)"; fi
dex "ip link set fboss_p5 up"

# 5. agent CLI disable -> kernel veth drops + view consistent. Precondition:
# the port must be Up before the disable (same vacuous-pass guard as check 4).
pre5() { portrow eth1/6/1 | grep -qw Up; }
up5=0
retry 12 3 pre5 && up5=1
dex "$FB set port eth1/6/1 state disable -y" >/dev/null 2>&1
# check5 latches each side (veth link-state, agent port view) into a global so the
# failure message can report which side lagged; it succeeds once both hold.
d5v=0
d5a=0
check5() {
  dex "ip link show fboss_p6" | head -1 | grep -q 'state DOWN' && d5v=1
  portrow eth1/6/1 | grep -qw Disabled && d5a=1
  [ "$d5v" = 1 ] && [ "$d5a" = 1 ]
}
if [ "$up5" = 1 ] && retry 12 3 check5; then
  ok "agent disable -> veth fboss_p6 down + view consistent"
else
  bad "agent disable inconsistent (pre_up=$up5 veth_down=$d5v agent_disabled=$d5a)"
fi
dex "$FB set port eth1/6/1 state enable -y" >/dev/null 2>&1

# 6. route programming: KernelRouteSyncer mirrors the resolved FIB into the
# kernel main table (protocol fboss == 196); VethIpInstaller installs the
# interface IPs onto the veths. Expect one connected scope-link route plus its
# IP per veth. Retry: same async observer reconciliation as the checks above.
check6() {
  rp4=$(dex "ip route show table main proto 196 | grep -c 'dev fboss_p'")
  rp6=$(dex "ip -6 route show table main proto 196 | grep -c 'dev fboss_p'")
  rpip=$(dex 'c=0; for p in $(seq 1 32); do ip -o -4 addr show fboss_p$p 2>/dev/null | grep -qE "inet 10[.]0[.]$p[.]1/30" && c=$((c + 1)); done; echo "$c"')
  [ "${rp4:-0}" = 32 ] && [ "${rp6:-0}" -ge 32 ] && [ "${rpip:-0}" = 32 ]
}
if retry 12 5 check6; then
  ok "route programming - $rp4 v4 + $rp6 v6 proto-fboss routes, $rpip veth IPs"
else bad "route programming (v4=${rp4:-?} v6=${rp6:-?} ips=${rpip:-?}; want 32/>=32/32)"; fi

# 7. veth flap -> route + IP re-programming. On link-down the kernel purges the
# veth's routes; KernelRouteSyncer must re-drive them on link-up (no FIB delta
# fires on link-up, so absent the re-drive they never return) and VethIpInstaller
# must re-install the IP. fboss_p7 is untouched by the checks above.
fp7route() { dex "ip route show table main proto 196 dev fboss_p7"; }
b7=$(fp7route)
dex "ip link set fboss_p7 down"
sleep 2
d7=$(fp7route)
dex "ip link set fboss_p7 up"
check7() {
  [ -n "$(fp7route)" ] && dex "ip -o -4 addr show fboss_p7" | grep -q 'inet 10.0.7.1/30'
}
if [ -n "$b7" ] && [ -z "$d7" ] && retry 12 3 check7; then
  ok "veth flap fboss_p7 -> route purged on down, re-driven on up + IP re-installed"
else bad "veth flap re-programming (before=[$b7] down=[$d7]; up route/IP not restored)"; fi

echo "== RESULT: $pass passed, $fail failed =="
[ "$fail" = 0 ]
