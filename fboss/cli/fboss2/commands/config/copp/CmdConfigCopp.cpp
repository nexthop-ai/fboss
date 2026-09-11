/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/copp/CmdConfigCopp.h"

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/Conv.h>
#include <thrift/lib/cpp/util/EnumUtils.h>
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
#include "fboss/cli/fboss2/commands/config/QueueConfigUtils.h"
#include "fboss/cli/fboss2/commands/config/copp/CoppUtils.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

namespace {

using copp_queue::parseQueueId;

// Literal tokens accepted in
// `config copp reason <reason-name> queue <id> [order <n>]`.
constexpr std::string_view kSubCmdQueue = "queue";
<<<<<<< HEAD

// Literal tokens and action types accepted by
// `config copp cpu-traffic-policy match <matcher-name> action <action-type>
// <value>`.
constexpr std::string_view kSubCmdMatch = "match";
constexpr std::string_view kSubCmdAction = "action";
using copp_cpu_traffic_policy::kActionCounter;
using copp_cpu_traffic_policy::kActionSendToQueue;
using copp_cpu_traffic_policy::kActionSetTc;
using copp_cpu_traffic_policy::kActionUserDefinedTrap;

// SetTcAction.tcValue is a thrift byte (int8_t); values above 127 wrap
// negative. The real per-ASIC cap is enforced by the agent at apply time.
constexpr int16_t kMaxTcValue = 127;

int32_t parseRateMax(const std::string& s, std::string_view unit) {
  int32_t parsed = 0;
  try {
    parsed = folly::to<int32_t>(s);
  } catch (const folly::ConversionError&) {
    throw std::invalid_argument(
        fmt::format(
            "rate-limit {} value must be an integer, got '{}'", unit, s));
  }
  if (parsed < 0) {
    throw std::invalid_argument(
        fmt::format(
            "rate-limit {} value must be non-negative, got {}", unit, parsed));
  }
  return parsed;
}

// Find the cpuQueues[] entry with matching id, or append a fresh one.
// A new entry uses thrift defaults (streamType=UNICAST, unset weight); this
// is only reached when the user targets a queue id that does not exist yet
// in the session config, which is rare in practice — platforms ship with a
// populated cpuQueues list.
cfg::PortQueue& findOrCreateCpuQueue(cfg::SwitchConfig& swConfig, int16_t id) {
  auto& queues = *swConfig.cpuQueues();
  auto it = copp_cpu_queue::findCpuQueue(queues, id);
  if (it != queues.end()) {
    return *it;
  }
  cfg::PortQueue q;
  q.id() = id;
  queues.push_back(q);
  return queues.back();
}

void applyRateLimit(cfg::PortQueue& q, CoppCpuQueueArgs::Op op, int32_t max) {
  cfg::Range range;
  range.minimum() = 0;
  range.maximum() = max;
  cfg::PortQueueRate rate;
  if (op == CoppCpuQueueArgs::Op::RATE_LIMIT_KBPS) {
    rate.kbitsPerSec() = range;
  } else {
    rate.pktsPerSec() = range;
  }
  q.portQueueRate() = rate;
}
||||||| be11fad19c

int32_t parseRateMax(const std::string& s, std::string_view unit) {
  int32_t parsed = 0;
  try {
    parsed = folly::to<int32_t>(s);
  } catch (const folly::ConversionError&) {
    throw std::invalid_argument(
        fmt::format(
            "rate-limit {} value must be an integer, got '{}'", unit, s));
  }
  if (parsed < 0) {
    throw std::invalid_argument(
        fmt::format(
            "rate-limit {} value must be non-negative, got {}", unit, parsed));
  }
  return parsed;
}

// Find the cpuQueues[] entry with matching id, or append a fresh one.
// A new entry uses thrift defaults (streamType=UNICAST, unset weight); this
// is only reached when the user targets a queue id that does not exist yet
// in the session config, which is rare in practice — platforms ship with a
// populated cpuQueues list.
cfg::PortQueue& findOrCreateCpuQueue(cfg::SwitchConfig& swConfig, int16_t id) {
  auto& queues = *swConfig.cpuQueues();
  auto it = copp_cpu_queue::findCpuQueue(queues, id);
  if (it != queues.end()) {
    return *it;
  }
  cfg::PortQueue q;
  q.id() = id;
  queues.push_back(q);
  return queues.back();
}

void applyRateLimit(cfg::PortQueue& q, CoppCpuQueueArgs::Op op, int32_t max) {
  cfg::Range range;
  range.minimum() = 0;
  range.maximum() = max;
  cfg::PortQueueRate rate;
  if (op == CoppCpuQueueArgs::Op::RATE_LIMIT_KBPS) {
    rate.kbitsPerSec() = range;
  } else {
    rate.pktsPerSec() = range;
  }
  q.portQueueRate() = rate;
}
=======
constexpr std::string_view kSubCmdOrder = "order";
>>>>>>> fbc276b526bb5274e1497b421b55d7be9dc455f6

} // namespace

CoppQueueArgs::CoppQueueArgs(std::vector<std::string> v) {
  if (v.empty()) {
    throw std::invalid_argument(
        "Expected <id> [<attr> <value> ...] where <attr> is one of: " +
        utils::validQueueAttrs());
  }
  queueId_ = parseQueueId(v[0], "queue");

  // Every token after <id> is a shared queue attribute, so the grammar cannot
  // drift from `config qos queue-config`'s.
  utils::walkQueueAttributes(v, 1, attributes_, aqmAttributes_);

  data_ = std::move(v);
}

CoppCpuTrafficPolicyArgs::CoppCpuTrafficPolicyArgs(std::vector<std::string> v) {
  if (v.size() != 5) {
    throw std::invalid_argument(
        fmt::format(
            "Expected {} <matcher-name> {} <action-type> <value>, got {} "
            "argument(s)",
            kSubCmdMatch,
            kSubCmdAction,
            v.size()));
  }
  if (v[0] != kSubCmdMatch) {
    throw std::invalid_argument(
        fmt::format(
            "Expected '{}' as first token, got '{}'", kSubCmdMatch, v[0]));
  }
  if (v[1].empty()) {
    throw std::invalid_argument("matcher-name must not be empty");
  }
  if (v[2] != kSubCmdAction) {
    throw std::invalid_argument(
        fmt::format(
            "Expected '{}' between matcher name and action type, got '{}'",
            kSubCmdAction,
            v[2]));
  }
  const auto& actionType = v[3];
  const auto& value = v[4];
  if (actionType == kActionSendToQueue ||
      actionType == kActionUserDefinedTrap) {
    parseQueueId(value, actionType);
  } else if (actionType == kActionSetTc) {
    int32_t tcValue = 0;
    try {
      tcValue = folly::to<int32_t>(value);
    } catch (const folly::ConversionError&) {
      throw std::invalid_argument(
          fmt::format(
              "Invalid tc-value '{}': must be an integer in [0, {}]",
              value,
              kMaxTcValue));
    }
    if (tcValue < 0 || tcValue > kMaxTcValue) {
      throw std::invalid_argument(
          fmt::format(
              "tc-value must be in [0, {}], got {}", kMaxTcValue, tcValue));
    }
  } else if (actionType == kActionCounter) {
    if (value.empty()) {
      throw std::invalid_argument("counter-name must not be empty");
    }
  } else {
    throw std::invalid_argument(
        fmt::format(
            "Invalid action-type '{}': must be one of: {}, {}, {}, {}",
            actionType,
            kActionSendToQueue,
            kActionCounter,
            kActionSetTc,
            kActionUserDefinedTrap));
  }
  matcherName_ = v[1];
  actionType_ = actionType;
  actionValue_ = value;
  data_ = std::move(v);
}

CoppReasonArgs::CoppReasonArgs(std::vector<std::string> v) {
  if (v.size() != 3 && v.size() != 5) {
    throw std::invalid_argument(
        fmt::format(
            "Expected <reason-name> {} <id> [{} <n>], got {} argument(s)",
            kSubCmdQueue,
            kSubCmdOrder,
            v.size()));
  }
  cfg::PacketRxReason reason = copp_reason::parseReason(v[0]);
  if (v[1] != kSubCmdQueue) {
    throw std::invalid_argument(
        fmt::format(
            "Expected '{}' between reason and queue id, got '{}'",
            kSubCmdQueue,
            v[1]));
  }
  reason_ = reason;
  queueId_ = parseQueueId(v[2], "reason");
  if (v.size() == 5) {
    if (v[3] != kSubCmdOrder) {
      throw std::invalid_argument(
          fmt::format(
              "Expected '{}' after the queue id, got '{}'",
              kSubCmdOrder,
              v[3]));
    }
    int32_t parsed = 0;
    try {
      parsed = folly::to<int32_t>(v[4]);
    } catch (const folly::ConversionError&) {
      throw std::invalid_argument(
          fmt::format("order value must be an integer, got '{}'", v[4]));
    }
    if (parsed < 0) {
      throw std::invalid_argument(
          fmt::format("order value must be non-negative, got {}", parsed));
    }
    order_ = static_cast<size_t>(parsed);
  }
  data_ = std::move(v);
}

namespace {

std::string applyCpuQueueConfig(
    cfg::SwitchConfig& swConfig,
    const CoppQueueArgs& args) {
  auto& queues = *swConfig.cpuQueues();
  auto it = copp_queue::findQueue(queues, args.getQueueId());
  const bool existed = it != queues.end();

  // Edit a local copy; splice back only after every attribute validates, so a
  // rejected edit cannot leave a half-built queue in the session config (same
  // pattern as the qos queue-config commands).
  cfg::PortQueue work;
  if (existed) {
    work = *it;
  } else {
    if (!utils::findStreamTypeAttr(args.getAttributes()).has_value()) {
      throw std::invalid_argument(
          fmt::format(
              "Creating queue {} requires stream-type: the agent only installs "
              "cpuQueues entries whose stream type the ASIC's CPU port exposes",
              args.getQueueId()));
    }
    work.id() = args.getQueueId();
  }

  if (!args.getAttributes().empty() || !args.getAqmAttributes().empty()) {
    utils::applyPortQueueConfig(
        work, args.getAttributes(), args.getAqmAttributes());
  }

  // `it` stays valid: nothing above touches `queues`.
  if (existed) {
    *it = work;
  } else {
    queues.push_back(std::move(work));
  }
  if (!args.hasEdits()) {
    return fmt::format("Ensured queue {} exists", args.getQueueId());
  }
  // Echo the applied tokens back (everything after <id>).
  const auto tokens = args.data();
  return fmt::format(
      "Updated queue {}: {}",
      args.getQueueId(),
      folly::join(" ", tokens.begin() + 1, tokens.end()));
}

std::string applyReasonConfig(
    cfg::SwitchConfig& swConfig,
    const CoppReasonArgs& args) {
  if (!swConfig.cpuTrafficPolicy().has_value()) {
    swConfig.cpuTrafficPolicy() = cfg::CPUTrafficPolicyConfig{};
  }
  auto& policy = *swConfig.cpuTrafficPolicy();
  if (!policy.rxReasonToQueueOrderedList().has_value()) {
    policy.rxReasonToQueueOrderedList() =
        std::vector<cfg::PacketRxReasonToQueue>{};
  }
  auto& list = *policy.rxReasonToQueueOrderedList();
  const auto reasonName = apache::thrift::util::enumNameSafe(args.getReason());

  auto it = std::find_if(
      list.begin(), list.end(), [&args](const cfg::PacketRxReasonToQueue& e) {
        return *e.rxReason() == args.getReason();
      });
  const bool existed = it != list.end();

  cfg::PacketRxReasonToQueue entry;
  entry.rxReason() = args.getReason();
  entry.queueId() = args.getQueueId();

  if (!args.getOrder().has_value()) {
    // No order given: an existing reason keeps its position, a new one
    // appends.
    if (existed) {
      *it = entry;
      return fmt::format(
          "Updated reason {} -> queue {}", reasonName, args.getQueueId());
    }
    list.push_back(entry);
    return fmt::format(
        "Mapped reason {} -> queue {}", reasonName, args.getQueueId());
  }

  // The list is position-sensitive; place the entry at the requested 0-based
  // index. The index refers to the final list, so an existing entry doesn't
  // count towards the bound (it is removed before reinsertion).
  const size_t order = *args.getOrder();
  const size_t maxOrder = existed ? list.size() - 1 : list.size();
  if (order > maxOrder) {
    throw std::invalid_argument(
        fmt::format(
            "order {} is out of range: highest valid position is {}",
            order,
            maxOrder));
  }
  if (existed) {
    list.erase(it);
  }
  list.insert(list.begin() + order, entry);
  return fmt::format(
      "{} reason {} -> queue {} at position {}",
      existed ? "Updated" : "Mapped",
      reasonName,
      args.getQueueId(),
      order);
}

std::string applyCpuTrafficPolicyConfig(
    cfg::SwitchConfig& swConfig,
    const CoppCpuTrafficPolicyArgs& args) {
  if (!swConfig.cpuTrafficPolicy().has_value()) {
    swConfig.cpuTrafficPolicy() = cfg::CPUTrafficPolicyConfig{};
  }
  auto& policy = *swConfig.cpuTrafficPolicy();
  if (!policy.trafficPolicy().has_value()) {
    policy.trafficPolicy() = cfg::TrafficPolicyConfig{};
  }
  auto& matchToActions = *policy.trafficPolicy()->matchToAction();

  const auto& name = args.getMatcherName();
  auto it = copp_cpu_traffic_policy::findMatchToAction(matchToActions, name);
  if (it == matchToActions.end()) {
    cfg::MatchToAction newEntry;
    newEntry.matcher() = name;
    newEntry.action() = cfg::MatchAction{};
    matchToActions.push_back(std::move(newEntry));
    it = std::prev(matchToActions.end());
  }

  auto& action = *it->action();
  const auto& actionType = args.getActionType();
  const auto& value = args.getActionValue();
  if (actionType == kActionSendToQueue) {
    cfg::QueueMatchAction queueAction;
    queueAction.queueId() = folly::to<int16_t>(value);
    action.sendToQueue() = std::move(queueAction);
  } else if (actionType == kActionCounter) {
    action.counter() = value;
  } else if (actionType == kActionSetTc) {
    cfg::SetTcAction setTcAction;
    setTcAction.tcValue() = folly::to<int8_t>(value);
    action.setTc() = std::move(setTcAction);
  } else {
    // kActionUserDefinedTrap
    cfg::UserDefinedTrapAction trapAction;
    trapAction.queueId() = folly::to<int16_t>(value);
    action.userDefinedTrap() = std::move(trapAction);
  }

  return fmt::format(
      "Set action '{}' = '{}' for matcher '{}'", actionType, value, name);
}

} // namespace

CmdConfigCoppQueueTraits::RetType CmdConfigCoppQueue::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto msg = applyCpuQueueConfig(*session.getAgentConfig().sw(), args);
  // cpuQueues edits are processed hitlessly by
  // SaiHostifManager::processHostifDelta -> changeCpuQueue -> QueueManager.
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  return msg;
}

void CmdConfigCoppQueue::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

CmdConfigCoppReasonTraits::RetType CmdConfigCoppReason::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto msg = applyReasonConfig(*session.getAgentConfig().sw(), args);
  // rxReason -> queue mapping edits are processed hitlessly by
  // SaiHostifManager::processHostifDelta (trap-group update path).
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  return msg;
}

void CmdConfigCoppReason::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

CmdConfigCoppCpuTrafficPolicyTraits::RetType
CmdConfigCoppCpuTrafficPolicy::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  auto& session = ConfigSession::getInstance();
  auto msg = applyCpuTrafficPolicyConfig(*session.getAgentConfig().sw(), args);
  session.saveConfig(cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS);
  return msg;
}

void CmdConfigCoppCpuTrafficPolicy::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiations
template void CmdHandler<CmdConfigCopp, CmdConfigCoppTraits>::run();
template void CmdHandler<CmdConfigCoppQueue, CmdConfigCoppQueueTraits>::run();
template void CmdHandler<CmdConfigCoppReason, CmdConfigCoppReasonTraits>::run();
template void CmdHandler<
    CmdConfigCoppCpuTrafficPolicy,
    CmdConfigCoppCpuTrafficPolicyTraits>::run();

} // namespace facebook::fboss
