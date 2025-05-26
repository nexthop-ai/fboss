/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/common/nh4010/Nh4010PlatformMapping.h"

namespace {
constexpr auto kJsonPlatformMappingStr = R"(
{
)";
} // namespace

namespace facebook::fboss {
Nh4010PlatformMapping::Nh4010PlatformMapping()
    : PlatformMapping(kJsonPlatformMappingStr) {}

Nh4010PlatformMapping::Nh4010PlatformMapping(
    const std::string& platformMappingStr)
    : PlatformMapping(platformMappingStr) {}

} // namespace facebook::fboss
