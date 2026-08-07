// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#pragma once

#include "fboss/agent/StateObserver.h"

#include <folly/IPAddress.h>
#include <folly/MacAddress.h>

#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <utility>

struct nl_sock;

namespace facebook::fboss {
class StateDelta;
class Interface;
} // namespace facebook::fboss

namespace facebook::fboss::cfboss {

class PortMap;

/**
 * Watches the FBOSS InterfaceMap and assigns/removes IP addresses on the
 * corresponding kernel veth (named fboss_p<N>) using libnl3 rtnl_addr_add /
 * rtnl_addr_delete.
 *
 * The mapping InterfaceID -> veth resolves through the interface's own PortID
 * (PORT-type router interfaces only; PortID == first SAI lane on cfboss) and
 * the PortMap. Non-PORT interfaces (e.g. VLAN router interfaces) have no port
 * and are skipped, which suits the cfboss single-port-per-interface topology.
 */
class VethIpInstaller : public StateObserver {
 public:
  explicit VethIpInstaller(std::shared_ptr<const PortMap> portMap);
  ~VethIpInstaller() override;

  void stateUpdated(const StateDelta& delta) override;

 private:
  using AddrKey = std::pair<int, std::pair<folly::IPAddress, uint8_t>>;

  // Resolve InterfaceID -> veth name via the interface's PortID -> PortMap.
  // Returns std::nullopt if the interface has no resolvable veth.
  std::optional<std::string> vethForInterface(
      const std::shared_ptr<Interface>& intf);

  // libnl helpers; both log and swallow errors (best-effort sync).
  void
  addAddrOnVeth(int ifindex, const folly::IPAddress& ip, uint8_t prefixLen);
  void
  delAddrOnVeth(int ifindex, const folly::IPAddress& ip, uint8_t prefixLen);

  // Align kernel netdev MAC to FBOSS's per-interface MAC. Required because
  // FBOSS emits ARP/NDP using its own platform MAC; if the veth's link
  // address does not match, kernel-side neighbors learn the FBOSS MAC and
  // their unicast frames arrive at the veth with a dst MAC that the kernel
  // IP layer rejects (only AF_PACKET sees them).
  void setMacOnVeth(int ifindex, folly::MacAddress mac);

  std::shared_ptr<const PortMap> portMap_;
  ::nl_sock* sock_{nullptr};

  // Track every (ifindex, ip, prefix) we installed so we never re-add or
  // try to remove something we don't own.
  std::mutex mutex_;
  std::set<AddrKey> installed_;
  std::map<int, folly::MacAddress> installedMacs_;
};

} // namespace facebook::fboss::cfboss
