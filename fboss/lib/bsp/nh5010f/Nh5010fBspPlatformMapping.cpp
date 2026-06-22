// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/lib/bsp/nh5010f/Nh5010fBspPlatformMapping.h"
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include "fboss/lib/bsp/BspPlatformMapping.h"
#include "fboss/lib/bsp/gen-cpp2/bsp_platform_mapping_types.h"

using namespace facebook::fboss;
using namespace apache::thrift;

namespace {
// TODO: Populate with the real BSP platform mapping for NH-5010-F
constexpr auto kJsonBspPlatformMappingStr = R"(
{
  "pimMapping": {}
}
)";

static BspPlatformMappingThrift buildNh5010fPlatformMapping(
    const std::string& platformMappingStr) {
  return apache::thrift::SimpleJSONSerializer::deserialize<
      BspPlatformMappingThrift>(platformMappingStr);
}

} // namespace

namespace facebook {
namespace fboss {

Nh5010fBspPlatformMapping::Nh5010fBspPlatformMapping()
    : BspPlatformMapping(
          buildNh5010fPlatformMapping(kJsonBspPlatformMappingStr)) {}

Nh5010fBspPlatformMapping::Nh5010fBspPlatformMapping(
    const std::string& platformMappingStr)
    : BspPlatformMapping(buildNh5010fPlatformMapping(platformMappingStr)) {}

} // namespace fboss
} // namespace facebook
