/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/acl/table/CmdDeleteAclTable.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/commands/config/acl/AclConfigUtils.h"

#include <fmt/format.h>
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

AclTableDeleteArgs::AclTableDeleteArgs(std::vector<std::string> v) {
  if (v.size() != 1) {
    throw std::invalid_argument(
        fmt::format("Expected <table-name>, got {} argument(s)", v.size()));
  }
  tableName_ = v[0];
  data_ = std::move(v);
}

CmdDeleteAclTableTraits::RetType CmdDeleteAclTable::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto& swConfig = *session.getAgentConfig().sw();

  auto [table, groupName] =
      acl_utils::resolveAclTable(swConfig, args.getTableName());

  // Every rule in the table is about to stop existing, so its traffic-policy
  // actions have to go with it. checkTrafficPolicyAclsExistInConfig walks both
  // policies and rejects a matcher naming a missing AclEntry, so a leftover
  // would make the next commit fail.
  const auto ruleNames = acl_utils::ruleNamesOfTable(*table);
  const auto entryCount = ruleNames.size();
  const auto strippedMatchers =
      acl_utils::stripMatchersForRules(swConfig, ruleNames);

  // resolveAclTable() already proved the table exists in this group; erase it
  // by the pointer it handed back rather than searching again by name.
  auto& tables =
      *acl_utils::findAclTableGroupOrThrow(swConfig, groupName).aclTables();
  tables.erase(tables.begin() + (table - tables.data()));

  // Removing a table is a hardware teardown rather than an entry edit: the
  // SAI layer drops the table object and everything in it. A config reload
  // still suffices, so the level stays HITLESS.
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  return fmt::format(
      "Deleted acl table '{}' from group '{}' ({} rule(s), {} traffic-policy "
      "action entr(ies)); the table is torn down in hardware when this is "
      "committed",
      args.getTableName(),
      groupName,
      entryCount,
      strippedMatchers);
}

void CmdDeleteAclTable::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

template void CmdHandler<CmdDeleteAclTable, CmdDeleteAclTableTraits>::run();

} // namespace facebook::fboss
