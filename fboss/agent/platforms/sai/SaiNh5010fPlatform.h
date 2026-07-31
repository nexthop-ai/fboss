/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#pragma once

#include "fboss/agent/platforms/sai/SaiBcmPlatform.h"

namespace facebook::fboss {

// NH-5010-F uses the Broadcom Qumran3D ASIC (bcm88872).
class Qumran3DAsic;

class SaiNh5010fPlatform : public SaiBcmPlatform {
 public:
  SaiNh5010fPlatform(
      std::unique_ptr<PlatformProductInfo> productInfo,
      folly::MacAddress localMac,
      const std::string& platformMappingStr);
  ~SaiNh5010fPlatform() override;
  HwAsic* getAsic() const override;
  bool isSerdesApiSupported() const override {
    return true;
  }

  void initLEDs() override {}

 private:
  void setupAsic(
      std::optional<int64_t> switchId,
      const cfg::SwitchInfo& switchInfo,
      std::optional<HwAsic::FabricNodeRole> fabricNodeRole) override;
  std::unique_ptr<Qumran3DAsic> asic_;
};

} // namespace facebook::fboss
