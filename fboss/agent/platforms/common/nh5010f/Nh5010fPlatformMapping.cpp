/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/common/nh5010f/Nh5010fPlatformMapping.h"

namespace {
// TODO: Populate with the generated platform mapping for NH-5010-F
constexpr auto kJsonPlatformMappingStr = R"(
{
  "ports": {},
  "chips": [],
  "platformSupportedProfiles": []
}
)";
} // namespace

namespace facebook::fboss {
Nh5010fPlatformMapping::Nh5010fPlatformMapping()
    : PlatformMapping(kJsonPlatformMappingStr) {}

Nh5010fPlatformMapping::Nh5010fPlatformMapping(
    const std::string& platformMappingStr)
    : PlatformMapping(platformMappingStr) {}

} // namespace facebook::fboss
