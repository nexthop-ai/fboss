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

#include <algorithm>
#include <cstdint>
<<<<<<< HEAD
||||||| be11fad19c
=======
#include <optional>
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6
#include <stdexcept>
#include <string>
#include <string_view>
<<<<<<< HEAD
||||||| be11fad19c
=======
#include <utility>
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6
#include <vector>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/QueueConfigUtils.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

<<<<<<< HEAD
// Shared vocabulary for the copp cpu-traffic-policy match-action commands,
// used by both the `config` and `delete` command trees so the accepted
// action-type tokens and the matcher lookup live in one place.
namespace copp_cpu_traffic_policy {

constexpr std::string_view kActionSendToQueue = "send-to-queue";
constexpr std::string_view kActionCounter = "counter";
constexpr std::string_view kActionSetTc = "set-tc";
constexpr std::string_view kActionUserDefinedTrap = "user-defined-trap";

inline bool isValidActionType(std::string_view actionType) {
  return actionType == kActionSendToQueue || actionType == kActionCounter ||
      actionType == kActionSetTc || actionType == kActionUserDefinedTrap;
}

// Return an iterator to the matchToAction entry for `matcher`, or end().
inline std::vector<cfg::MatchToAction>::iterator findMatchToAction(
    std::vector<cfg::MatchToAction>& matchToActions,
    const std::string& matcher) {
  return std::find_if(
      matchToActions.begin(),
      matchToActions.end(),
      [&matcher](const cfg::MatchToAction& mta) {
        return *mta.matcher() == matcher;
      });
}

} // namespace copp_cpu_traffic_policy

// Argument for `config copp cpu-queue <id> [<sub-cmd> <value>]`.
||||||| be11fad19c
// Argument for `config copp cpu-queue <id> [<sub-cmd> <value>]`.
=======
// Argument for `config copp queue <id> [<attr> <value> ...]`.
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6
//
// Accepted forms (validated by CoppQueueArgs):
//   <id>                         -> ensure queue <id> exists; creating a new
//                                   one requires the stream-type attribute
//   <id> <attr> <value...> [...] -> any cfg::PortQueue attribute accepted by
//                                   utils::applyPortQueueConfig (see
//                                   utils::validQueueAttrs()): name,
//                                   reserved-bytes, shared-bytes,
//                                   max-dynamic-shared-bytes, weight,
//                                   scaling-factor, scheduling, stream-type,
//                                   buffer-pool-name, rate-limit,
//                                   active-queue-management
//
// Attributes may be combined in a single invocation. active-queue-management
// consumes all remaining tokens, and rate-limit takes several value tokens.
// This is the same grammar as `config qos queue-config <name>`, parsed and
// applied by the same code -- copp keeps no queue vocabulary of its own.
//
// The accepted integer range for <id> is 0..255 (CPU queue IDs are a small,
// platform-bounded set; the exact cap depends on the ASIC via
// SaiHostifManager::getMaxCpuQueues). Attribute value parsing is deferred to
// applyCpuQueueConfig() so error messages can name the specific attribute.
class CoppQueueArgs : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */ CoppQueueArgs( // NOLINT(google-explicit-constructor)
      std::vector<std::string> v);

  int16_t getQueueId() const {
    return queueId_;
  }

  // <attr, value tokens> destined for utils::applyPortQueueConfig.
  const std::vector<std::pair<std::string, std::vector<std::string>>>&
  getAttributes() const {
    return attributes_;
  }

  // Token stream following active-queue-management, if present.
  const std::vector<std::string>& getAqmAttributes() const {
    return aqmAttributes_;
  }

  bool hasEdits() const {
    return !attributes_.empty() || !aqmAttributes_.empty();
  }

 private:
  int16_t queueId_ = 0;
  std::vector<std::pair<std::string, std::vector<std::string>>> attributes_;
  std::vector<std::string> aqmAttributes_;
};

// Argument for `config copp reason <reason-name> queue <id> [order <n>]`.
//
// <reason-name> is matched case-insensitively against the cfg::PacketRxReason
// enum (e.g. arp, ndp, bgp, lacp, lldp, dhcp, dhcpv6, bgpv6, ttl_1, ...).
// <id> is validated as a non-negative int16.
//
// rxReasonToQueueOrderedList is position-sensitive (the agent programs the
// reasons in list order), so `order <n>` places the entry at 0-based index
// <n>. Without it, a new reason appends and an existing reason keeps its
// current position.
class CoppReasonArgs : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */ CoppReasonArgs( // NOLINT(google-explicit-constructor)
      std::vector<std::string> v);

  cfg::PacketRxReason getReason() const {
    return reason_;
  }

  int16_t getQueueId() const {
    return queueId_;
  }

  const std::optional<size_t>& getOrder() const {
    return order_;
  }

 private:
  cfg::PacketRxReason reason_{};
  int16_t queueId_ = 0;
  std::optional<size_t> order_;
};

// Argument for
// `config copp cpu-traffic-policy match <matcher-name> action <action-type>
// <value>`.
//
// <matcher-name> references an ACL defined in the config; the entry in
// cpuTrafficPolicy.trafficPolicy.matchToAction is created if absent.
// <action-type> / <value> pairs:
//   send-to-queue     <queue-id>      (integer 0-255)
//   counter           <counter-name>  (non-empty string)
//   set-tc            <tc-value>      (integer 0-127)
//   user-defined-trap <queue-id>      (integer 0-255)
class CoppCpuTrafficPolicyArgs : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */
  CoppCpuTrafficPolicyArgs( // NOLINT(google-explicit-constructor)
      std::vector<std::string> v);

  const std::string& getMatcherName() const {
    return matcherName_;
  }

  const std::string& getActionType() const {
    return actionType_;
  }

  const std::string& getActionValue() const {
    return actionValue_;
  }

 private:
  std::string matcherName_;
  std::string actionType_;
  std::string actionValue_;
};

// The `copp` parent node itself is not usable; it only exists to dispatch to
<<<<<<< HEAD
// cpu-queue, reason, and cpu-traffic-policy. The parent needs a handler
// (rather than being a pure branch node) so that addCommandBranch()
// increments depth before descending into the leaves — without that, the
// children would all register their positional args at the same CmdArgsLists
// slot, and CLI11 parsing collides with siblings of `config` whose names
// happen to also be valid reason names (e.g. `arp`).
||||||| be11fad19c
// cpu-queue and reason. The parent needs a handler (rather than being a pure
// branch node) so that addCommandBranch() increments depth before descending
// into the leaves — without that, cpu-queue and reason would both register
// their positional args at the same CmdArgsLists slot, and CLI11 parsing
// collides with siblings of `config` whose names happen to also be valid
// reason names (e.g. `arp`).
=======
// queue and reason. The parent needs a handler (rather than being a pure
// branch node) so that addCommandBranch() increments depth before descending
// into the leaves — without that, queue and reason would both register
// their positional args at the same CmdArgsLists slot, and CLI11 parsing
// collides with siblings of `config` whose names happen to also be valid
// reason names (e.g. `arp`).
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6
struct CmdConfigCoppTraits : public WriteCommandTraits {
  using ObjectArgType = utils::NoneArgType;
  using RetType = std::string;
};

class CmdConfigCopp : public CmdHandler<CmdConfigCopp, CmdConfigCoppTraits> {
 public:
  using ObjectArgType = CmdConfigCoppTraits::ObjectArgType;
  using RetType = CmdConfigCoppTraits::RetType;

  RetType queryClient(const HostInfo& /* hostInfo */) {
    throw std::runtime_error(
<<<<<<< HEAD
        "Incomplete command, please use 'cpu-queue', 'reason', or "
        "'cpu-traffic-policy' subcommand");
||||||| be11fad19c
        "Incomplete command, please use 'cpu-queue' or 'reason' subcommand");
=======
        "Incomplete command, please use 'queue' or 'reason' subcommand");
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6
  }

  void printOutput(const RetType& /* model */) {}
};

struct CmdConfigCoppQueueTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigCopp;
  using ObjectArgType = CoppQueueArgs;
  using RetType = std::string;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    // required() + expected() keeps CLI11 routing positionals to this option
    // instead of reclassifying them as sibling `config <x>` subcommands (see
    // the CmdConfigCoppReasonTraits comment). Only the first `min` tokens are
    // shielded, so a *value* that spells a sibling name past token 1 (e.g.
    // `queue 1 name arp`) can still be hijacked -- an accepted limitation of
    // this variable-length grammar; pick queue names that are not fboss2
    // command words.
    cmd.add_option(
           "copp_queue_config",
           args,
           "<id> [<attr> <value> ...] where <attr> is one of: "
           "name <string>, rate-limit <kbps|pps> <max>, " +
               utils::validQueueAttrs())
        ->required()
        ->expected(1, 64);
  }
};

class CmdConfigCoppQueue
    : public CmdHandler<CmdConfigCoppQueue, CmdConfigCoppQueueTraits> {
 public:
  using ObjectArgType = CmdConfigCoppQueueTraits::ObjectArgType;
  using RetType = CmdConfigCoppQueueTraits::RetType;

  RetType queryClient(const HostInfo& hostInfo, const ObjectArgType& args);

  void printOutput(const RetType& logMsg);
};

struct CmdConfigCoppReasonTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigCopp;
  using ObjectArgType = CoppReasonArgs;
  using RetType = std::string;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    // required() + expected(3) forces CLI11 to route positionals to this
    // option even when they would otherwise classify as a subcommand.
    // Without this, `config copp reason arp queue 0` sees CLI11 reclassify
    // "arp" as the sibling `config arp` subcommand via _valid_subcommand
    // recursing up the ancestor chain.
    cmd.add_option(
           "copp_reason_config",
           args,
           "<reason-name> queue <id> [order <n>] where <reason-name> is a "
           "cfg::PacketRxReason (e.g. arp, ndp, bgp, bgpv6, lacp, "
           "lldp, dhcp, dhcpv6, ttl_1, ...) and <n> is the 0-based position "
           "in rxReasonToQueueOrderedList")
        ->required()
        ->expected(3, 5);
  }
};

class CmdConfigCoppReason
    : public CmdHandler<CmdConfigCoppReason, CmdConfigCoppReasonTraits> {
 public:
  using ObjectArgType = CmdConfigCoppReasonTraits::ObjectArgType;
  using RetType = CmdConfigCoppReasonTraits::RetType;

  RetType queryClient(const HostInfo& hostInfo, const ObjectArgType& args);

  void printOutput(const RetType& logMsg);
};

struct CmdConfigCoppCpuTrafficPolicyTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigCopp;
  using ObjectArgType = CoppCpuTrafficPolicyArgs;
  using RetType = std::string;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    // required() + expected(5) forces CLI11 to route positionals to this
    // option even when a token would otherwise classify as a subcommand
    // elsewhere in the tree (same rationale as CmdConfigCoppReasonTraits).
    cmd.add_option(
           "copp_cpu_traffic_policy_config",
           args,
           "match <matcher-name> action <action-type> <value> where "
           "<action-type> <value> is one of: send-to-queue <queue-id>, "
           "counter <counter-name>, set-tc <tc-value>, "
           "user-defined-trap <queue-id>")
        ->required()
        ->expected(5);
  }
};

class CmdConfigCoppCpuTrafficPolicy : public CmdHandler<
                                          CmdConfigCoppCpuTrafficPolicy,
                                          CmdConfigCoppCpuTrafficPolicyTraits> {
 public:
  using ObjectArgType = CmdConfigCoppCpuTrafficPolicyTraits::ObjectArgType;
  using RetType = CmdConfigCoppCpuTrafficPolicyTraits::RetType;

  RetType queryClient(const HostInfo& hostInfo, const ObjectArgType& args);

  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
