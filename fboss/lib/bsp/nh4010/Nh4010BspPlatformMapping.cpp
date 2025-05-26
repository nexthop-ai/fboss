// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/lib/bsp/nh4010/Nh4010BspPlatformMapping.h"
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include "fboss/lib/bsp/BspPlatformMapping.h"
#include "fboss/lib/bsp/gen-cpp2/bsp_platform_mapping_types.h"

using namespace facebook::fboss;
using namespace apache::thrift;

namespace {
constexpr auto kJsonBspPlatformMappingStr = R"(
{
)";

static BspPlatformMappingThrift buildNh4010PlatformMapping(
    const std::string& platformMappingStr) {
  return apache::thrift::SimpleJSONSerializer::deserialize<
      BspPlatformMappingThrift>(platformMappingStr);
}

} // namespace

namespace facebook {
namespace fboss {

Nh4010BspPlatformMapping::Nh4010BspPlatformMapping()
    : BspPlatformMapping(
          buildNh4010PlatformMapping(kJsonBspPlatformMappingStr)) {}

Nh4010BspPlatformMapping::Nh4010BspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(buildNh4010PlatformMapping(platformMappingStr)) {}

} // namespace fboss
} // namespace facebook
