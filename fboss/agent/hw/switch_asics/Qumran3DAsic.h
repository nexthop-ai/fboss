// Copyright 2004-present Facebook. All Rights Reserved.

#pragma once

#include <optional>
#include <utility>
#include "fboss/agent/hw/switch_asics/Jericho3Asic.h"

namespace facebook::fboss {

class Qumran3DAsic : public Jericho3Asic {
 public:
  Qumran3DAsic(
      std::optional<int64_t> switchId,
      cfg::SwitchInfo switchInfo,
      std::optional<cfg::SdkVersion> sdkVersion = std::nullopt)
      : Jericho3Asic(switchId, std::move(switchInfo), std::move(sdkVersion)) {}

  bool isSupported(Feature) const override;

  cfg::AsicType getAsicType() const override {
    return cfg::AsicType::ASIC_TYPE_QUMRAN3D;
  }

  uint32_t getNumCores() const override {
    return 8;
  }

  uint32_t getNumDies() const override {
    return 2;
  }

  std::vector<InternalSystemPortConfig> getInternalSystemPortConfig(
      const CpuPortCoreAndPortIndex& cpuPortsCoreAndPortIdx) const override;
};

} // namespace facebook::fboss
