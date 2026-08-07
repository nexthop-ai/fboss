/*
 *  Copyright (c) 2026, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#include "fboss/agent/hw/sai/fake/FakeSaiPacketBackend.h"

#include <folly/logging/xlog.h>

#include <mutex>

namespace facebook::fboss {

namespace {

// Preserves the behavior FakeSai had before the backend interface was
// introduced: TX is a no-op, RX never fires. Existing FakeSai unit tests
// must continue to pass against this default.
class NoopFakeSaiPacketBackend : public FakeSaiPacketBackend {
 public:
  sai_status_t tx(
      sai_object_id_t /*tx_port*/,
      sai_size_t /*buffer_size*/,
      const void* /*buffer*/) override {
    return SAI_STATUS_SUCCESS;
  }
  void setRxCallback(
      sai_object_id_t /*switch_id*/,
      sai_packet_event_notification_fn /*cb*/) override {}
};

std::mutex& registryMutex() {
  static std::mutex m;
  return m;
}

std::shared_ptr<FakeSaiPacketBackend>& backendSlot() {
  static std::shared_ptr<FakeSaiPacketBackend> backend =
      std::make_shared<NoopFakeSaiPacketBackend>();
  return backend;
}

} // namespace

std::shared_ptr<FakeSaiPacketBackend> FakeSaiPacketBackendRegistry::get() {
  std::lock_guard<std::mutex> g(registryMutex());
  return backendSlot();
}

void FakeSaiPacketBackendRegistry::install(
    std::unique_ptr<FakeSaiPacketBackend> backend) {
  if (!backend) {
    XLOG(ERR) << "FakeSaiPacketBackendRegistry::install: refusing null backend";
    return;
  }
  std::lock_guard<std::mutex> g(registryMutex());
  XLOG(INFO) << "FakeSaiPacketBackendRegistry: replacing active backend";
  backendSlot() = std::move(backend);
}

} // namespace facebook::fboss
