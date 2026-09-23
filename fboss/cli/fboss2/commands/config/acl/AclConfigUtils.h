/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#pragma once

#include <optional>
#include <set>
#include <string>
#include <utility>

#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/agent/gen-cpp2/switch_config_types.h"

/*
 * Shared lookup, creation and cleanup helpers for the `acl` command family.
<<<<<<< HEAD
 * Every command that names an AclTableGroup or an AclTable resolves it through
 * here, so the rules about which config shapes are addressable live in one
 * place rather than being restated per handler.
 */
namespace facebook::fboss::acl_utils {

/*
 * Returns a mutable reference to the AclTableGroup named `groupName` in
 * swConfig.aclTableGroups() (field 56; the deprecated aclTableGroup, field
 * 45, is not supported). Throws std::runtime_error when no group with that
 * name exists (including when aclTableGroups is unset or empty).
 */
cfg::AclTableGroup& findAclTableGroupOrThrow(
    cfg::SwitchConfig& swConfig,
    const std::string& groupName);

/*
 * Throws unless the agent config opts into the table-group path with
 * defaultCommandLineArgs["enable_acl_table_group"] = "true". The agent applies
 * that map at startup (initFlagDefaults in CommonInit.cpp), and
 * FLAGS_enable_acl_table_group defaults to false, under which
 * ApplyThriftConfig never reads aclTableGroups at all -- so without the
 * opt-in, anything written there is config the agent silently discards. The
 * flag is read here, never written: which parsing mode the agent runs in is
 * the operator's call, and the error message names the exact line to add.
 */
void requireAclTableGroupMode(const cfg::AgentConfig& config);

/*
 * Ensures the group exists at the given stage, creating it when absent --
 * including the very first group on a config that has none, which is how a
 * box whose agent config already opts into the table-group path (see
 * requireAclTableGroupMode, which callers must have passed) bootstraps its
 * ACL config through the CLI. Returns true when the group was created, false
 * when it already existed, so callers can word their output accordingly.
 *
 * Refuses a second group on a stage that already has one, and refuses to
 * move an existing group to a different stage. AclTableGroupMap is keyed by
 * stage, so a duplicate would overwrite its sibling and a move would read as
 * one group disappearing and another appearing -- which the agent does not
 * apply (it restarts and the stage comes back unchanged).
 */
bool findOrCreateAclTableGroup(
    cfg::SwitchConfig& swConfig,
    const std::string& groupName,
    cfg::AclStage stage);

/*
 * Find an AclTable by name across every AclTableGroup. Returns the table and
 * the name of its owning group, or std::nullopt when no table has that name
 * (including when aclTableGroups is unset). The non-throwing primitive under
 * resolveAclTable, for callers that need to branch on absence.
 */
std::optional<std::pair<cfg::AclTable*, std::string>> findAclTable(
    cfg::SwitchConfig& swConfig,
    const std::string& tableName);

/*
 * Resolve an AclTable by name across every AclTableGroup, or resolve the
 * single table implicitly when `tableName` is unset. Returns the table and the
 * name of its owning group.
 *
 * Table names are unique within a group and we walk all groups, so the caller
 * never has to name the group. Passing std::nullopt is the "default table"
 * case: it succeeds only when exactly one table exists config-wide, which is
 * the shape a stock config ships (one ingress group holding one table), and
 * throws listing the candidates when there is more than one.
 *
 * Throws std::runtime_error when a named table does not exist, or when an
 * omitted name is ambiguous or resolves to nothing.
 */
std::pair<cfg::AclTable*, std::string> resolveAclTable(
    cfg::SwitchConfig& swConfig,
    const std::optional<std::string>& tableName);

/*
 * Remove every MatchToAction whose matcher names one of `ruleNames`, from both
 * dataPlaneTrafficPolicy and cpuTrafficPolicy.trafficPolicy. Callers that
 * delete an AclEntry must run this: ApplyThriftConfig's
 * checkTrafficPolicyAclsExistInConfig walks both policies and rejects a config
 * whose matcher references a rule that no longer exists, so a leftover entry
 * makes the next `config session commit` fail. Takes a set so deleting a whole
 * table is one pass. Returns the number of matchers removed.
 */
/*
 * The names of every AclEntry in the table, in the shape
 * stripMatchersForRules() takes. Both delete commands feed it.
 */
std::set<std::string> ruleNamesOfTable(const cfg::AclTable& table);

||||||| a86baef3b7
=======
 */
namespace facebook::fboss::acl_utils {

/*
 * Mutable reference to the AclTableGroup named `groupName` in
 * swConfig.aclTableGroups(); throws std::runtime_error when absent.
 */
cfg::AclTableGroup& findAclTableGroupOrThrow(
    cfg::SwitchConfig& swConfig,
    const std::string& groupName);

/*
 * Throws unless the agent config sets
 * defaultCommandLineArgs["enable_acl_table_group"] = "true". With the flag
 * off the agent never reads aclTableGroups, so anything written there is
 * silently discarded. The map only sets the flag's *default*
 * (initFlagDefaults applies it with SET_FLAGS_DEFAULT), so an explicit
 * --enable_acl_table_group on the agent command line overrides what this
 * check sees. Read-only: which mode the agent runs in is the operator's call.
 */
void requireAclTableGroupMode(const cfg::AgentConfig& config);

/*
 * Ensures the group exists at the given stage, creating it when absent --
 * including the first group on a config that has none. Returns true when
 * created. Throws on a stage move or on a stage another group already holds.
 */
bool findOrCreateAclTableGroup(
    cfg::SwitchConfig& swConfig,
    const std::string& groupName,
    cfg::AclStage stage);

/*
 * Find an AclTable by name across every AclTableGroup. Returns the table and
 * its owning group's name, or std::nullopt when absent. Non-throwing.
 */
std::optional<std::pair<cfg::AclTable*, std::string>> findAclTable(
    cfg::SwitchConfig& swConfig,
    const std::string& tableName);

/*
 * Resolve an AclTable by name across every group (names are unique across
 * groups, so callers never name the group), or resolve the single table
 * config-wide when `tableName` is unset. Throws when the name is missing, or
 * when an omitted name is ambiguous or matches nothing.
 */
std::pair<cfg::AclTable*, std::string> resolveAclTable(
    cfg::SwitchConfig& swConfig,
    const std::optional<std::string>& tableName);

// The names of every AclEntry in the table, in the shape
// stripMatchersForRules() takes.
std::set<std::string> ruleNamesOfTable(const cfg::AclTable& table);

/*
 * Remove every MatchToAction whose matcher names one of `ruleNames`, from
 * both dataPlaneTrafficPolicy and cpuTrafficPolicy.trafficPolicy. Callers
 * that delete an AclEntry must run this: the agent rejects a config whose
 * matcher references a rule that no longer exists, so a leftover fails the
 * next commit. Returns the number of matchers removed.
 */
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
std::size_t stripMatchersForRules(
    cfg::SwitchConfig& swConfig,
    const std::set<std::string>& ruleNames);

} // namespace facebook::fboss::acl_utils
