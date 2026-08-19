/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/hw/sai/switch/SaiBufferManager.h"

#include "fboss/agent/hw/sai/api/SaiApiTable.h"
#include "fboss/agent/hw/sai/switch/SaiSwitch.h"
#include "fboss/agent/hw/switch_asics/Tomahawk6Asic.h"
#include "fboss/agent/hw/switch_asics/TomahawkAsic.h"
#include "fboss/agent/platforms/sai/SaiBcmPlatform.h"

#include <folly/logging/xlog.h>

namespace facebook::fboss {

uint32_t SaiBufferManager::getNumCellsAvailable(const SaiPlatform* platform) {
  auto asic = platform->getAsic();
  if (asic->getAsicType() == cfg::AsicType::ASIC_TYPE_TOMAHAWK) {
    auto saiBcmPlatform = static_cast<const SaiBcmPlatform*>(platform);
    return static_cast<const TomahawkAsic*>(asic)->getNumCellsAvailable(
        platform->getType(),
        saiBcmPlatform->getHwConfigValue(
            TomahawkAsic::optimizedMqueueGuaranteeHwConfig()) != nullptr,
        saiBcmPlatform->getHwConfigValue(
            TomahawkAsic::optimizedMmuConfigOverrideHwConfig()) != nullptr);
  } else if (
      asic->getAsicType() == cfg::AsicType::ASIC_TYPE_TOMAHAWK6 &&
      platform->getType() == PlatformType::PLATFORM_NH4220F) {
    // The shared-pool ceiling is config dependent: the SDK computes it at TM
    // init as total cells minus all per-port/PG/queue reservations, and
    // rejects any larger shared-limit write. Query it rather than assuming a
    // constant. The attribute reads the egress (THDO) default, but the SDK
    // programs the ingress (THDI) default from the same computed value —
    // measured identical on hardware — so it bounds both accounting
    // directions.
    try {
      auto saiSwitch = static_cast<SaiSwitch*>(platform->getHwSwitch());
      uint32_t availableBytes =
          SaiApiTable::getInstance()->switchApi().getAttribute(
              saiSwitch->getSaiSwitchId(),
              SaiSwitchTraits::Attributes::EgressPoolAvailableSize{});
      return availableBytes /
          static_cast<const Tomahawk6Asic*>(asic)->getMMUCellSize();
    } catch (const std::exception& e) {
      XLOG(WARN) << "Failed to query egress pool available size, falling "
                 << "back to per-platform cell count: " << e.what();
    }
  }
  return asic->getNumCellsAvailable(platform->getType());
}

void SaiBufferManager::loadCpuPortEgressBufferPool() {}
} // namespace facebook::fboss
