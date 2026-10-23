/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/qos/queue_config/CmdDeleteQosQueueConfigQueueId.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/Conv.h>
#include <folly/String.h>
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include <thrift/lib/cpp/util/EnumUtils.h>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/config/QueueConfigUtils.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

namespace {

constexpr std::string_view kAttrAqm = "active-queue-management";
constexpr std::string_view kAttrAqmShort = "aqm";
constexpr std::string_view kAttrRateLimit = "rate-limit";

// The optional PortQueue fields a delete may reset. scheduling and stream-type
// are required thrift fields and so are deliberately absent.
// max-dynamic-shared-bytes and buffer-pool-name are also absent: the agent's
// checkSwConfPortQueueMatch() does not compare them, so clearing one on an
// existing queue is not re-programmed and the reset would be a silent no-op.
const std::set<std::string_view> kResettableAttrs = {
    "name",
    "weight",
    "reserved-bytes",
    "shared-bytes",
    "scaling-factor",
    kAttrRateLimit,
};

constexpr auto kValidDeleteAttrs =
    "name, weight, reserved-bytes, shared-bytes, scaling-factor, rate-limit, "
    "active-queue-management <ECN|EARLY_DROP>";

void resetAttribute(cfg::PortQueue& queue, std::string_view attr) {
  if (attr == "name") {
    queue.name().reset();
  } else if (attr == "weight") {
    queue.weight().reset();
  } else if (attr == "reserved-bytes") {
    queue.reservedBytes().reset();
  } else if (attr == "shared-bytes") {
    queue.sharedBytes().reset();
  } else if (attr == "scaling-factor") {
    queue.scalingFactor().reset();
  } else if (attr == kAttrRateLimit) {
    queue.portQueueRate().reset();
  }
}

} // namespace

DeleteQueueId::DeleteQueueId(std::vector<std::string> v) {
  if (v.empty()) {
    throw std::invalid_argument("queue-id is required");
  }
  auto parsed = folly::tryTo<int16_t>(v[0]);
  if (!parsed.hasValue()) {
    throw std::invalid_argument(
        fmt::format("Invalid queue-id: '{}'. Must be an integer", v[0]));
  }
  // Shared upper bound (utils::kMaxQueueId): the same limit the config
  // command's queue-id parser enforces, kept in one place so they can't
  // drift.
  if (parsed.value() < 0 || parsed.value() > utils::kMaxQueueId) {
    throw std::invalid_argument(
        fmt::format(
            "queue-id must be between 0 and {}, got: {}",
            utils::kMaxQueueId,
            v[0]));
  }
  queueId_ = parsed.value();

  for (size_t i = 1; i < v.size(); ++i) {
    const auto& attr = v[i];
    if (attr == kAttrAqm || attr == kAttrAqmShort) {
      if (i + 1 >= v.size()) {
        throw std::invalid_argument(
            fmt::format(
                "{} requires the behavior of the entry to remove: "
                "{} <ECN|EARLY_DROP>",
                kAttrAqm,
                kAttrAqm));
      }
      aqmBehaviors_.push_back(utils::parseCongestionBehavior(v[++i]));
    } else if (kResettableAttrs.count(attr) != 0) {
      attributes_.push_back(attr);
    } else {
      throw std::invalid_argument(
          fmt::format(
              "Unknown queue attribute '{}'. Valid attributes are: {}",
              attr,
              kValidDeleteAttrs));
    }
  }
  data_ = std::move(v);
}

CmdDeleteQosQueueConfigQueueIdTraits::RetType
CmdDeleteQosQueueConfigQueueId::queryClient(
    const HostInfo& /* hostInfo */,
    const utils::QueueConfigName& name,
    const ObjectArgType& queueId) {
  auto& session = ConfigSession::getInstance();
  auto& agentConfig = session.getAgentConfig();
  auto& switchConfig = *agentConfig.sw();

  // findQueueConfigList rather than queueConfigListForWrite: a missing name
  // must not silently create an empty entry.
  auto* configList = utils::findQueueConfigList(switchConfig, name);
  if (configList == nullptr) {
    return fmt::format(
        "Warning: queue config '{}' not found, nothing to delete",
        name.getName());
  }

  int16_t queueIdVal = queueId.getQueueId();
  auto it = std::find_if(
      configList->begin(), configList->end(), [queueIdVal](const auto& queue) {
        return *queue.id() == queueIdVal;
      });

  if (it == configList->end()) {
    return fmt::format(
        "Warning: queue-id {} not found in queue config '{}', nothing to delete",
        queueIdVal,
        name.getName());
  }

  if (queueId.wholeQueue()) {
    // No binding check here, unlike whole-config deletion: dropping one queue
    // leaves Port::portQueueConfigName resolving to the same (smaller) config,
    // so no reference is left dangling. An emptied entry is likewise left in
    // place so queues can be added back to it later.
    configList->erase(it);

    session.saveConfig(
        cli::ServiceType::AGENT, cli::ConfigActionLevel::SERVICE_RESTART);

    return fmt::format(
        "Successfully deleted queue config '{}' queue-id {}",
        name.getName(),
        queueIdVal);
  }

  // Attribute-level reset. Edit a copy and splice it back only once every
  // requested reset resolved, so a missing second AQM entry leaves the first
  // one in place too (same discipline as the config command).
  std::vector<std::string> reset;
  cfg::PortQueue queue = *it;
  for (auto behavior : queueId.getAqmBehaviors()) {
    const auto behaviorName = apache::thrift::util::enumNameSafe(behavior);
    if (!queue.aqms().has_value()) {
      throw std::runtime_error(
          fmt::format(
              "No active-queue-management on queue-id {} in queue config '{}'",
              queueIdVal,
              name.getName()));
    }
    auto& aqms = *queue.aqms();
    auto aqmIt =
        std::find_if(aqms.begin(), aqms.end(), [behavior](const auto& aqm) {
          return *aqm.behavior() == behavior;
        });
    if (aqmIt == aqms.end()) {
      throw std::runtime_error(
          fmt::format(
              "No {} active-queue-management on queue-id {} in queue config "
              "'{}'",
              behaviorName,
              queueIdVal,
              name.getName()));
    }
    aqms.erase(aqmIt);
    if (aqms.empty()) {
      // An empty optional list and an absent one serialize differently;
      // absent is what a queue that never had AQM carries.
      queue.aqms().reset();
    }
    reset.push_back(fmt::format("{} {}", kAttrAqm, behaviorName));
  }
  for (const auto& attr : queueId.getAttributes()) {
    // Resetting an unset optional is a no-op, not an error, so a script can
    // clear a field without first checking whether it is set.
    resetAttribute(queue, attr);
    reset.push_back(attr);
  }
  *it = std::move(queue);

  session.saveConfig(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::SERVICE_RESTART);

  return fmt::format(
      "Reset queue config '{}' queue-id {} {}",
      name.getName(),
      queueIdVal,
      folly::join(", ", reset));
}

void CmdDeleteQosQueueConfigQueueId::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<
    CmdDeleteQosQueueConfigQueueId,
    CmdDeleteQosQueueConfigQueueIdTraits>::run();

} // namespace facebook::fboss
