/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/acl/table_group/CmdConfigAclTableGroup.h"

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/commands/config/acl/AclConfigUtils.h"

#include <fmt/format.h>
#include <algorithm>
#include <cctype>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "thrift/lib/cpp/util/EnumUtils.h"

namespace facebook::fboss {

namespace {
constexpr std::string_view kAclTableGroupAttrStage = "stage";

constexpr std::string_view kAclStageIngress = "ingress";
constexpr std::string_view kAclStageIngressMacsec = "ingress-macsec";
constexpr std::string_view kAclStageEgressMacsec = "egress-macsec";
constexpr std::string_view kAclStageIngressPostLookup = "ingress-post-lookup";

const std::unordered_map<std::string_view, cfg::AclStage> kAclStageByName = {
    {kAclStageIngress, cfg::AclStage::INGRESS},
    {kAclStageIngressMacsec, cfg::AclStage::INGRESS_MACSEC},
    {kAclStageEgressMacsec, cfg::AclStage::EGRESS_MACSEC},
    {kAclStageIngressPostLookup, cfg::AclStage::INGRESS_POST_LOOKUP},
};

// Stage names only (case-insensitive). A bare 0-3 would be accepted by the
// thrift enum but says nothing at the call site about which stage it selects,
// so the names are the only spelling.
cfg::AclStage parseAclStage(const std::string& s) {
  std::string lower = s;
  std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
  auto it = kAclStageByName.find(lower);
  if (it != kAclStageByName.end()) {
    return it->second;
  }
  throw std::invalid_argument(
      fmt::format(
          "Invalid stage '{}'. Valid values: ingress, ingress-macsec, "
          "egress-macsec, ingress-post-lookup",
          s));
}
} // namespace

AclTableGroupConfigArgs::AclTableGroupConfigArgs(std::vector<std::string> v) {
  if (v.size() != 3) {
    throw std::invalid_argument(
        fmt::format(
            "Expected <group-name> stage <stage-value>, got {} argument(s)",
            v.size()));
  }
  if (v[1] != kAclTableGroupAttrStage) {
    throw std::invalid_argument(
        fmt::format(
            "Unknown attribute '{}' for acl table-group. Valid attrs: stage",
            v[1]));
  }
  groupName_ = v[0];
  stage_ = parseAclStage(v[2]);
  data_ = std::move(v);
}

CmdConfigAclTableGroupTraits::RetType CmdConfigAclTableGroup::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto& config = session.getAgentConfig();
  auto& swConfig = *config.sw();

  // Refuse up front on a config whose agent ignores aclTableGroups, rather
  // than writing something it will never read.
  acl_utils::requireAclTableGroupMode(config);

  // Creates at the requested stage, or is a no-op when the group already
  // sits there. Any other case throws: a group cannot be moved between
  // stages, and two groups cannot share one.
  const bool created = acl_utils::findOrCreateAclTableGroup(
      swConfig, args.getGroupName(), args.getStage());

  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  if (created) {
    return fmt::format(
        "Created acl table-group '{}' at stage {}",
        args.getGroupName(),
        apache::thrift::util::enumNameSafe(args.getStage()));
  }
  return fmt::format(
      "acl table-group '{}' is already at stage {}; nothing to do",
      args.getGroupName(),
      apache::thrift::util::enumNameSafe(args.getStage()));
}

void CmdConfigAclTableGroup::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void
CmdHandler<CmdConfigAclTableGroup, CmdConfigAclTableGroupTraits>::run();

} // namespace facebook::fboss
