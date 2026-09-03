// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/lib/bsp/nh5010f/Nh5010fBspPlatformMapping.h"
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include "fboss/lib/bsp/gen-cpp2/bsp_platform_mapping_types.h"

namespace facebook {
namespace fboss {

Nh5010fBspPlatformMapping::Nh5010fBspPlatformMapping()
    : BspPlatformMapping("nh5010f") {}

Nh5010fBspPlatformMapping::Nh5010fBspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(
          apache::thrift::SimpleJSONSerializer::deserialize<
              BspPlatformMappingThrift>(platformMappingStr)) {}

} // namespace fboss
} // namespace facebook
