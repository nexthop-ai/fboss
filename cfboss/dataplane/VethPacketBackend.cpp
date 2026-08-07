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

#include <fmt/format.h>

// NOLINTNEXTLINE(misc-include-cleaner): htons resolves via glibc sub-headers
#include <arpa/inet.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/rtnetlink.h>
#include <net/if.h>
#include <netlink/msg.h>
#include <netlink/route/link.h>
#include <netlink/socket.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <fstream>
#include <optional>
#include <stdexcept>
#include <thread>

namespace facebook::fboss {

namespace {

// Production seam: the real host syscalls. Opening an AF_PACKET socket needs
// CAP_NET_RAW and the sysfs counters only exist for real interfaces, so tests
// substitute a fake VethSyscalls to drive the backend without either.
class RealVethSyscalls : public VethSyscalls {
 public:
  std::pair<int, int> openPacketSocket(const std::string& ifname) override {
    int fd = ::socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (fd < 0) {
      throw std::runtime_error(
          fmt::format(
              "VethPacketBackend: socket(AF_PACKET) failed for {}: {}",
              ifname,
              folly::errnoStr(errno)));
    }
    struct ifreq ifr{};
    std::strncpy(ifr.ifr_name, ifname.c_str(), IFNAMSIZ - 1);
    if (::ioctl(fd, SIOCGIFINDEX, &ifr) < 0) {
      int err = errno;
      ::close(fd);
      throw std::runtime_error(
          fmt::format(
              "VethPacketBackend: SIOCGIFINDEX failed for {}: {}",
              ifname,
              folly::errnoStr(err)));
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
          fmt::format(
              "VethPacketBackend: bind(AF_PACKET) failed for {}: {}",
              ifname,
              folly::errnoStr(err)));
    }
    return {fd, ifindex};
  }

  uint64_t readInterfaceStat(const std::string& veth, const std::string& stat)
      override {
    std::ifstream f(fmt::format("/sys/class/net/{}/statistics/{}", veth, stat));
    uint64_t v = 0;
    if (!(f >> v)) {
      return 0;
    }
    return v;
  }
};

} // namespace

std::shared_ptr<VethSyscalls> makeDefaultVethSyscalls() {
  return std::make_shared<RealVethSyscalls>();
}

VethPacketBackend::VethSocket::VethSocket(int fd, int ifindex, std::string name)
    : fd(fd), ifindex(ifindex), name(std::move(name)) {}

VethPacketBackend::VethSocket::~VethSocket() {
  if (fd >= 0) {
    ::close(fd);
  }
}

VethPacketBackend::VethPacketBackend(
    std::shared_ptr<const cfboss::PortMap> portMap,
    std::shared_ptr<VethSyscalls> syscalls)
    : portMap_(std::move(portMap)), syscalls_(std::move(syscalls)) {
  if (!portMap_) {
    throw std::runtime_error("VethPacketBackend: null PortMap");
  }
  if (!syscalls_) {
    throw std::runtime_error("VethPacketBackend: null VethSyscalls");
  }
  for (const auto& [lane, veth] : portMap_->laneToVeth()) {
    auto [fd, ifindex] = syscalls_->openPacketSocket(veth);
    sockets_.try_emplace(veth, fd, ifindex, veth);
    ifindexToVeth_[ifindex] = veth;
    lastLinkUp_[veth] = true; // veth bootstrap brings each side IFF_UP.
    XLOG(INFO) << "VethPacketBackend: opened AF_PACKET on " << veth
               << " (ifindex=" << ifindex << ", fd=" << fd << ", lane=" << lane
               << ")";
  }
  rxThreads_.reserve(sockets_.size());
  try {
    for (auto& [name, sock] : sockets_) {
      rxThreads_.emplace_back([this, sockPtr = &sock]() { rxLoop(sockPtr); });
    }
    linkStateSubThread_ = std::thread([this]() { linkStateSubscribeLoop(); });
  } catch (...) {
    // A constructor throw with threads already running must join them before
    // the members are destroyed — destroying a joinable std::thread calls
    // std::terminate. (Open fds are released by ~VethSocket regardless.)
    stopThreads_.store(true, std::memory_order_release);
    for (auto& t : rxThreads_) {
      if (t.joinable()) {
        t.join();
      }
    }
    if (linkStateSubThread_.joinable()) {
      linkStateSubThread_.join();
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
  if (linkStateSubThread_.joinable()) {
    linkStateSubThread_.join();
  }
  {
    std::lock_guard<std::mutex> g(adminSockMutex_);
    if (adminWriteSock_) {
      ::nl_socket_free(adminWriteSock_);
      adminWriteSock_ = nullptr;
    }
  }
  // Per-veth fds are closed by ~VethSocket when sockets_ is destroyed.
}

const VethPacketBackend::VethSocket* FOLLY_NULLABLE
VethPacketBackend::socketForVeth(const std::string& veth) const {
  auto it = sockets_.find(veth);
  return it == sockets_.end() ? nullptr : &it->second;
}

sai_status_t VethPacketBackend::tx(
    sai_object_id_t tx_port,
    sai_size_t buffer_size,
    const void* buffer) {
  const VethSocket* sock = nullptr;
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = oidToSocket_.find(tx_port);
    if (it == oidToSocket_.end()) {
      XLOG_EVERY_MS(WARN, 1000)
          << "VethPacketBackend: TX for unknown sai port oid=" << std::hex
          << tx_port << " - drop";
      return SAI_STATUS_SUCCESS;
    }
    sock = it->second;
  }
  ssize_t n = ::write(sock->fd, buffer, buffer_size);
  if (n < 0) {
    XLOG_EVERY_MS(WARN, 1000) << "VethPacketBackend: write to " << sock->name
                              << " failed: " << folly::errnoStr(errno);
    return SAI_STATUS_FAILURE;
  }
  if (static_cast<size_t>(n) != buffer_size) {
    // A truncated frame on the wire is a failed TX; do not report it to
    // FBOSS as delivered.
    XLOG_EVERY_MS(WARN, 1000)
        << "VethPacketBackend: short write to " << sock->name << ": " << n
        << " of " << buffer_size;
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

void VethPacketBackend::notifyPortStateUnlocked(
    sai_port_state_change_notification_fn cb,
    sai_object_id_t oid,
    bool isUp) {
  if (!cb) {
    return;
  }
  sai_port_oper_status_notification_t notif{};
  notif.port_id = oid;
  notif.port_state = isUp ? SAI_PORT_OPER_STATUS_UP : SAI_PORT_OPER_STATUS_DOWN;
  cb(/*count=*/1, &notif);
  XLOG(INFO) << "VethPacketBackend: notified PORT_OPER_STATUS_"
             << (isUp ? "UP" : "DOWN") << " for oid=" << std::hex << oid;
}

void VethPacketBackend::setPortStateCallback(
    sai_port_state_change_notification_fn cb) {
  std::vector<sai_object_id_t> catchUpOids;
  {
    std::lock_guard<std::mutex> g(mutex_);
    portStateCallback_ = cb;
    if (cb) {
      // Snapshot the already-bound ports under the lock; deliver the callback
      // for them only after releasing mutex_ (see notifyPortStateUnlocked).
      catchUpOids.reserve(oidToSocket_.size());
      for (const auto& [oid, _sock] : oidToSocket_) {
        catchUpOids.push_back(oid);
      }
    }
  }
  XLOG(INFO) << "VethPacketBackend: port-state-change callback "
             << (cb ? "registered" : "cleared");
  // Catch-up: fire UP for every already-bound port. Bootstrap creates the
  // veths UP/LOWER_UP and they stay that way for the container's lifetime.
  for (auto oid : catchUpOids) {
    notifyPortStateUnlocked(cb, oid, /*isUp=*/true);
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
  const VethSocket* sock = socketForVeth(*veth);
  if (!sock) {
    XLOG(WARN) << "VethPacketBackend: onPortCreated for veth=" << *veth
               << " with no open socket (oid=" << std::hex << oid << ")";
    return;
  }
  sai_port_state_change_notification_fn cb = nullptr;
  bool isUp = true;
  {
    std::lock_guard<std::mutex> g(mutex_);
    sock->oid_.store(oid, std::memory_order_release);
    oidToSocket_[oid] = sock;
    cb = portStateCallback_;
    // Fire the tracked link state, not an unconditional UP: if the veth went
    // down between socket-open and port-create, reporting UP would desync
    // SAI's view from lastLinkUp_ and suppress the next genuine DOWN edge
    // (no transition would be observed).
    auto lit = lastLinkUp_.find(*veth);
    isUp = lit == lastLinkUp_.end() ? true : lit->second;
  }
  XLOG(INFO) << "VethPacketBackend: bound oid=" << std::hex << oid
             << " <-> veth=" << *veth;
  notifyPortStateUnlocked(cb, oid, isUp);
}

void VethPacketBackend::onPortRemoved(sai_object_id_t oid) {
  std::lock_guard<std::mutex> g(mutex_);
  auto it = oidToSocket_.find(oid);
  if (it != oidToSocket_.end()) {
    it->second->oid_.store(0, std::memory_order_release);
    oidToSocket_.erase(it);
  }
}

void VethPacketBackend::rxLoop(const VethSocket* sock) {
  // Must exceed the documented cfboss MTU (9412) + L2 header (14) + VLAN tag
  // (4). 9600 leaves headroom over 9412+18.
  constexpr size_t kMaxPacketSize = 9600; // jumbo (MTU=9412 on cfboss intfs)
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
    if (n < 0) {
      // EAGAIN/EWOULDBLOCK: nothing queued (MSG_DONTWAIT). EINTR: interrupted.
      // All transient — retry quietly. Any other errno (ENETDOWN, ENOBUFS,
      // ...) is a real error that would otherwise busy-loop with no diagnostic.
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
        continue;
      }
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: recvfrom on " << sock->name
          << " failed: " << folly::errnoStr(errno);
      continue;
    }
    if (n == 0) {
      continue;
    }
    if (sll.sll_pkttype == PACKET_OUTGOING) {
      continue;
    }

    // The bound port OID is cached on the socket, so the hot RX path reads
    // it lock-free instead of taking mutex_ to consult a veth->oid table per
    // packet. 0 means no SAI port is bound (before create_port_fn or after
    // remove) -- drop the frame rather than deliver against a stale oid.
    sai_object_id_t portOid = sock->oid_.load(std::memory_order_acquire);
    if (portOid == 0) {
      continue;
    }
    sai_packet_event_notification_fn cb = nullptr;
    sai_object_id_t switchId = 0;
    {
      std::lock_guard<std::mutex> g(mutex_);
      cb = rxCallback_;
      switchId = rxSwitchId_;
    }
    if (!cb) {
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

// libnl callback for RTM_NEWLINK / RTM_DELLINK multicast messages. Parses
// the netlink-message ifinfomsg header to get ifindex + flags and forwards
// to VethPacketBackend::onKernelLinkEvent. `arg` is the VethPacketBackend.
//
// The link is treated as UP iff IFF_UP is set in the ifinfomsg flags — the
// kernel administrative link state, the same flag the veth bootstrap sets
// and onAdminStateChange toggles. IFLA_OPERSTATE / carrier state is not
// consulted (a veth peer's carrier drop leaves IFF_UP set).
int handleRtnLinkMessage(::nl_msg* msg, void* arg) {
  auto* backend = static_cast<VethPacketBackend*>(arg);
  if (!backend || !msg) {
    return NL_OK;
  }
  ::nlmsghdr* hdr = ::nlmsg_hdr(msg);
  if (!hdr) {
    return NL_OK;
  }
  if (hdr->nlmsg_type != RTM_NEWLINK && hdr->nlmsg_type != RTM_DELLINK) {
    return NL_OK;
  }
  if (::nlmsg_datalen(hdr) < static_cast<int>(sizeof(::ifinfomsg))) {
    return NL_OK;
  }
  auto* ifi = static_cast<::ifinfomsg*>(::nlmsg_data(hdr));
  bool isUp = hdr->nlmsg_type != RTM_DELLINK && (ifi->ifi_flags & IFF_UP) != 0;
  backend->onKernelLinkEvent(ifi->ifi_index, isUp);
  return NL_OK;
}

} // namespace

void VethPacketBackend::onKernelLinkEvent(int ifindex, bool isUp) {
  auto vit = ifindexToVeth_.find(ifindex);
  if (vit == ifindexToVeth_.end()) {
    // Not a veth we own — e.g. lo, eth0, peer side. Ignore.
    return;
  }
  const std::string& veth = vit->second;

  sai_port_state_change_notification_fn cb = nullptr;
  sai_object_id_t oid = 0;
  {
    std::lock_guard<std::mutex> g(mutex_);
    auto prev = lastLinkUp_.find(veth);
    bool prevUp = (prev != lastLinkUp_.end()) ? prev->second : true;
    if (isUp == prevUp) {
      return; // No transition, suppress duplicate.
    }
    lastLinkUp_[veth] = isUp;

    const VethSocket* sock = socketForVeth(veth);
    oid = sock ? sock->oid_.load(std::memory_order_acquire) : 0;
    if (oid == 0) {
      // Veth known but no SAI port OID bound yet (between sock open and
      // FakeSai create_port_fn). The first onPortCreated will fire UP.
      return;
    }
    cb = portStateCallback_;
  }
  notifyPortStateUnlocked(cb, oid, isUp);
}

void VethPacketBackend::linkStateSubscribeLoop() {
  // Dedicated rtnetlink socket subscribed to RTNLGRP_LINK. Multicast
  // RTM_NEWLINK/RTM_DELLINK messages arrive on actual kernel transitions —
  // no polling cadence, no wakeups when nothing has happened.
  ::nl_sock* sock = ::nl_socket_alloc();
  if (!sock) {
    XLOG(ERR) << "VethPacketBackend: nl_socket_alloc failed (RTNLGRP_LINK); "
              << "link-state propagation will be silent";
    return;
  }
  // RTNLGRP_LINK is unsolicited multicast — no request/response seq pairing.
  ::nl_socket_disable_seq_check(sock);
  // Default 32k recv buf is too small if a burst of 32 veth changes arrives
  // simultaneously (each ifinfomsg is ~200B + attrs); bump to 1 MiB.
  ::nl_socket_set_buffer_size(sock, 1 << 20, 0);
  if (::nl_socket_modify_cb(
          sock, NL_CB_VALID, NL_CB_CUSTOM, handleRtnLinkMessage, this) < 0) {
    XLOG(ERR) << "VethPacketBackend: nl_socket_modify_cb failed";
    ::nl_socket_free(sock);
    return;
  }
  if (::nl_connect(sock, NETLINK_ROUTE) < 0) {
    XLOG(ERR) << "VethPacketBackend: nl_connect(NETLINK_ROUTE) failed";
    ::nl_socket_free(sock);
    return;
  }
  if (::nl_socket_add_membership(sock, RTNLGRP_LINK) < 0) {
    XLOG(ERR) << "VethPacketBackend: nl_socket_add_membership(RTNLGRP_LINK) "
              << "failed";
    ::nl_socket_free(sock);
    return;
  }
  // Non-blocking so we can observe stopThreads_ on shutdown via poll().
  if (::nl_socket_set_nonblocking(sock) < 0) {
    XLOG(WARN) << "VethPacketBackend: nl_socket_set_nonblocking failed";
  }
  int fd = ::nl_socket_get_fd(sock);
  XLOG(INFO) << "VethPacketBackend: rtnetlink RTNLGRP_LINK subscriber up "
             << "(fd=" << fd << ", tracking " << ifindexToVeth_.size()
             << " ifindexes)";

  while (!stopThreads_.load(std::memory_order_acquire)) {
    ::pollfd pfd{};
    pfd.fd = fd;
    pfd.events = POLLIN;
    int rc = ::poll(&pfd, 1, 500); // 500ms tick to observe stopThreads_.
    if (rc < 0) {
      if (errno == EINTR) {
        continue;
      }
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: rtnl poll failed: " << folly::errnoStr(errno);
      continue;
    }
    if (rc == 0 || !(pfd.revents & POLLIN)) {
      continue;
    }
    int err = ::nl_recvmsgs_default(sock);
    if (err == -NLE_NOMEM) {
      // Receive-buffer overflow dropped multicast messages, so a link
      // transition may have been missed and lastLinkUp_ may have diverged
      // from the kernel. Re-read the flags of every owned veth to reconcile.
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: rtnl receive overflow — resyncing link state";
      resyncLinkStates();
    } else if (err < 0 && err != -NLE_AGAIN && err != -NLE_INTR) {
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: nl_recvmsgs_default: " << ::nl_geterror(err);
    }
  }
  ::nl_socket_free(sock);
  XLOG(INFO) << "VethPacketBackend: rtnetlink subscriber loop exited";
}

void VethPacketBackend::resyncLinkStates() {
  for (const auto& [name, sock] : sockets_) {
    struct ifreq ifr{};
    std::strncpy(ifr.ifr_name, name.c_str(), IFNAMSIZ - 1);
    if (::ioctl(sock.fd, SIOCGIFFLAGS, &ifr) < 0) {
      XLOG_EVERY_MS(WARN, 5000) << "VethPacketBackend: SIOCGIFFLAGS failed for "
                                << name << ": " << folly::errnoStr(errno);
      continue;
    }
    // onKernelLinkEvent dedupes against lastLinkUp_, so feeding the current
    // state is a no-op for veths whose events were not dropped.
    onKernelLinkEvent(sock.ifindex, (ifr.ifr_flags & IFF_UP) != 0);
  }
}

::nl_sock* FOLLY_NULLABLE VethPacketBackend::getAdminWriteSocket() {
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
    auto it = oidToSocket_.find(oid);
    if (it == oidToSocket_.end()) {
      // Admin-state set before create_port_fn registered the mapping; the
      // FakeSaiPort code path fans to onPortCreated first in that case so we
      // shouldn't reach here without a binding. Log for safety.
      XLOG_EVERY_MS(WARN, 5000)
          << "VethPacketBackend: onAdminStateChange for unknown oid=0x"
          << std::hex << oid;
      return;
    }
    veth = it->second->name;
    ifindex = it->second->ifindex;
  }

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
    auto it = oidToSocket_.find(oid);
    if (it == oidToSocket_.end()) {
      // No binding (no create_port_fn yet). Return zeros to satisfy the
      // FBOSS port-stats reader without crashing.
      for (uint32_t i = 0; i < num_of_counters; ++i) {
        counters[i] = 0;
      }
      return SAI_STATUS_SUCCESS;
    }
    veth = it->second->name;
  }

  // The kernel only updates these when packets actually traverse the veth, so
  // they are real values, not placeholders. Read each sysfs counter lazily and
  // at most once: a caller asking for a single (or unknown) counter id must not
  // pay to open all five files. Kernel doesn't separate tx-multicast on a
  // per-veth basis (no /statistics/tx_multicast), so tx_ucast ~= tx_packets.
  std::optional<uint64_t> rxBytes, rxPkts, rxMulticast, txBytes, txPkts;
  auto lazy = [&](std::optional<uint64_t>& slot, const char* stat) -> uint64_t {
    if (!slot.has_value()) {
      slot = syscalls_->readInterfaceStat(veth, stat);
    }
    return *slot;
  };

  for (uint32_t i = 0; i < num_of_counters; ++i) {
    switch (counter_ids[i]) {
      case SAI_PORT_STAT_IF_IN_OCTETS:
        counters[i] = lazy(rxBytes, "rx_bytes");
        break;
      case SAI_PORT_STAT_IF_IN_UCAST_PKTS: {
        const uint64_t pkts = lazy(rxPkts, "rx_packets");
        const uint64_t mcast = lazy(rxMulticast, "multicast");
        counters[i] = (pkts > mcast) ? (pkts - mcast) : 0;
        break;
      }
      case SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS:
      case SAI_PORT_STAT_IF_IN_MULTICAST_PKTS:
        counters[i] = lazy(rxMulticast, "multicast");
        break;
      case SAI_PORT_STAT_IF_OUT_OCTETS:
        counters[i] = lazy(txBytes, "tx_bytes");
        break;
      case SAI_PORT_STAT_IF_OUT_UCAST_PKTS:
        counters[i] = lazy(txPkts, "tx_packets");
        break;
      default:
        counters[i] = 0;
        break;
    }
  }
  return SAI_STATUS_SUCCESS;
}

} // namespace facebook::fboss
