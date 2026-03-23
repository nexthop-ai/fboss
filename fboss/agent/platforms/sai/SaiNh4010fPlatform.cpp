/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiNh4010fPlatform.h"

#include "fboss/agent/hw/switch_asics/Tomahawk5Asic.h"
#include "fboss/agent/platforms/common/nh4010f/Nh4010fPlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiNh4010fPlatform::SaiNh4010fPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<Nh4010fPlatformMapping>()
              : std::make_unique<Nh4010fPlatformMapping>(platformMappingStr),
          localMac) {}

void SaiNh4010fPlatform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Tomahawk5Asic>(switchId, switchInfo);
}

HwAsic* SaiNh4010fPlatform::getAsic() const {
  return asic_.get();
}

SaiNh4010fPlatform::~SaiNh4010fPlatform() = default;

} // namespace facebook::fboss
