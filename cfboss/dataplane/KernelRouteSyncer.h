// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#pragma once

#include "fboss/agent/StateObserver.h"

#include <folly/IPAddress.h>

#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

struct nl_sock;

namespace facebook::fboss {
class StateDelta;
class SwitchState;
template <typename AddrT>
class Route;
} // namespace facebook::fboss

namespace facebook::fboss::cfboss {

class PortMap;

/**
 * Watches the FBOSS ForwardingInformationBase and syncs each resolved unicast
 * route into the Linux kernel main route table using libnl3 rtnl_route_add /
 * rtnl_route_delete.
 *
 * Routes installed by this syncer are tagged with RTPROT_FBOSS=196 so they
 * are distinguishable from other proto-tagged routes (kernel, dhcp, bgp, etc.)
 * and an operator can audit them via `ip route show proto fboss`.
 *
 * Next-hop interface resolution: each unicast next-hop's InterfaceID maps to
 * a PortID -> fboss_p<N> veth via PortMap (same mapping as VethIpInstaller).
 *
 * Routes whose next-hops are unresolved are withdrawn (deleted) from the
 * kernel so it never black-holes traffic; for multipath routes the resolvable
 * subset of next-hops is installed.
 */
class KernelRouteSyncer : public StateObserver {
 public:
  // The custom rtnetlink protocol tag for FBOSS-installed routes.
  // Chosen in the range reserved for site-local use (>= 192).
  static constexpr int kRtprotFboss = 196;

  explicit KernelRouteSyncer(std::shared_ptr<const PortMap> portMap);
  ~KernelRouteSyncer() override;

  void stateUpdated(const StateDelta& delta) override;

 private:
  // One resolved next-hop to install on a route. Multiple ResolvedNh
  // entries on a single addOrReplaceRoute call program the kernel for
  // ECMP — the kernel picks among them per-flow via fib_multipath_hash_policy.
  struct ResolvedNh {
    int oifIndex{0}; // kernel ifindex of the egress veth
    folly::IPAddress gateway;
    int weight{0}; // FBOSS NextHop weight (0 means unspecified, treated as 1)
  };

  // Install (or replace) one prefix with N >= 1 next-hops. With >1 hops the
  // route is a real ECMP route via libnl's rtnl_route_add_nexthop loop.
  // isConnected=true installs the prefix as a scope-link on-link route with no
  // gateway, mirroring how the ASIC programs a connected route to the
  // router-interface object rather than to a gateway IP.
  void addOrReplaceRoute(
      const folly::IPAddress& prefix,
      uint8_t prefixLen,
      const std::vector<ResolvedNh>& nexthops,
      bool isConnected = false);

  void delRoute(const folly::IPAddress& prefix, uint8_t prefixLen);

  // Reconcile a single FIB route (v4 or v6) against the kernel. Walks every
  // resolved next-hop and installs them all so the kernel ECMP-hashes flows
  // across the available paths. Skips a next-hop with no intfID or no veth
  // ifindex; removes the prefix if nothing resolves.
  template <typename RouteT>
  void reconcileRoute(
      const std::shared_ptr<RouteT>& route,
      const std::shared_ptr<SwitchState>& newState,
      bool isDelete);

  // Re-install every resolved FIB route in newState whose next-hop egresses the
  // given (now oper-up) kernel ifindex. On a port link flap the kernel purges
  // that interface's routes on link-DOWN, but FBOSS's FIB does not change, so
  // no FIB delta fires on link-UP — this re-drives the install path for the
  // affected routes only. Idempotent via reconcileRoute's NLM_F_REPLACE.
  void resyncRoutesForIfIndex(
      int upIfIndex,
      const std::shared_ptr<SwitchState>& newState);

  std::shared_ptr<const PortMap> portMap_;
  ::nl_sock* sock_{nullptr};

  // Serializes stateUpdated (and everything it reaches: the reconcile path,
  // sock_, vethIfIndexCache_) so the observer has the same thread model as
  // VethIpInstaller regardless of which thread delivers a delta.
  std::mutex mutex_;

  // veth name -> kernel ifindex, resolved once via if_nametoindex and cached,
  // never invalidated. Safe because cfboss veths are created once at boot and
  // never deleted/recreated — only admin up/down flaps occur, which preserve
  // ifindex — so a cached entry cannot go stale. It also avoids resolving per
  // next-hop per route on every FIB delta / port-up resync.
  std::map<std::string, int> vethIfIndexCache_;

  // Resolve a veth name to its kernel ifindex via vethIfIndexCache_. Returns
  // -1 on miss (unknown veth or if_nametoindex failure); a miss is not cached
  // so a later call retries. Same fall-back behavior as calling if_nametoindex
  // directly.
  int ifIndexForVeth(const std::string& veth);
  int ifIndexFromIntfId(const std::shared_ptr<SwitchState>& state, int intfId);
  int ifIndexFromPortId(int portId);
};

} // namespace facebook::fboss::cfboss
