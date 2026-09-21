/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/acl/rule/CmdConfigAclRule.h"

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/commands/config/acl/AclConfigUtils.h"
#include "fboss/cli/fboss2/commands/config/acl/rule/AclRuleAttrs.h"
#include "fboss/cli/fboss2/commands/config/traffic_counter/TrafficCounterConfigUtils.h"

#include <fmt/format.h>
#include <folly/String.h>
#include <algorithm>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

std::string aclRuleConfigHelpText() {
  static const std::string kText =
      "<table-name> <rule-name> <attr> <value> [<extra>] "
      "creates the rule if missing; <attr> is one of: " +
      aclRuleAttrKeysCsv() +
      ". For 'action', <value> is one of: " + aclRuleActionKeysCsv() +
      " (all take no further value). Richer actions (send-to-queue, set-dscp, "
      "set-tc, mirror, counter, to-cpu, redirect, ...) are set with `config "
      "copp traffic-policy` or `config data-plane traffic-policy`, which name "
      "the policy the action belongs to.";
  return kText;
}

AclRuleConfigArgs::AclRuleConfigArgs(std::vector<std::string> v) {
  // Validate + parse the spec into a deferred mutation (throws on bad input).
  AclRuleMutation m = parseAclRuleSpec(v);
  tableName_ = v[kAclRuleIdxTable];
  ruleName_ = v[kAclRuleIdxRule];
  attribute_ = v[kAclRuleIdxAttr];
  // Echo every token after <attr> so the success message shows exactly what
  // was set (ttl mask, action value, redirect ip, ...).
  rawValue_ = folly::join(" ", v.begin() + kAclRuleMatchPrefix, v.end());
  applyEntryFn_ = std::move(m.entryFn);
  data_ = std::move(v);
}

void AclRuleConfigArgs::applyTo(cfg::AclEntry& rule) const {
  if (applyEntryFn_) {
    applyEntryFn_(rule);
  }
}

CmdConfigAclRuleTraits::RetType CmdConfigAclRule::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto& config = session.getAgentConfig();
  auto& swConfig = *config.sw();

  auto [matchingTable, matchingGroupName] =
      acl_utils::resolveAclTable(swConfig, args.getTableName());

  auto& entries = *matchingTable->aclEntries();
  auto eit =
      std::find_if(entries.begin(), entries.end(), [&](const cfg::AclEntry& e) {
        return *e.name() == args.getRuleName();
      });
  bool created = false;
  if (eit == entries.end()) {
    cfg::AclEntry fresh;
    fresh.name() = args.getRuleName();
    entries.push_back(std::move(fresh));
    eit = std::prev(entries.end());
    created = true;
  }

  args.applyTo(*eit);

<<<<<<< HEAD
=======
  // MatchAction-typed action sub-attrs (send-to-queue, set-dscp, set-tc,
  // mirror-ingress, mirror-egress, counter, trap/copy-to-cpu, redirect)
  // live on dataPlaneTrafficPolicy.matchToAction, keyed by rule name —
  // not on the AclEntry. Locate or create the MatchToAction for this
  // rule and apply the action to it.
  if (args.isMatchAction()) {
    if (!swConfig.dataPlaneTrafficPolicy()) {
      swConfig.dataPlaneTrafficPolicy() = cfg::TrafficPolicyConfig{};
    }
    auto& mtaList = *swConfig.dataPlaneTrafficPolicy()->matchToAction();
    auto mit = std::find_if(
        mtaList.begin(), mtaList.end(), [&](const cfg::MatchToAction& mta) {
          return *mta.matcher() == args.getRuleName();
        });
    if (mit == mtaList.end()) {
      cfg::MatchToAction fresh;
      fresh.matcher() = args.getRuleName();
      mtaList.push_back(std::move(fresh));
      mit = std::prev(mtaList.end());
    }
    args.applyActionTo(*mit->action());
    if (const auto& counterName = mit->action()->counter()) {
      utils::ensureTrafficCounterDeclared(swConfig, *counterName);
    }
  }

>>>>>>> bfe2a26c7c (NOS-16562: Create missing counters when configuring ACL and CoPP actions (#1966))
  // AclEntry mutations are applied at runtime via processAclTableGroupDelta
  // in SaiAclTableManager; SaiSwitch has no warmboot-prohibited guard for
  // ACL entry attributes, so every supported attribute is HITLESS.
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);

  return fmt::format(
      "{} acl rule '{}' (table '{}', group '{}') {} to {}",
      created ? "Created and set" : "Set",
      args.getRuleName(),
      args.getTableName(),
      matchingGroupName,
      args.getAttribute(),
      args.getRawValue());
}

void CmdConfigAclRule::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdConfigAclRule, CmdConfigAclRuleTraits>::run();

} // namespace facebook::fboss
