// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook::fboss {

class Wedge800BNHPBspPlatformMapping : public BspPlatformMapping {
 public:
  Wedge800BNHPBspPlatformMapping();
  explicit Wedge800BNHPBspPlatformMapping(
      const std::string& platformMappingStr);
};

} // namespace facebook::fboss
