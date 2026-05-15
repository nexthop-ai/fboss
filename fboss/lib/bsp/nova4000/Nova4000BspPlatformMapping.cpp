/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */

#include "fboss/lib/bsp/nova4000/Nova4000BspPlatformMapping.h"

#include <thrift/lib/cpp2/protocol/Serializer.h>

namespace facebook::fboss {

Nova4000BspPlatformMapping::Nova4000BspPlatformMapping()
    : BspPlatformMapping("nova4000") {}

Nova4000BspPlatformMapping::Nova4000BspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(
          apache::thrift::SimpleJSONSerializer::deserialize<
              BspPlatformMappingThrift>(platformMappingStr)) {}

} // namespace facebook::fboss
