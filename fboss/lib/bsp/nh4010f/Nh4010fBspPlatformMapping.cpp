// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/lib/bsp/nh4010f/Nh4010fBspPlatformMapping.h"

#include <thrift/lib/cpp2/protocol/Serializer.h>

namespace facebook::fboss {

Nh4010fBspPlatformMapping::Nh4010fBspPlatformMapping()
    : BspPlatformMapping("nh4010f") {}

Nh4010fBspPlatformMapping::Nh4010fBspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(
          apache::thrift::SimpleJSONSerializer::deserialize<
              BspPlatformMappingThrift>(platformMappingStr)) {}

} // namespace facebook::fboss
