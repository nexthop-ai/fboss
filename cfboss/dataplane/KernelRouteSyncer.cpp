// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/KernelRouteSyncer.h"
#include "cfboss/dataplane/NetlinkUtils.h"
#include "cfboss/dataplane/PortMap.h"

#include "fboss/agent/state/DeltaFunctions.h"
#include "fboss/agent/state/FibInfoMap.h"
#include "fboss/agent/state/ForwardingInformationBase.h" // NOLINT(misc-include-cleaner)
#include "fboss/agent/state/Interface.h"
#include "fboss/agent/state/Port.h"
#include "fboss/agent/state/RouteNextHop.h" // NOLINT(misc-include-cleaner)
#include "fboss/agent/state/StateDelta.h"
#include "fboss/agent/state/SwitchState.h"
#include "fboss/agent/types.h"

#include <folly/logging/xlog.h>

#include <netlink/addr.h>
#include <netlink/route/nexthop.h>
#include <netlink/route/route.h>
#include <netlink/socket.h>

#include <mutex>
#include <utility>

namespace facebook::fboss::cfboss {

KernelRouteSyncer::KernelRouteSyncer(std::shared_ptr<const PortMap> portMap)
    : portMap_(std::move(portMap)) {
  if (!portMap_) {
    throw std::runtime_error("KernelRouteSyncer: null PortMap");
  }
  sock_ = openRouteNetlinkSocket("KernelRouteSyncer");
  if (!sock_) {
    throw std::runtime_error(
        "KernelRouteSyncer: failed to open netlink socket");
  }
  XLOG(INFO) << "KernelRouteSyncer: ready (netlink socket connected)";
}

KernelRouteSyncer::~KernelRouteSyncer() {
  if (sock_) {
    ::nl_socket_free(sock_);
  }
}

int KernelRouteSyncer::ifIndexForVeth(const std::string& veth) {
  auto it = vethIfIndexCache_.find(veth);
  if (it != vethIfIndexCache_.end()) {
    return it->second;
  }
  // Don't cache a miss: the veth may appear later, and the next call will
  // re-resolve it.
  int ifindex = cfboss::ifIndexForVeth(veth);
  if (ifindex >= 0) {
    vethIfIndexCache_[veth] = ifindex;
  }
  return ifindex;
}

int KernelRouteSyncer::ifIndexFromIntfId(
    const std::shared_ptr<SwitchState>& state,
    int intfId) {
  auto intf = state->getInterfaces()->getNodeIf(InterfaceID(intfId));
  if (!intf) {
    return -1;
  }
  auto vethName = resolveVeth(*portMap_, *intf);
  if (!vethName) {
    return -1;
  }
  return ifIndexForVeth(*vethName);
}

int KernelRouteSyncer::ifIndexFromPortId(int portId) {
  // cfboss convention: PortID == first SAI lane (same mapping as
  // ifIndexFromIntfId above and VethIpInstaller).
  auto vethName = portMap_->vethForLane(static_cast<uint32_t>(portId));
  if (!vethName) {
    return -1;
  }
  return ifIndexForVeth(*vethName);
}

void KernelRouteSyncer::addOrReplaceRoute(
    const folly::IPAddress& prefix,
    uint8_t prefixLen,
    const std::vector<ResolvedNh>& nexthops,
    bool isConnected) {
  if (nexthops.empty()) {
    XLOG(WARN) << "KernelRouteSyncer: addOrReplaceRoute called with empty "
               << "nexthop vector for " << prefix << "/"
               << static_cast<int>(prefixLen);
    return;
  }
  ::rtnl_route* route = ::rtnl_route_alloc();
  if (!route) {
    XLOG(ERR) << "KernelRouteSyncer: rtnl_route_alloc failed";
    return;
  }
  ::nl_addr* dst = makeNlAddr(prefix, prefixLen);
  if (!dst) {
    ::rtnl_route_put(route);
    return;
  }
  ::rtnl_route_set_family(route, prefix.isV4() ? AF_INET : AF_INET6);
  ::rtnl_route_set_dst(route, dst);
  ::rtnl_route_set_protocol(route, kRtprotFboss);
  ::rtnl_route_set_table(route, RT_TABLE_MAIN);
  // A connected/interface route is installed scope-link with no gateway
  // (mirrors the ASIC programming the RIF object), so gateway routes resolve
  // on-link against it naturally. Non-connected routes stay scope-universe.
  ::rtnl_route_set_scope(
      route, isConnected ? RT_SCOPE_LINK : RT_SCOPE_UNIVERSE);
  ::rtnl_route_set_type(route, RTN_UNICAST);

  // Append every resolved next-hop. With >1 the kernel performs ECMP (uses
  // the FIB hashing policy already configured via
  // sysctl/net.ipv{4,6}.fib_multipath_hash_policy).
  size_t added = 0;
  for (const auto& hop : nexthops) {
    ::rtnl_nexthop* nh = ::rtnl_route_nh_alloc();
    if (!nh) {
      XLOG(ERR) << "KernelRouteSyncer: rtnl_route_nh_alloc failed for "
                << prefix << "/" << static_cast<int>(prefixLen);
      continue;
    }
    ::rtnl_route_nh_set_ifindex(nh, hop.oifIndex);
    // Connected routes carry the RIF own IP as the next-hop addr; installing it
    // as a gateway would clobber the proto-kernel scope-link route with a
    // recursive "via <own-ip>" entry. Skip the gateway and keep it on-link.
    if (!isConnected && !hop.gateway.empty()) {
      ::nl_addr* gw = makeNlAddr(hop.gateway, hop.gateway.isV4() ? 32 : 128);
      if (gw) {
        ::rtnl_route_nh_set_gateway(nh, gw);
        ::nl_addr_put(gw);
      }
    }
    // libnl's rtnl_route_nh_set_weight uses the "weight-minus-one" encoding
    // that maps directly to the kernel's rtnh_hops field — pass weight-1.
    // weight of 0 (unspecified) maps to the kernel's default of 1.
    if (hop.weight > 1) {
      ::rtnl_route_nh_set_weight(nh, hop.weight - 1);
    }
    ::rtnl_route_add_nexthop(route, nh);
    ++added;
  }

  if (added == 0) {
    XLOG(WARN) << "KernelRouteSyncer: no nexthops materialized for " << prefix
               << "/" << static_cast<int>(prefixLen);
    ::nl_addr_put(dst);
    ::rtnl_route_put(route);
    return;
  }

  int rc = ::rtnl_route_add(sock_, route, NLM_F_REPLACE | NLM_F_CREATE);
  ::nl_addr_put(dst);
  ::rtnl_route_put(route);
  if (rc < 0 && rc != -NLE_EXIST) {
    XLOG(WARN) << "KernelRouteSyncer: rtnl_route_add(" << prefix << "/"
               << static_cast<int>(prefixLen) << " nexthops=" << added
               << ") failed: " << ::nl_geterror(rc);
    return;
  }
  if (added == 1) {
    XLOG(INFO) << "KernelRouteSyncer: installed " << prefix << "/"
               << static_cast<int>(prefixLen) << " via " << nexthops[0].gateway
               << " oif=" << nexthops[0].oifIndex << " proto=fboss";
  } else {
    XLOG(INFO) << "KernelRouteSyncer: installed " << prefix << "/"
               << static_cast<int>(prefixLen) << " ECMP nexthops=" << added
               << " proto=fboss";
  }
}

void KernelRouteSyncer::delRoute(
    const folly::IPAddress& prefix,
    uint8_t prefixLen) {
  // Always attempt the kernel delete when FBOSS reports the route gone. The
  // kernel delete is filtered by protocol=fboss + dst/prefixlen/table, so
  // deleting a route we did not install is a harmless no-op — no local
  // bookkeeping is needed to gate it.
  ::rtnl_route* route = ::rtnl_route_alloc();
  if (!route) {
    return;
  }
  ::nl_addr* dst = makeNlAddr(prefix, prefixLen);
  if (!dst) {
    ::rtnl_route_put(route);
    return;
  }
  ::rtnl_route_set_family(route, prefix.isV4() ? AF_INET : AF_INET6);
  ::rtnl_route_set_dst(route, dst);
  ::rtnl_route_set_protocol(route, kRtprotFboss);
  ::rtnl_route_set_table(route, RT_TABLE_MAIN);
  // Match scope-agnostically (RT_SCOPE_NOWHERE) and set no nexthops so a single
  // delete matches both the scope-universe gateway routes and the scope-link
  // connected routes, as well as ECMP/multipath routes.
  ::rtnl_route_set_scope(route, RT_SCOPE_NOWHERE);
  int rc = ::rtnl_route_delete(sock_, route, 0);
  ::nl_addr_put(dst);
  ::rtnl_route_put(route);
  if (rc == 0) {
    XLOG(INFO) << "KernelRouteSyncer: removed " << prefix << "/"
               << static_cast<int>(prefixLen);
  } else if (rc == -NLE_OBJ_NOTFOUND) {
    XLOG(DBG2) << "KernelRouteSyncer: route " << prefix << "/"
               << static_cast<int>(prefixLen) << " already absent from kernel";
  } else {
    XLOG(WARN) << "KernelRouteSyncer: rtnl_route_delete(" << prefix << "/"
               << static_cast<int>(prefixLen)
               << ") failed: " << ::nl_geterror(rc);
  }
}

template <typename RouteT>
void KernelRouteSyncer::reconcileRoute(
    const std::shared_ptr<RouteT>& route,
    const std::shared_ptr<SwitchState>& newState,
    bool isDelete) {
  if (!route) {
    return;
  }
  const auto& prefix = route->prefix();
  folly::IPAddress prefixIp(prefix.network());
  uint8_t prefixLen = prefix.mask();

  if (isDelete) {
    delRoute(prefixIp, prefixLen);
    return;
  }

  // We need to look at the route's forwarding info to pick an interface.
  if (!route->isResolved()) {
    // Unresolved: drop any kernel route we previously installed for this
    // prefix so the kernel doesn't black-hole forward.
    delRoute(prefixIp, prefixLen);
    return;
  }
  const auto& fwdInfo = route->getForwardInfo();
  const auto& nexthops = fwdInfo.getNextHopSet();
  if (nexthops.empty()) {
    delRoute(prefixIp, prefixLen);
    return;
  }

  // Materialize every resolved next-hop so the kernel can ECMP-hash across
  // them. Drop a next-hop if it has no intfID or its veth ifindex can't be
  // resolved; install whatever remains.
  std::vector<ResolvedNh> resolved;
  resolved.reserve(nexthops.size());
  for (const auto& nh : nexthops) {
    if (!nh.intfID().has_value()) {
      XLOG_EVERY_MS(WARN, 5000)
          << "KernelRouteSyncer: next-hop for " << prefixIp << "/"
          << static_cast<int>(prefixLen) << " has no intfID (skipping)";
      continue;
    }
    int oifIndex = ifIndexFromIntfId(newState, static_cast<int>(*nh.intfID()));
    if (oifIndex < 0) {
      XLOG_EVERY_MS(WARN, 5000)
          << "KernelRouteSyncer: no kernel ifindex for intfID=" << *nh.intfID()
          << " (route " << prefixIp << "/" << static_cast<int>(prefixLen)
          << ", skipping nh)";
      continue;
    }
    resolved.push_back(
        ResolvedNh{oifIndex, nh.addr(), static_cast<int>(nh.weight())});
  }

  if (resolved.empty()) {
    XLOG_EVERY_MS(WARN, 5000)
        << "KernelRouteSyncer: no resolvable nexthops for " << prefixIp << "/"
        << static_cast<int>(prefixLen) << " — removing from kernel";
    delRoute(prefixIp, prefixLen);
    return;
  }
  addOrReplaceRoute(prefixIp, prefixLen, resolved, route->isConnected());
}

void KernelRouteSyncer::resyncRoutesForIfIndex(
    int upIfIndex,
    const std::shared_ptr<SwitchState>& newState) {
  if (upIfIndex < 0) {
    return;
  }
  auto fibsInfoMap = newState->getFibsInfoMap();
  if (!fibsInfoMap) {
    return;
  }
  size_t count = 0;
  // Re-install every resolved route in newState whose next-hop egresses the
  // now-up port (matched by-oif). Idempotent: reconcileRoute ->
  // addOrReplaceRoute uses NLM_F_REPLACE|NLM_F_CREATE, so re-installing an
  // already-present route is a no-op. Only routes egressing the up port are
  // touched; routes on other (possibly still-down) ports are left alone.
  auto walkFib = [&](const auto& fib) {
    if (!fib) {
      return;
    }
    for (const auto& routeEntry : std::as_const(*fib)) {
      const auto& route = routeEntry.second;
      if (!route || !route->isResolved()) {
        continue;
      }
      bool egressesPort = false;
      for (const auto& nh : route->getForwardInfo().getNextHopSet()) {
        if (!nh.intfID().has_value()) {
          continue;
        }
        if (ifIndexFromIntfId(newState, static_cast<int>(*nh.intfID())) ==
            upIfIndex) {
          egressesPort = true;
          break;
        }
      }
      if (egressesPort) {
        reconcileRoute(route, newState, /*isDelete=*/false);
        ++count;
      }
    }
  };
  for (const auto& fibInfoEntry : std::as_const(*fibsInfoMap)) {
    const auto& fibInfo = fibInfoEntry.second;
    auto fibsMap = fibInfo->getfibsMap();
    if (!fibsMap) {
      continue;
    }
    for (const auto& fibEntry : std::as_const(*fibsMap)) {
      const auto& fibContainer = fibEntry.second;
      walkFib(fibContainer->getFibV4());
      walkFib(fibContainer->getFibV6());
    }
  }
  if (count > 0) {
    XLOG(INFO) << "KernelRouteSyncer: port-up re-sync on ifindex=" << upIfIndex
               << " re-installed " << count << " route(s)";
  }
}

void KernelRouteSyncer::stateUpdated(const StateDelta& delta) {
  using DeltaFunctions::forEachChanged;
  std::lock_guard<std::mutex> g(mutex_);
  const auto& newState = delta.newState();

  // Walk both v4 and v6 FIBs across all VRFs (cfboss has 1 VRF).
  // The two-level iteration matches the canonical pattern in SaiSwitch.cpp:
  // delta.getFibsInfoDelta() -> per-switch FIB container deltas
  //   -> getFibsMapDelta()    -> per-VRF route delta
  //     -> getFibDelta<v4|v6> -> the v4 / v6 route map delta
  for (const auto& fibInfoDelta : delta.getFibsInfoDelta()) {
    for (const auto& routeDelta : fibInfoDelta.getFibsMapDelta()) {
      forEachChanged(
          routeDelta.getFibDelta<folly::IPAddressV4>(),
          [&](const auto& /*oldR*/, const auto& newR) {
            reconcileRoute(newR, newState, /*isDelete=*/false);
          },
          [&](const auto& addedR) {
            reconcileRoute(addedR, newState, /*isDelete=*/false);
          },
          [&](const auto& removedR) {
            reconcileRoute(removedR, newState, /*isDelete=*/true);
          });
      forEachChanged(
          routeDelta.getFibDelta<folly::IPAddressV6>(),
          [&](const auto& /*oldR*/, const auto& newR) {
            reconcileRoute(newR, newState, /*isDelete=*/false);
          },
          [&](const auto& addedR) {
            reconcileRoute(addedR, newState, /*isDelete=*/false);
          },
          [&](const auto& removedR) {
            reconcileRoute(removedR, newState, /*isDelete=*/true);
          });
    }
  }

  // On a port link flap the Linux kernel purges that interface's routes on
  // link-DOWN, but FBOSS's RIB/FIB does not change (route resolution is
  // recursive through interface routes, not ARP), so no FIB delta fires on
  // link-UP. Re-drive the install path for every FBOSS route egressing a port
  // that just transitioned DOWN->UP so connected/static/dynamic routes are
  // restored. Neighbors auto-relearn via the kernel's re-ARP on veth up.
  forEachChanged(
      delta.getPortsDelta(),
      [&](const std::shared_ptr<Port>& oldPort,
          const std::shared_ptr<Port>& newPort) {
        // Only a genuine DOWN->UP transition (mirrors PortUpdateHandler), to
        // avoid needless churn on unrelated ports deltas.
        if (!oldPort->isUp() && newPort->isUp()) {
          resyncRoutesForIfIndex(
              ifIndexFromPortId(static_cast<int>(newPort->getID())), newState);
        }
      });
}

} // namespace facebook::fboss::cfboss
