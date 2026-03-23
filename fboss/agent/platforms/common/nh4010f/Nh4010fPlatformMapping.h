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

class Nh4010fPlatformMapping : public PlatformMapping {
 public:
  Nh4010fPlatformMapping();
  explicit Nh4010fPlatformMapping(const std::string& platformMappingStr);

 private:
  // Forbidden copy constructor and assignment operator
  Nh4010fPlatformMapping(Nh4010fPlatformMapping const&) = delete;
  Nh4010fPlatformMapping& operator=(Nh4010fPlatformMapping const&) = delete;
};
} // namespace facebook::fboss
