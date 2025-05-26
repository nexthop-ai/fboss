// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook {
namespace fboss {

class Nh4010BspPlatformMapping : public BspPlatformMapping {
 public:
  Nh4010BspPlatformMapping();
  explicit Nh4010BspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace fboss
} // namespace facebook
