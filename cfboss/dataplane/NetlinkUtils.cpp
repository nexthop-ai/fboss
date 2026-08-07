// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/NetlinkUtils.h"
#include "cfboss/dataplane/PortMap.h"

#include "fboss/agent/state/Interface.h"

#include <folly/String.h>
#include <folly/logging/xlog.h>

#include <net/if.h>
#include <netlink/addr.h>
#include <netlink/netlink.h>
#include <netlink/socket.h>

#include <cerrno>

namespace facebook::fboss::cfboss {

::nl_addr* makeNlAddr(const folly::IPAddress& ip, uint8_t prefixLen) {
  ::nl_addr* a = nullptr;
  if (ip.isV4()) {
    auto v4 = ip.asV4().toLong(); // network byte order
    a = ::nl_addr_build(AF_INET, &v4, sizeof(v4));
  } else {
    auto v6 = ip.asV6().toBinary();
    a = ::nl_addr_build(AF_INET6, v6.data(), v6.size());
  }
  if (a) {
    ::nl_addr_set_prefixlen(a, prefixLen);
  }
  return a;
}

int ifIndexForVeth(const std::string& veth) {
  unsigned idx = ::if_nametoindex(veth.c_str());
  if (idx == 0) {
    XLOG_EVERY_MS(WARN, 5000)
        << "cfboss: if_nametoindex failed for " << veth
        << " (does the veth exist?): " << folly::errnoStr(errno);
    return -1;
  }
  return static_cast<int>(idx);
}

std::optional<std::string> resolveVeth(
    const PortMap& portMap,
    const Interface& intf) {
  auto portId = intf.getPortIDf();
  if (!portId) {
    // Non-PORT interface type (e.g. VLAN router interfaces): cfboss uses
    // port-type interfaces, so there is no backing veth.
    return std::nullopt;
  }
  // On cfboss the PortID equals the first SAI lane (see port_map.json).
  auto vethName = portMap.vethForLane(static_cast<uint32_t>(*portId));
  if (!vethName) {
    XLOG_EVERY_MS(WARN, 5000) << "cfboss: no PortMap entry for port " << *portId
                              << " (interface " << intf.getID() << ")";
  }
  return vethName;
}

::nl_sock* openRouteNetlinkSocket(const char* owner) {
  ::nl_sock* sock = ::nl_socket_alloc();
  if (!sock) {
    XLOG(ERR) << owner << ": nl_socket_alloc failed";
    return nullptr;
  }
  int rc = ::nl_connect(sock, NETLINK_ROUTE);
  if (rc < 0) {
    XLOG(ERR) << owner
              << ": nl_connect(NETLINK_ROUTE) failed: " << ::nl_geterror(rc);
    ::nl_socket_free(sock);
    return nullptr;
  }
  return sock;
}

} // namespace facebook::fboss::cfboss
