// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/NetlinkUtils.h"

#include <folly/logging/xlog.h>

#include <netlink/netlink.h>
#include <netlink/socket.h>

namespace facebook::fboss::cfboss {

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
