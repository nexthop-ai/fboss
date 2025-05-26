/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiNh4010Platform.h"

#include "fboss/agent/hw/switch_asics/Tomahawk5Asic.h"
#include "fboss/agent/platforms/common/nh4010/Nh4010PlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiNh4010Platform::SaiNh4010Platform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<Nh4010PlatformMapping>()
              : std::make_unique<Nh4010PlatformMapping>(platformMappingStr),
          localMac) {}

void SaiNh4010Platform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Tomahawk5Asic>(switchId, switchInfo);
}

HwAsic* SaiNh4010Platform::getAsic() const {
  return asic_.get();
}

SaiNh4010Platform::~SaiNh4010Platform() = default;

} // namespace facebook::fboss
