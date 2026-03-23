// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook {
namespace fboss {

class Nh4010fBspPlatformMapping : public BspPlatformMapping {
 public:
  Nh4010fBspPlatformMapping();
  explicit Nh4010fBspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace fboss
} // namespace facebook
