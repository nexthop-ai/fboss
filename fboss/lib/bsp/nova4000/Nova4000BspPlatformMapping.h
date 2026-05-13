// Copyright (c) 2025-present, Nexthop Systems, Inc.

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook::fboss {

class Nova4000BspPlatformMapping : public BspPlatformMapping {
 public:
  Nova4000BspPlatformMapping();
  explicit Nova4000BspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace facebook::fboss
