// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook {
namespace fboss {

class Nh5010fBspPlatformMapping : public BspPlatformMapping {
 public:
  Nh5010fBspPlatformMapping();
  explicit Nh5010fBspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace fboss
} // namespace facebook
