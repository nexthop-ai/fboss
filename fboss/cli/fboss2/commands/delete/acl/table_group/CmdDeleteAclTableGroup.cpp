/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/acl/table_group/CmdDeleteAclTableGroup.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/commands/config/acl/AclConfigUtils.h"

#include <fmt/format.h>
#include <algorithm>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

AclTableGroupDeleteArgs::AclTableGroupDeleteArgs(std::vector<std::string> v) {
  if (v.size() != 1) {
    throw std::invalid_argument(
        fmt::format("Expected <group-name>, got {} argument(s)", v.size()));
  }
  groupName_ = v[0];
  data_ = std::move(v);
}

CmdDeleteAclTableGroupTraits::RetType CmdDeleteAclTableGroup::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto& swConfig = *session.getAgentConfig().sw();

  // Throws when the group is absent, and when there are no aclTableGroups at
  // all (a box on the flat sw.acls path).
  const auto& group =
      acl_utils::findAclTableGroupOrThrow(swConfig, args.getGroupName());

  // Refuse to empty the list. updateAclTableGroups throws "ACL Table Group
  // must be specified if Multiple ACL Table support is enabled" when neither
  // aclTableGroup nor a non-empty aclTableGroups is present, so this would
  // produce a config that cannot be committed.
  if (swConfig.aclTableGroups()->size() == 1) {
    throw std::runtime_error(
        fmt::format(
            "AclTableGroup '{}' is the only group in the config and cannot be "
            "deleted: the agent requires at least one when multiple ACL table "
            "support is enabled",
            args.getGroupName()));
  }

  std::set<std::string> ruleNames;
  std::size_t tableCount = 0;
  for (const auto& table : *group.aclTables()) {
    ++tableCount;
    ruleNames.merge(acl_utils::ruleNamesOfTable(table));
  }
  const auto strippedMatchers =
      acl_utils::stripMatchersForRules(swConfig, ruleNames);

  auto& groups = *swConfig.aclTableGroups();
  groups.erase(
      std::remove_if(
          groups.begin(),
          groups.end(),
          [&](const cfg::AclTableGroup& g) {
            return *g.name() == args.getGroupName();
          }),
      groups.end());

  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  return fmt::format(
      "Deleted acl table-group '{}' ({} table(s), {} rule(s), {} "
      "traffic-policy action entr(ies)); the tables are torn down in hardware "
      "when this is committed",
      args.getGroupName(),
      tableCount,
      ruleNames.size(),
      strippedMatchers);
}

void CmdDeleteAclTableGroup::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

template void
CmdHandler<CmdDeleteAclTableGroup, CmdDeleteAclTableGroupTraits>::run();

} // namespace facebook::fboss
