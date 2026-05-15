/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#pragma once

#include "fboss/agent/platforms/sai/SaiBcmPlatform.h"

namespace facebook::fboss {

class Tomahawk6Asic;

class SaiBcmNova4000Platform : public SaiBcmPlatform {
 public:
  SaiBcmNova4000Platform(
      std::unique_ptr<PlatformProductInfo> productInfo,
      folly::MacAddress localMac,
      const std::string& platformMappingStr);
  ~SaiBcmNova4000Platform() override;
  HwAsic* getAsic() const override;
  uint32_t numLanesPerCore() const override {
    return 8;
  }

  uint32_t numCellsAvailable() const override {
    return 616994;
  }

  bool isSerdesApiSupported() const override {
    return true;
  }

  void initLEDs() override {}

 private:
  void setupAsic(
      std::optional<int64_t> switchId,
      const cfg::SwitchInfo& switchInfo,
      std::optional<HwAsic::FabricNodeRole> fabricNodeRole) override;
  std::unique_ptr<Tomahawk6Asic> asic_;
};

} // namespace facebook::fboss
