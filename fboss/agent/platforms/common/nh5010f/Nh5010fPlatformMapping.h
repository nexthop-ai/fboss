/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
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

class Nh5010fPlatformMapping : public PlatformMapping {
 public:
  Nh5010fPlatformMapping();
  explicit Nh5010fPlatformMapping(const std::string& platformMappingStr);

 private:
  // Forbidden copy constructor and assignment operator
  Nh5010fPlatformMapping(Nh5010fPlatformMapping const&) = delete;
  Nh5010fPlatformMapping& operator=(Nh5010fPlatformMapping const&) = delete;
};
} // namespace facebook::fboss
