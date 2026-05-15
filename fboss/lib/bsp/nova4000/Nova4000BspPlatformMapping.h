/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */

#pragma once

#include "fboss/lib/bsp/BspPlatformMapping.h"

namespace facebook::fboss {

class Nova4000BspPlatformMapping : public BspPlatformMapping {
 public:
  Nova4000BspPlatformMapping();
  explicit Nova4000BspPlatformMapping(const std::string& platformMappingStr);
};

} // namespace facebook::fboss
