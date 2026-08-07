// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#pragma once

struct nl_sock;

namespace facebook::fboss::cfboss {

// Open a connected NETLINK_ROUTE socket (nl_socket_alloc + nl_connect).
// Returns nullptr on failure; `owner` names the caller in the diagnostic log.
::nl_sock* openRouteNetlinkSocket(const char* owner);

} // namespace facebook::fboss::cfboss
