/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */

#include "fboss/agent/platforms/sai/SaiBcmM4062nhpPlatform.h"

#include "fboss/agent/hw/switch_asics/Tomahawk6Asic.h"
#include "fboss/agent/platforms/common/m4062nhp/M4062nhpPlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiBcmM4062nhpPlatform::SaiBcmM4062nhpPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<M4062nhpPlatformMapping>()
              : std::make_unique<M4062nhpPlatformMapping>(platformMappingStr),
          localMac) {}

void SaiBcmM4062nhpPlatform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Tomahawk6Asic>(switchId, switchInfo);
}

HwAsic* SaiBcmM4062nhpPlatform::getAsic() const {
  return asic_.get();
}

SaiBcmM4062nhpPlatform::~SaiBcmM4062nhpPlatform() = default;

} // namespace facebook::fboss
