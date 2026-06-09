/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#pragma once

#include "fboss/agent/platforms/sai/SaiBcmPlatformPort.h"

namespace facebook::fboss {

class SaiBcmM4062nhpPlatformPort : public SaiBcmPlatformPort {
 public:
  SaiBcmM4062nhpPlatformPort(PortID id, SaiPlatform* platform)
      : SaiBcmPlatformPort(id, platform) {}
  void linkStatusChanged(bool up, bool adminUp) override;
  void externalState(PortLedExternalState lfs) override;
  uint32_t getPhysicalLaneId(uint32_t chipId, uint32_t logicalLane)
      const override {
    if (getPortType() == cfg::PortType::MANAGEMENT_PORT) {
      // TH6 management-port lane numbering starts at 514 rather than the
      // logical-lane base, so shift by 1 to match the SDK's view.
      return SaiBcmPlatformPort::getPhysicalLaneId(chipId, logicalLane) + 1;
    }
    return SaiBcmPlatformPort::getPhysicalLaneId(chipId, logicalLane);
  }
};

} // namespace facebook::fboss
