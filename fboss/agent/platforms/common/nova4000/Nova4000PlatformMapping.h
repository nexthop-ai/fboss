/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#pragma once

#include "fboss/agent/platforms/common/PlatformMapping.h"

namespace facebook::fboss {

class Nova4000PlatformMapping : public PlatformMapping {
 public:
  Nova4000PlatformMapping();
  explicit Nova4000PlatformMapping(const std::string& platformMappingStr);
  ~Nova4000PlatformMapping() override = default;

  Nova4000PlatformMapping(Nova4000PlatformMapping const&) = delete;
  Nova4000PlatformMapping& operator=(Nova4000PlatformMapping const&) = delete;
  Nova4000PlatformMapping(Nova4000PlatformMapping&&) = delete;
  Nova4000PlatformMapping& operator=(Nova4000PlatformMapping&&) = delete;
};
} // namespace facebook::fboss
