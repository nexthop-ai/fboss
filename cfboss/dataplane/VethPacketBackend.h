/*
 *  Copyright (c) 2026, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#pragma once

#include "fboss/agent/hw/sai/fake/FakeSaiPacketBackend.h"

#include <folly/CppAttributes.h>

#include <atomic>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

struct nl_sock;

namespace facebook::fboss::cfboss {
class PortMap;
}

namespace facebook::fboss {

// Injectable seam over the two host-facing syscall surfaces the veth backend
// depends on: opening an AF_PACKET socket bound to a veth (needs CAP_NET_RAW)
// and reading a per-interface counter from sysfs. The production seam performs
// the real syscalls; unit tests substitute a fake so the concurrent RX and
// stats paths can run without privilege or real interfaces.
class VethSyscalls {
 public:
  virtual ~VethSyscalls() = default;

  // Open a packet socket bound to `ifname`, returning {fd, ifindex}. Throws
  // std::runtime_error on failure (any partial fd is closed before throwing).
  virtual std::pair<int, int> openPacketSocket(const std::string& ifname) = 0;

  // Read /sys/class/net/<veth>/statistics/<stat>; 0 on any failure.
  virtual uint64_t readInterfaceStat(
      const std::string& veth,
      const std::string& stat) = 0;
};

// The production seam: real socket()/ioctl()/bind() and sysfs reads.
std::shared_ptr<VethSyscalls> makeDefaultVethSyscalls();

/**
 * FakeSai packet backend that moves real packets across kernel veth
 * interfaces (named fboss_p<N>) using AF_PACKET sockets.
 *
 * Lifecycle:
 *   1. Construct with a loaded PortMap. The backend opens AF_PACKET sockets
 *      for every veth in the map and spawns one RX thread per socket.
 *   2. install() into FakeSaiPacketBackendRegistry before SAI init.
 *   3. FakeSai's create_port_fn calls onPortCreated(oid, lanes); we record
 *      both oid -> veth and veth -> oid mappings.
 *   4. TX: FakeSai's send_hostif_fn calls tx(oid, ...); we write to the
 *      corresponding veth's AF_PACKET socket.
 *   5. RX: each per-veth thread polls its socket, skips PACKET_OUTGOING
 *      (our own TX echoes), looks up the port OID for the ingress veth,
 *      builds an attribute list with SAI_HOSTIF_PACKET_ATTR_INGRESS_PORT,
 *      and invokes the registered sai_packet_event_notification_fn.
 */
class VethPacketBackend : public FakeSaiPacketBackend {
 public:
  // `syscalls` is the host-syscall seam; defaults to the real implementation.
  // Tests inject a fake to hand out pollable stand-in fds and canned counters.
  explicit VethPacketBackend(
      std::shared_ptr<const cfboss::PortMap> portMap,
      std::shared_ptr<VethSyscalls> syscalls = makeDefaultVethSyscalls());
  ~VethPacketBackend() override;

  sai_status_t tx(
      sai_object_id_t tx_port,
      sai_size_t buffer_size,
      const void* buffer) override;

  void setRxCallback(
      sai_object_id_t switch_id,
      sai_packet_event_notification_fn cb) override;

  void setPortStateCallback(sai_port_state_change_notification_fn cb) override;

  void onPortCreated(sai_object_id_t oid, const std::vector<uint32_t>& lanes)
      override;
  void onPortRemoved(sai_object_id_t oid) override;

  // FBOSS -> kernel link state. When FBOSS toggles SAI_PORT_ATTR_ADMIN_STATE,
  // we set/clear IFF_UP on the corresponding veth via RTM_NEWLINK so a
  // 'fboss2 set port ... --admin-state DOWN' actually drops the kernel link.
  void onAdminStateChange(sai_object_id_t oid, bool isAdminUp) override;

  // FBOSS port stats. Reads /sys/class/net/<veth>/statistics/{rx,tx}_{bytes,
  // packets} plus multicast, and maps to SAI_PORT_STAT_IF_IN_OCTETS,
  // IF_IN_UCAST_PKTS (rx_packets - multicast), IF_IN_{NON_UCAST,MULTICAST}_PKTS
  // (multicast), IF_OUT_OCTETS, and IF_OUT_UCAST_PKTS. Other SAI counter IDs
  // return 0 (the kernel does not surface them per veth).
  sai_status_t getPortStats(
      sai_object_id_t oid,
      uint32_t num_of_counters,
      const sai_stat_id_t* counter_ids,
      uint64_t* counters) override;

  // Called from the rtnetlink subscription callback (a free function in an
  // anonymous namespace) when an RTM_NEWLINK / RTM_DELLINK arrives. Maps
  // ifindex -> veth via ifindexToVeth_, then fires the SAI port-state
  // callback if the up/down state actually changed. Public because the
  // free-function callback cannot access private members.
  void onKernelLinkEvent(int ifindex, bool isUp);

 private:
  // Owns an AF_PACKET fd with an RAII destructor, so a throwing constructor
  // closes every already opened fd via ~VethSocket rather than leaking it
  // (the backend dtor never runs on a failed ctor); threads started before
  // the throw are joined by the constructor's catch block before members are
  // destroyed. Non-copyable and non-movable: constructed in place in
  // sockets_ and never relocated, so RX threads' raw pointers stay valid.
  // The dtor is defined out-of-line in the .cpp so <unistd.h> need not leak
  // into this header.
  struct VethSocket {
    VethSocket() = default;
    VethSocket(int fd, int ifindex, std::string name);
    ~VethSocket();
    VethSocket(const VethSocket&) = delete;
    VethSocket& operator=(const VethSocket&) = delete;
    VethSocket(VethSocket&&) = delete;
    VethSocket& operator=(VethSocket&&) = delete;

    int fd{-1};
    int ifindex{0};
    std::string name;
    // SAI port OID bound to this veth, or 0 when no port is bound (the veth
    // exists from construction; its port is created later and may be
    // removed). Mutable + atomic so the RX loop reads it lock-free per
    // packet while onPortCreated/onPortRemoved write it under mutex_.
    mutable std::atomic<sai_object_id_t> oid_{0};
  };

  void rxLoop(const VethSocket* sock);
  const VethSocket* FOLLY_NULLABLE socketForVeth(const std::string& veth) const;

  std::shared_ptr<const cfboss::PortMap> portMap_;

  // Host-syscall seam (socket open + sysfs stat reads). Injected for tests.
  std::shared_ptr<VethSyscalls> syscalls_;

  // veth name -> socket. The map is built at construction and never changes
  // structurally, so RX threads hold raw pointers into it without locking;
  // only each socket's atomic oid_ is mutated at runtime.
  std::map<std::string, VethSocket> sockets_;

  // Guards the runtime maps + the registered callbacks.
  mutable std::mutex mutex_;

  // FBOSS's RxPktEventQueueType is a SingleProducer folly::coro::BoundedQueue
  // whose dequeueReady CHECKs that invariant; invoking the SAI client's
  // packet callback from multiple per-veth RX threads concurrently violates
  // it. Serialize delivery through this mutex, cache-line separated from
  // mutex_ so the hot delivery lock does not false-share with the
  // config-side lock.
  alignas(64) std::mutex rxDeliveryMutex_;

  // SAI port OID -> its veth socket, so TX / admin-state / stats resolve the
  // socket directly rather than going OID -> veth-name -> socket. Guarded by
  // mutex_; pointers are stable because sockets_ never relocates. The reverse
  // direction is VethSocket::oid_, cached on each socket.
  std::map<sai_object_id_t, const VethSocket*> oidToSocket_;
  sai_object_id_t rxSwitchId_{0};
  sai_packet_event_notification_fn rxCallback_{nullptr};
  sai_port_state_change_notification_fn portStateCallback_{nullptr};

  // Fires PORT_OPER_STATUS_{UP,DOWN} for `oid` via `cb`. MUST be called with
  // mutex_ released: `cb` is an external SAI notification callback and firing
  // it under the non-recursive mutex_ is a re-entrancy/deadlock hazard.
  // Callers snapshot the callback pointer + target oid under the lock, drop
  // the lock, then invoke this (mirrors how rxLoop copies rxCallback_ under
  // the lock and delivers outside it). Unlike RX delivery, port-state
  // delivery needs no serialization mutex: LinkChangeEventQueueType is
  // multi-producer, unlike the single-producer Rx queue that
  // rxDeliveryMutex_ guards.
  void notifyPortStateUnlocked(
      sai_port_state_change_notification_fn cb,
      sai_object_id_t oid,
      bool isUp);

  // Background thread subscribed to rtnetlink RTNLGRP_LINK group. Receives
  // RTM_NEWLINK / RTM_DELLINK messages on actual kernel link transitions and
  // dispatches PORT_OPER_STATUS_DOWN/UP from ifi_flags & IFF_UP (the kernel
  // administrative link state) without polling.
  void linkStateSubscribeLoop();

  // Re-read every owned veth's current IFF_UP flag via SIOCGIFFLAGS and feed
  // it through onKernelLinkEvent (which suppresses non-transitions). Called
  // after an rtnl receive overflow (NLE_NOMEM), when a link event may have
  // been dropped and lastLinkUp_ may have diverged from the kernel.
  void resyncLinkStates();

  // Helper used by onAdminStateChange: open/cache the write-side netlink
  // socket used to issue RTM_NEWLINK with IFF_UP/down. Returns nullptr on
  // failure (admin-state writes silently fail rather than crash).
  ::nl_sock* FOLLY_NULLABLE getAdminWriteSocket();

  std::atomic<bool> stopThreads_{false};
  std::vector<std::thread> rxThreads_;
  std::thread linkStateSubThread_;

  // Cached netlink socket for issuing admin-state writes (RTM_NEWLINK with
  // IFF_UP set/cleared). Lazily opened on first call to onAdminStateChange.
  // Guarded by adminSockMutex_ because onAdminStateChange may be invoked
  // from multiple threads.
  std::mutex adminSockMutex_;
  ::nl_sock* adminWriteSock_{nullptr};

  // veth name -> last seen up/down state, used by the netlink subscription
  // loop to suppress duplicate notifications. Guarded by mutex_.
  std::map<std::string, bool> lastLinkUp_;

  // ifindex -> veth name, populated from sockets_ at construction time.
  // Used by the netlink subscription loop to map RTM_NEWLINK ifindex back
  // to the cfboss-owned veth set. Immutable after construction; no lock.
  std::map<int, std::string> ifindexToVeth_;
};

} // namespace facebook::fboss
