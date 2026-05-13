/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#pragma once

#include "fboss/agent/platforms/sai/SaiBcmPlatformPort.h"

namespace facebook::fboss {

class SaiBcmNova4000PlatformPort : public SaiBcmPlatformPort {
 public:
  SaiBcmNova4000PlatformPort(PortID id, SaiPlatform* platform)
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
