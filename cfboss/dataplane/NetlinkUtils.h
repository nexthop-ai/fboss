// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#pragma once

#include <folly/IPAddress.h>

#include <optional>
#include <string>

struct nl_addr;
struct nl_sock;

namespace facebook::fboss {
class Interface;
namespace cfboss {
class PortMap;

// Build an nl_addr from a folly::IPAddress with the given prefix length.
// Returns nullptr on failure; the caller owns the result (nl_addr_put()).
::nl_addr* makeNlAddr(const folly::IPAddress& ip, uint8_t prefixLen);

// Resolve a veth name (fboss_p<N>) to its kernel ifindex via if_nametoindex.
// Returns -1 (with a rate-limited warning) if the veth does not exist.
int ifIndexForVeth(const std::string& veth);

// Resolve a router interface to its backing veth name through the interface's
// PortID and the PortMap. PORT-type interfaces only (on cfboss the PortID is
// the first SAI lane); non-PORT interfaces (e.g. VLAN router interfaces) have
// no backing veth and return nullopt.
std::optional<std::string> resolveVeth(
    const PortMap& portMap,
    const Interface& intf);

// Open a connected NETLINK_ROUTE socket (nl_socket_alloc + nl_connect).
// Returns nullptr on failure; `owner` names the caller in the diagnostic log.
::nl_sock* openRouteNetlinkSocket(const char* owner);

} // namespace cfboss
} // namespace facebook::fboss
