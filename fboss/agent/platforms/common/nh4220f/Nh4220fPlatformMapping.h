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

class Nh4220fPlatformMapping : public PlatformMapping {
 public:
  Nh4220fPlatformMapping();
  explicit Nh4220fPlatformMapping(const std::string& platformMappingStr);
  ~Nh4220fPlatformMapping() override = default;

  Nh4220fPlatformMapping(Nh4220fPlatformMapping const&) = delete;
  Nh4220fPlatformMapping& operator=(Nh4220fPlatformMapping const&) = delete;
  Nh4220fPlatformMapping(Nh4220fPlatformMapping&&) = delete;
  Nh4220fPlatformMapping& operator=(Nh4220fPlatformMapping&&) = delete;
};
} // namespace facebook::fboss
