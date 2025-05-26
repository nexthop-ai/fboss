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

class Nh4010PlatformMapping : public PlatformMapping {
 public:
  Nh4010PlatformMapping();
  explicit Nh4010PlatformMapping(const std::string& platformMappingStr);

 private:
  // Forbidden copy constructor and assignment operator
  Nh4010PlatformMapping(Nh4010PlatformMapping const&) = delete;
  Nh4010PlatformMapping& operator=(Nh4010PlatformMapping const&) = delete;
};
} // namespace facebook::fboss
