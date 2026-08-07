// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/VethIpInstaller.h"
#include "cfboss/dataplane/NetlinkUtils.h"
#include "cfboss/dataplane/PortMap.h"

#include "fboss/agent/state/DeltaFunctions.h"
#include "fboss/agent/state/Interface.h"
#include "fboss/agent/state/StateDelta.h"

#include <folly/logging/xlog.h>

#include <netlink/addr.h>
#include <netlink/route/addr.h>
#include <netlink/route/link.h>
#include <netlink/socket.h>

namespace facebook::fboss::cfboss {

VethIpInstaller::VethIpInstaller(std::shared_ptr<const PortMap> portMap)
    : portMap_(std::move(portMap)) {
  if (!portMap_) {
    throw std::runtime_error("VethIpInstaller: null PortMap");
  }
  sock_ = openRouteNetlinkSocket("VethIpInstaller");
  if (!sock_) {
    throw std::runtime_error("VethIpInstaller: failed to open netlink socket");
  }
  XLOG(INFO) << "VethIpInstaller: ready (netlink socket connected)";
}

VethIpInstaller::~VethIpInstaller() {
  if (sock_) {
    ::nl_socket_free(sock_);
  }
}

void VethIpInstaller::addAddrOnVeth(
    int ifindex,
    const folly::IPAddress& ip,
    uint8_t prefixLen) {
  AddrKey key{ifindex, {ip, prefixLen}};
  {
    std::lock_guard<std::mutex> g(mutex_);
    if (installed_.count(key)) {
      return;
    }
  }
  ::rtnl_addr* addr = ::rtnl_addr_alloc();
  if (!addr) {
    XLOG(ERR) << "VethIpInstaller: rtnl_addr_alloc failed";
    return;
  }
  ::nl_addr* nl = makeNlAddr(ip, prefixLen);
  if (!nl) {
    XLOG(ERR) << "VethIpInstaller: nl_addr build failed for " << ip;
    ::rtnl_addr_put(addr);
    return;
  }
  ::rtnl_addr_set_ifindex(addr, ifindex);
  ::rtnl_addr_set_local(addr, nl);
  ::rtnl_addr_set_family(addr, ip.isV4() ? AF_INET : AF_INET6);
  int rc = ::rtnl_addr_add(sock_, addr, NLM_F_REPLACE | NLM_F_CREATE);
  ::nl_addr_put(nl);
  ::rtnl_addr_put(addr);
  if (rc < 0 && rc != -NLE_EXIST) {
    XLOG(ERR) << "VethIpInstaller: rtnl_addr_add(" << ip << "/"
              << static_cast<int>(prefixLen) << " ifindex=" << ifindex
              << ") failed: " << ::nl_geterror(rc);
    return;
  }
  std::lock_guard<std::mutex> g(mutex_);
  installed_.insert(key);
  XLOG(INFO) << "VethIpInstaller: assigned " << ip << "/"
             << static_cast<int>(prefixLen) << " to ifindex=" << ifindex;
}

void VethIpInstaller::delAddrOnVeth(
    int ifindex,
    const folly::IPAddress& ip,
    uint8_t prefixLen) {
  AddrKey key{ifindex, {ip, prefixLen}};
  {
    std::lock_guard<std::mutex> g(mutex_);
    if (!installed_.count(key)) {
      return;
    }
  }
  ::rtnl_addr* addr = ::rtnl_addr_alloc();
  if (!addr) {
    XLOG(ERR) << "VethIpInstaller: rtnl_addr_alloc failed (delete)";
    return;
  }
  ::nl_addr* nl = makeNlAddr(ip, prefixLen);
  if (!nl) {
    ::rtnl_addr_put(addr);
    return;
  }
  ::rtnl_addr_set_ifindex(addr, ifindex);
  ::rtnl_addr_set_local(addr, nl);
  ::rtnl_addr_set_family(addr, ip.isV4() ? AF_INET : AF_INET6);
  int rc = ::rtnl_addr_delete(sock_, addr, 0);
  ::nl_addr_put(nl);
  ::rtnl_addr_put(addr);
  if (rc < 0 && rc != -NLE_OBJ_NOTFOUND) {
    // A genuine delete failure leaves the address on the veth; keep the key
    // in installed_ (and do not log a removal) so the bookkeeping stays in
    // sync with the kernel — mirroring the add path, which only records an
    // address after the kernel accepted it.
    XLOG(WARN) << "VethIpInstaller: rtnl_addr_delete(" << ip << "/"
               << static_cast<int>(prefixLen) << " ifindex=" << ifindex
               << ") failed: " << ::nl_geterror(rc);
    return;
  }
  std::lock_guard<std::mutex> g(mutex_);
  installed_.erase(key);
  XLOG(INFO) << "VethIpInstaller: removed " << ip << "/"
             << static_cast<int>(prefixLen) << " from ifindex=" << ifindex;
}

void VethIpInstaller::setMacOnVeth(int ifindex, folly::MacAddress mac) {
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = installedMacs_.find(ifindex);
    if (it != installedMacs_.end() && it->second == mac) {
      return;
    }
  }
  ::rtnl_link* change = ::rtnl_link_alloc();
  if (!change) {
    XLOG(ERR) << "VethIpInstaller: rtnl_link_alloc failed (MAC)";
    return;
  }
  auto bytes = mac.bytes();
  ::nl_addr* lladdr = ::nl_addr_build(AF_LLC, bytes, folly::MacAddress::SIZE);
  if (!lladdr) {
    XLOG(ERR) << "VethIpInstaller: nl_addr_build failed for MAC " << mac;
    ::rtnl_link_put(change);
    return;
  }
  ::rtnl_link_set_addr(change, lladdr);
  ::rtnl_link_set_ifindex(change, ifindex);
  // Pass the same link as both orig and changes; the ifindex set above is what
  // identifies the target netdev.
  int rc = ::rtnl_link_change(sock_, change, change, 0);
  ::nl_addr_put(lladdr);
  ::rtnl_link_put(change);
  if (rc < 0) {
    XLOG(ERR) << "VethIpInstaller: rtnl_link_change(MAC=" << mac
              << " ifindex=" << ifindex << ") failed: " << ::nl_geterror(rc);
    return;
  }
  std::lock_guard<std::mutex> g(mutex_);
  installedMacs_[ifindex] = mac;
  XLOG(INFO) << "VethIpInstaller: aligned ifindex=" << ifindex << " MAC to "
             << mac;
}

std::optional<std::string> VethIpInstaller::vethForInterface(
    const std::shared_ptr<Interface>& intf) {
  if (!intf) {
    return std::nullopt;
  }
  return resolveVeth(*portMap_, *intf);
}

void VethIpInstaller::stateUpdated(const StateDelta& delta) {
  using DeltaFunctions::forEachChanged;

  auto applyAdd = [&](const std::shared_ptr<Interface>& intf) {
    auto vethName = vethForInterface(intf);
    if (!vethName) {
      return;
    }
    int ifindex = ifIndexForVeth(*vethName);
    if (ifindex < 0) {
      return;
    }
    setMacOnVeth(ifindex, intf->getMac());
    for (const auto& [ip, prefix] : intf->getAddressesCopy()) {
      addAddrOnVeth(ifindex, ip, prefix);
    }
  };

  auto applyDel = [&](const std::shared_ptr<Interface>& intf) {
    auto vethName = vethForInterface(intf);
    if (!vethName) {
      return;
    }
    int ifindex = ifIndexForVeth(*vethName);
    if (ifindex < 0) {
      return;
    }
    for (const auto& [ip, prefix] : intf->getAddressesCopy()) {
      delAddrOnVeth(ifindex, ip, prefix);
    }
  };

  forEachChanged(
      delta.getIntfsDelta(),
      [&](const std::shared_ptr<Interface>& oldIntf,
          const std::shared_ptr<Interface>& newIntf) {
        // Address change: diff old vs new
        auto vethName = vethForInterface(newIntf);
        if (!vethName) {
          return;
        }
        int ifindex = ifIndexForVeth(*vethName);
        if (ifindex < 0) {
          return;
        }
        if (oldIntf->getMac() != newIntf->getMac()) {
          setMacOnVeth(ifindex, newIntf->getMac());
        }
        auto oldAddrs = oldIntf->getAddressesCopy();
        auto newAddrs = newIntf->getAddressesCopy();
        for (const auto& [ip, prefix] : oldAddrs) {
          auto it = newAddrs.find(ip);
          if (it == newAddrs.end() || it->second != prefix) {
            delAddrOnVeth(ifindex, ip, prefix);
          }
        }
        for (const auto& [ip, prefix] : newAddrs) {
          auto it = oldAddrs.find(ip);
          if (it == oldAddrs.end() || it->second != prefix) {
            addAddrOnVeth(ifindex, ip, prefix);
          }
        }
      },
      [&](const std::shared_ptr<Interface>& addedIntf) { applyAdd(addedIntf); },
      [&](const std::shared_ptr<Interface>& removedIntf) {
        applyDel(removedIntf);
      });
}

} // namespace facebook::fboss::cfboss
