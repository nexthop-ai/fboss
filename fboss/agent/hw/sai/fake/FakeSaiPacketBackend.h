/*
 *  Copyright (c) 2026, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#pragma once

#include <cstdint>
#include <memory>
#include <vector>

extern "C" {
#include <sai.h> // NOLINT(misc-include-cleaner)
}

namespace facebook::fboss {

// Pluggable backend for Fake SAI hostif TX/RX and port-state events. FakeSai
// delegates through the installed backend: the default noop backend preserves
// the pre-existing "TX is a no-op, RX never fires" behavior that unit tests
// rely on, and an independently linked library may install a concrete
// implementation via the registry to provide real packet I/O.
//
// The interface defaults the non-TX/RX methods to no-ops so minimal
// backends only need to implement the two required methods.
class FakeSaiPacketBackend {
 public:
  virtual ~FakeSaiPacketBackend() = default;

  // Called by FakeSai's send_hostif_fn for each TX packet.
  virtual sai_status_t
  tx(sai_object_id_t tx_port, sai_size_t buffer_size, const void* buffer) = 0;

  // FakeSai's set_switch_attribute_fn delivers the SAI client's packet
  // event callback here. The backend is responsible for invoking it on RX.
  virtual void setRxCallback(
      sai_object_id_t switch_id,
      sai_packet_event_notification_fn cb) = 0;

  // FakeSai's set_switch_attribute_fn delivers the SAI client's port-state
  // change callback here. The backend fires UP/DOWN notifications based on
  // some external link-state signal. Default no-op.
  virtual void setPortStateCallback(
      sai_port_state_change_notification_fn /*cb*/) {}

  // FakeSai notifies the backend when a SAI port is created or removed so
  // it can maintain a lane (first lane) -> oid mapping. May be invoked more
  // than once for the same port (cold-boot create + admin-up, warm-boot
  // rebind); implementations must be idempotent. Default no-op.
  virtual void onPortCreated(
      sai_object_id_t /*oid*/,
      const std::vector<uint32_t>& /*lanes*/) {}
  virtual void onPortRemoved(sai_object_id_t /*oid*/) {}

  // Fired when the SAI client sets SAI_PORT_ATTR_ADMIN_STATE on a port.
  // Backends that own a kernel interface can mirror the state. Default no-op.
  virtual void onAdminStateChange(sai_object_id_t /*oid*/, bool /*isAdminUp*/) {
  }

  // Fake-SAI port stats are delegated here. Default fills `counters` with 0,
  // preserving the historical placeholder behavior every existing FakeSai
  // test relies on. Backends with real underlying I/O override to surface
  // actual counter values.
  virtual sai_status_t getPortStats(
      sai_object_id_t /*oid*/,
      uint32_t num_of_counters,
      const sai_stat_id_t* /*counter_ids*/,
      uint64_t* counters) {
    for (uint32_t i = 0; i < num_of_counters; ++i) {
      counters[i] = 0;
    }
    return SAI_STATUS_SUCCESS;
  }
};

// Process-wide registry holding the active FakeSaiPacketBackend.
// Defaults to a no-op backend until install() is called. get() returns a
// shared_ptr copy taken under the registry lock, so a caller's backend stays
// alive across use even if install() concurrently replaces the active one.
class FakeSaiPacketBackendRegistry {
 public:
  static std::shared_ptr<FakeSaiPacketBackend> get();
  static void install(std::unique_ptr<FakeSaiPacketBackend> backend);
};

} // namespace facebook::fboss
