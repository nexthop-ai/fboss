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

#include <atomic>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

struct nl_sock;

namespace facebook::fboss::cfboss {
class PortMap;
}

namespace facebook::fboss {

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
  explicit VethPacketBackend(std::shared_ptr<const cfboss::PortMap> portMap);
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

 private:
  struct VethSocket {
    int fd{-1};
    int ifindex{0};
    std::string name;
  };

  void rxLoop(const VethSocket* sock);
  const VethSocket* socketForVeth(const std::string& veth) const;

  std::shared_ptr<const cfboss::PortMap> portMap_;

  // veth name -> socket. Built at construction; immutable thereafter so
  // RX threads can hold raw pointers into it without locking.
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

  std::map<sai_object_id_t, std::string> oidToVeth_;
  std::map<std::string, sai_object_id_t> vethToOid_;
  sai_object_id_t rxSwitchId_{0};
  sai_packet_event_notification_fn rxCallback_{nullptr};
  sai_port_state_change_notification_fn portStateCallback_{nullptr};

  // Fires PORT_OPER_STATUS_UP for `oid` if portStateCallback_ is set.
  // Called with mutex_ held.
  void notifyPortUpLocked(sai_object_id_t oid);

  // Helper used by onAdminStateChange: open/cache the write-side netlink
  // socket used to issue RTM_NEWLINK with IFF_UP/down. Returns nullptr on
  // failure (admin-state writes silently fail rather than crash).
  ::nl_sock* getAdminWriteSocket();

  std::atomic<bool> stopThreads_{false};
  std::vector<std::thread> rxThreads_;

  // Cached netlink socket for issuing admin-state writes (RTM_NEWLINK with
  // IFF_UP set/cleared). Lazily opened on first call to onAdminStateChange.
  // Guarded by adminSockMutex_ because onAdminStateChange may be invoked
  // from multiple threads.
  std::mutex adminSockMutex_;
  ::nl_sock* adminWriteSock_{nullptr};
};

} // namespace facebook::fboss
