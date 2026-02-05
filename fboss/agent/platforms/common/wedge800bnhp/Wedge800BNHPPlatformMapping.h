/*
 *  Copyright (c) 2004-present, Facebook, Inc.
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

class Wedge800BNHPPlatformMapping : public PlatformMapping {
 public:
  Wedge800BNHPPlatformMapping();
  explicit Wedge800BNHPPlatformMapping(const std::string& platformMappingStr);
  ~Wedge800BNHPPlatformMapping() override = default;

  Wedge800BNHPPlatformMapping(Wedge800BNHPPlatformMapping const&) = delete;
  Wedge800BNHPPlatformMapping& operator=(Wedge800BNHPPlatformMapping const&) =
      delete;
  Wedge800BNHPPlatformMapping(Wedge800BNHPPlatformMapping&&) = delete;
  Wedge800BNHPPlatformMapping& operator=(Wedge800BNHPPlatformMapping&&) =
      delete;
};
} // namespace facebook::fboss
