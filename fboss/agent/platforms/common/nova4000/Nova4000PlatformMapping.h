/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
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
