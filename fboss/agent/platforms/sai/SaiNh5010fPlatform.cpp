/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiNh5010fPlatform.h"

#include "fboss/agent/hw/switch_asics/Qumran3DAsic.h"
#include "fboss/agent/platforms/common/nh5010f/Nh5010fPlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiNh5010fPlatform::SaiNh5010fPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<Nh5010fPlatformMapping>()
              : std::make_unique<Nh5010fPlatformMapping>(platformMappingStr),
          localMac) {}

void SaiNh5010fPlatform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Qumran3DAsic>(switchId, switchInfo);
}

HwAsic* SaiNh5010fPlatform::getAsic() const {
  return asic_.get();
}

SaiNh5010fPlatform::~SaiNh5010fPlatform() = default;

} // namespace facebook::fboss
