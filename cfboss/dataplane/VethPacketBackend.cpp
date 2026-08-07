/*
 *  Copyright (c) 2026, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#include "cfboss/dataplane/VethPacketBackend.h"

#include "cfboss/dataplane/NetlinkUtils.h"
#include "cfboss/dataplane/PortMap.h"

#include <folly/String.h>
#include <folly/logging/xlog.h>

// NOLINTNEXTLINE(misc-include-cleaner): htons resolves via glibc sub-headers
#include <arpa/inet.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <netlink/route/link.h>
#include <netlink/socket.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace facebook::fboss {

namespace {

std::pair<int, int> openAfPacket(const std::string& ifname) {
  int fd = ::socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
  if (fd < 0) {
    throw std::runtime_error(
        "VethPacketBackend: socket(AF_PACKET) failed for " + ifname + ": " +
        folly::errnoStr(errno));
  }
  struct ifreq ifr{};
  std::strncpy(ifr.ifr_name, ifname.c_str(), IFNAMSIZ - 1);
  if (::ioctl(fd, SIOCGIFINDEX, &ifr) < 0) {
    int err = errno;
    ::close(fd);
    throw std::runtime_error(
        "VethPacketBackend: SIOCGIFINDEX failed for " + ifname + ": " +
        folly::errnoStr(err));
  }
  int ifindex = ifr.ifr_ifindex;
  struct sockaddr_ll sll{};
  sll.sll_family = AF_PACKET;
  sll.sll_protocol = htons(ETH_P_ALL);
  sll.sll_ifindex = ifindex;
  if (::bind(fd, reinterpret_cast<struct sockaddr*>(&sll), sizeof(sll)) < 0) {
    int err = errno;
    ::close(fd);
    throw std::runtime_error(
        "VethPacketBackend: bind(AF_PACKET) failed for " + ifname + ": " +
        folly::errnoStr(err));
  }
  return {fd, ifindex};
}

} // namespace

VethPacketBackend::VethPacketBackend(
    std::shared_ptr<const cfboss::PortMap> portMap)
    : portMap_(std::move(portMap)) {
  if (!portMap_) {
    throw std::runtime_error("VethPacketBackend: null PortMap");
  }
  for (const auto& [lane, veth] : portMap_->laneToVeth()) {
    auto [fd, ifindex] = openAfPacket(veth);
    sockets_[veth] = VethSocket{fd, ifindex, veth};
    XLOG(INFO) << "VethPacketBackend: opened AF_PACKET on " << veth
               << " (ifindex=" << ifindex << ", fd=" << fd << ", lane=" << lane
               << ")";
  }
  rxThreads_.reserve(sockets_.size());
  try {
    for (auto& [name, sock] : sockets_) {
      rxThreads_.emplace_back([this, sockPtr = &sock]() { rxLoop(sockPtr); });
    }
  } catch (...) {
    // A constructor throw with threads already running must join them before
    // the members are destroyed — destroying a joinable std::thread calls
    // std::terminate.
    stopThreads_.store(true, std::memory_order_release);
    for (auto& t : rxThreads_) {
      if (t.joinable()) {
        t.join();
      }
    }
    throw;
  }
  XLOG(INFO) << "VethPacketBackend: opened " << sockets_.size()
             << " veth sockets, " << rxThreads_.size() << " RX threads up";
}

VethPacketBackend::~VethPacketBackend() {
  stopThreads_.store(true, std::memory_order_release);
  for (auto& t : rxThreads_) {
    if (t.joinable()) {
      t.join();
    }
  }
  {
    std::lock_guard<std::mutex> g(adminSockMutex_);
    if (adminWriteSock_) {
      ::nl_socket_free(adminWriteSock_);
      adminWriteSock_ = nullptr;
    }
  }
  for (auto& [name, sock] : sockets_) {
    if (sock.fd >= 0) {
      ::close(sock.fd);
    }
  }
}

const VethPacketBackend::VethSocket* VethPacketBackend::socketForVeth(
    const std::string& veth) const {
  auto it = sockets_.find(veth);
  return it == sockets_.end() ? nullptr : &it->second;
}

sai_status_t VethPacketBackend::tx(
    sai_object_id_t tx_port,
    sai_size_t buffer_size,
    const void* buffer) {
  std::string veth;
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = oidToVeth_.find(tx_port);
    if (it == oidToVeth_.end()) {
      XLOG_EVERY_MS(WARN, 1000)
          << "VethPacketBackend: TX for unknown sai port oid=" << std::hex
          << tx_port << " - drop";
      return SAI_STATUS_SUCCESS;
    }
    veth = it->second;
  }
  const VethSocket* sock = socketForVeth(veth);
  if (!sock) {
    XLOG(ERR) << "VethPacketBackend: TX for veth " << veth
              << " has no open socket - drop";
    return SAI_STATUS_FAILURE;
  }
  ssize_t n = ::write(sock->fd, buffer, buffer_size);
  if (n < 0) {
    XLOG_EVERY_MS(WARN, 1000) << "VethPacketBackend: write to " << veth
                              << " failed: " << folly::errnoStr(errno);
    return SAI_STATUS_FAILURE;
  }
  if (static_cast<size_t>(n) != buffer_size) {
    // A truncated frame on the wire is a failed TX; do not report it to
    // FBOSS as delivered.
    XLOG_EVERY_MS(WARN, 1000) << "VethPacketBackend: short write to " << veth
                              << ": " << n << " of " << buffer_size;
    return SAI_STATUS_FAILURE;
  }
  return SAI_STATUS_SUCCESS;
}

void VethPacketBackend::setRxCallback(
    sai_object_id_t switch_id,
    sai_packet_event_notification_fn cb) {
  std::lock_guard<std::mutex> g(mutex_);
  rxSwitchId_ = switch_id;
  rxCallback_ = cb;
  XLOG(INFO) << "VethPacketBackend: RX callback "
             << (cb ? "registered" : "cleared") << " for switch_id=" << std::hex
             << switch_id;
}

void VethPacketBackend::notifyPortUpLocked(sai_object_id_t oid) {
  if (!portStateCallback_) {
    return;
  }
  sai_port_oper_status_notification_t notif{};
  notif.port_id = oid;
  notif.port_state = SAI_PORT_OPER_STATUS_UP;
  portStateCallback_(/*count=*/1, &notif);
  XLOG(INFO) << "VethPacketBackend: notified PORT_OPER_STATUS_UP for oid="
             << std::hex << oid;
}

void VethPacketBackend::setPortStateCallback(
    sai_port_state_change_notification_fn cb) {
  std::lock_guard<std::mutex> g(mutex_);
  portStateCallback_ = cb;
  XLOG(INFO) << "VethPacketBackend: port-state-change callback "
             << (cb ? "registered" : "cleared");
  if (!cb) {
    return;
  }
  // Catch-up: fire UP for every already-bound port. Bootstrap creates the
  // veths UP/LOWER_UP and they stay that way for the container's lifetime.
  for (const auto& [oid, _veth] : oidToVeth_) {
    notifyPortUpLocked(oid);
  }
}

void VethPacketBackend::onPortCreated(
    sai_object_id_t oid,
    const std::vector<uint32_t>& lanes) {
  if (lanes.empty()) {
    XLOG(WARN) << "VethPacketBackend: onPortCreated with empty lanes for oid="
               << std::hex << oid;
    return;
  }
  auto veth = portMap_->vethForLane(lanes.front());
  if (!veth) {
    XLOG(WARN) << "VethPacketBackend: no veth in port_map for first lane="
               << lanes.front() << " (oid=" << std::hex << oid << ")";
    return;
  }
  std::lock_guard<std::mutex> g(mutex_);
  oidToVeth_[oid] = *veth;
  vethToOid_[*veth] = oid;
  XLOG(INFO) << "VethPacketBackend: bound oid=" << std::hex << oid
             << " <-> veth=" << *veth;
  notifyPortUpLocked(oid);
}

void VethPacketBackend::onPortRemoved(sai_object_id_t oid) {
  std::lock_guard<std::mutex> g(mutex_);
  auto it = oidToVeth_.find(oid);
  if (it != oidToVeth_.end()) {
    vethToOid_.erase(it->second);
    oidToVeth_.erase(it);
  }
}

void VethPacketBackend::rxLoop(const VethSocket* sock) {
  constexpr size_t kMaxPacketSize = 9216; // jumbo (MTU=9412 on cfboss intfs)
  std::vector<uint8_t> buf(kMaxPacketSize);

  while (!stopThreads_.load(std::memory_order_acquire)) {
    struct pollfd pfd{};
    pfd.fd = sock->fd;
    pfd.events = POLLIN;
    int rc = ::poll(&pfd, 1, 500); // 500ms — observe stopThreads_ within ~500ms
    if (rc < 0) {
      if (errno == EINTR) {
        continue;
      }
      XLOG_EVERY_MS(WARN, 5000) << "VethPacketBackend: poll failed on "
                                << sock->name << ": " << folly::errnoStr(errno);
      continue;
    }
    if (rc == 0 || !(pfd.revents & POLLIN)) {
      continue;
    }

    // recvfrom with sockaddr_ll so we can filter PACKET_OUTGOING (TX echoes).
    struct sockaddr_ll sll{};
    socklen_t slen = sizeof(sll);
    ssize_t n = ::recvfrom(
        sock->fd,
        buf.data(),
        buf.size(),
        MSG_DONTWAIT,
        reinterpret_cast<struct sockaddr*>(&sll),
        &slen);
    if (n <= 0) {
      continue;
    }
    if (sll.sll_pkttype == PACKET_OUTGOING) {
      continue;
    }

    sai_packet_event_notification_fn cb = nullptr;
    sai_object_id_t switchId = 0;
    sai_object_id_t portOid = 0;
    {
      std::lock_guard<std::mutex> g(mutex_);
      cb = rxCallback_;
      switchId = rxSwitchId_;
      auto it = vethToOid_.find(sock->name);
      if (it != vethToOid_.end()) {
        portOid = it->second;
      }
    }
    if (!cb || portOid == 0) {
      continue;
    }

    sai_attribute_t attrs[1];
    attrs[0].id = SAI_HOSTIF_PACKET_ATTR_INGRESS_PORT;
    attrs[0].value.oid = portOid;
    XLOG_EVERY_MS(DBG3, 1000)
        << "VethPacketBackend: RX on " << sock->name << " " << n
        << " bytes -> SAI callback (port oid=" << std::hex << portOid << ")";
    // Serialize SAI callback invocations across the per-veth RX threads;
    // FBOSS's RxPktEventQueueType is a single-producer BoundedQueue and
    // would otherwise CHECK-fail under concurrent enqueue.
    std::lock_guard<std::mutex> deliveryLock(rxDeliveryMutex_);
    cb(switchId,
       static_cast<sai_size_t>(n),
       buf.data(),
       /*attr_count=*/1,
       attrs);
  }
  XLOG(INFO) << "VethPacketBackend: RX loop exiting for " << sock->name;
}

namespace {

// Read a single uint64_t value from /sys/class/net/<veth>/statistics/<stat>.
// Returns 0 on any failure (matches the historical placeholder behavior).
uint64_t readVethStat(const std::string& veth, const std::string& stat) {
  std::ifstream f("/sys/class/net/" + veth + "/statistics/" + stat);
  uint64_t v = 0;
  if (!(f >> v)) {
    return 0;
  }
  return v;
}

} // namespace

::nl_sock* VethPacketBackend::getAdminWriteSocket() {
  // Caller must hold adminSockMutex_.
  if (adminWriteSock_) {
    return adminWriteSock_;
  }
  adminWriteSock_ =
      cfboss::openRouteNetlinkSocket("VethPacketBackend admin-write");
  if (adminWriteSock_) {
    XLOG(INFO) << "VethPacketBackend: admin-write netlink socket connected";
  }
  return adminWriteSock_;
}

void VethPacketBackend::onAdminStateChange(
    sai_object_id_t oid,
    bool isAdminUp) {
  std::string veth;
  int ifindex = 0;
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = oidToVeth_.find(oid);
    if (it == oidToVeth_.end()) {
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: onAdminStateChange for unknown oid=0x"
          << std::hex << oid;
      return;
    }
    veth = it->second;
  }
  auto sit = sockets_.find(veth);
  if (sit == sockets_.end()) {
    return;
  }
  ifindex = sit->second.ifindex;

  std::lock_guard<std::mutex> g(adminSockMutex_);
  ::nl_sock* sock = getAdminWriteSocket();
  if (!sock) {
    return;
  }
  ::rtnl_link* link = ::rtnl_link_alloc();
  if (!link) {
    XLOG(ERR) << "VethPacketBackend: rtnl_link_alloc failed for " << veth;
    return;
  }
  ::rtnl_link_set_ifindex(link, ifindex);
  if (isAdminUp) {
    ::rtnl_link_set_flags(link, IFF_UP);
  } else {
    ::rtnl_link_unset_flags(link, IFF_UP);
  }
  ::rtnl_link* changes = ::rtnl_link_alloc();
  if (!changes) {
    ::rtnl_link_put(link);
    return;
  }
  ::rtnl_link_set_ifindex(changes, ifindex);
  if (isAdminUp) {
    ::rtnl_link_set_flags(changes, IFF_UP);
  } else {
    ::rtnl_link_unset_flags(changes, IFF_UP);
  }
  int rc = ::rtnl_link_change(sock, link, changes, 0);
  ::rtnl_link_put(changes);
  ::rtnl_link_put(link);
  if (rc < 0) {
    XLOG(WARN) << "VethPacketBackend: rtnl_link_change("
               << (isAdminUp ? "UP" : "DOWN") << ") for " << veth
               << " failed: " << ::nl_geterror(rc);
    return;
  }
  XLOG(INFO) << "VethPacketBackend: kernel link " << (isAdminUp ? "UP" : "DOWN")
             << " on " << veth << " (oid=0x" << std::hex << oid << std::dec
             << ")";
}

sai_status_t VethPacketBackend::getPortStats(
    sai_object_id_t oid,
    uint32_t num_of_counters,
    const sai_stat_id_t* counter_ids,
    uint64_t* counters) {
  std::string veth;
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = oidToVeth_.find(oid);
    if (it == oidToVeth_.end()) {
      for (uint32_t i = 0; i < num_of_counters; ++i) {
        counters[i] = 0;
      }
      return SAI_STATUS_SUCCESS;
    }
    veth = it->second;
  }

  const uint64_t rxBytes = readVethStat(veth, "rx_bytes");
  const uint64_t rxPkts = readVethStat(veth, "rx_packets");
  const uint64_t rxMulticast = readVethStat(veth, "multicast");
  const uint64_t txBytes = readVethStat(veth, "tx_bytes");
  const uint64_t txPkts = readVethStat(veth, "tx_packets");

  for (uint32_t i = 0; i < num_of_counters; ++i) {
    switch (counter_ids[i]) {
      case SAI_PORT_STAT_IF_IN_OCTETS:
        counters[i] = rxBytes;
        break;
      case SAI_PORT_STAT_IF_IN_UCAST_PKTS:
        counters[i] = (rxPkts > rxMulticast) ? (rxPkts - rxMulticast) : 0;
        break;
      case SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS:
      case SAI_PORT_STAT_IF_IN_MULTICAST_PKTS:
        counters[i] = rxMulticast;
        break;
      case SAI_PORT_STAT_IF_OUT_OCTETS:
        counters[i] = txBytes;
        break;
      case SAI_PORT_STAT_IF_OUT_UCAST_PKTS:
        counters[i] = txPkts;
        break;
      default:
        counters[i] = 0;
        break;
    }
  }
  return SAI_STATUS_SUCCESS;
}

} // namespace facebook::fboss
