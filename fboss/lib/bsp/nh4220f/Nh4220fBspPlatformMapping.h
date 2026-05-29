// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook::fboss {

class Nh4220fBspPlatformMapping : public BspPlatformMapping {
 public:
  Nh4220fBspPlatformMapping();
  explicit Nh4220fBspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace facebook::fboss
