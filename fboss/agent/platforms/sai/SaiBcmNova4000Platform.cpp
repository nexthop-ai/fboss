/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiBcmNova4000Platform.h"

#include "fboss/agent/hw/switch_asics/Tomahawk6Asic.h"
#include "fboss/agent/platforms/common/nova4000/Nova4000PlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiBcmNova4000Platform::SaiBcmNova4000Platform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<Nova4000PlatformMapping>()
              : std::make_unique<Nova4000PlatformMapping>(platformMappingStr),
          localMac) {}

void SaiBcmNova4000Platform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Tomahawk6Asic>(switchId, switchInfo);
}

HwAsic* SaiBcmNova4000Platform::getAsic() const {
  return asic_.get();
}

SaiBcmNova4000Platform::~SaiBcmNova4000Platform() = default;

} // namespace facebook::fboss
