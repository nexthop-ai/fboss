/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiBcmWedge800BNHPPlatform.h"

#include "fboss/agent/hw/switch_asics/Tomahawk5Asic.h"
#include "fboss/agent/platforms/common/wedge800bnhp/Wedge800BNHPPlatformMapping.h"

#include <cstring>
namespace facebook::fboss {

SaiBcmWedge800BNHPPlatform::SaiBcmWedge800BNHPPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr)
    : SaiBcmPlatform(
          std::move(productInfo),
          platformMappingStr.empty()
              ? std::make_unique<Wedge800BNHPPlatformMapping>()
              : std::make_unique<Wedge800BNHPPlatformMapping>(
                    platformMappingStr),
          localMac) {}

void SaiBcmWedge800BNHPPlatform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  CHECK(!fabricNodeRole.has_value());
  asic_ = std::make_unique<Tomahawk5Asic>(switchId, switchInfo);
}

HwAsic* SaiBcmWedge800BNHPPlatform::getAsic() const {
  return asic_.get();
}

SaiBcmWedge800BNHPPlatform::~SaiBcmWedge800BNHPPlatform() = default;

} // namespace facebook::fboss
