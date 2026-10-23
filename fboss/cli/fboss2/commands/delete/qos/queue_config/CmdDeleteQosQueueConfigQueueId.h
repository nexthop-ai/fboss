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

#include <cstdint>
#include <string>
#include <vector>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/QueueConfigUtils.h"
#include "fboss/cli/fboss2/commands/delete/qos/queue_config/CmdDeleteQosQueueConfig.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

/**
 * Parses the positional tokens of
 *   delete qos queue-config <name> queue-id <id> [<attr> ...]
 *
 * With no attribute the whole queue entry is removed. With attributes only the
 * named optional fields are reset on the queue, which otherwise stays:
 *   name, weight, reserved-bytes, shared-bytes, scaling-factor, rate-limit
 *   active-queue-management <ECN|EARLY_DROP>  - drop that AQM entry
 *
 * active-queue-management takes the behavior because aqms is a list keyed by
 * it (a queue may carry an ECN and an EARLY_DROP entry side by side), the same
 * key `config qos queue-config` uses to pick the entry it edits.
 *
 * scheduling and stream-type are required thrift fields, so "delete" has no
 * meaning for them: use `config qos queue-config` to change them.
 */
class DeleteQueueId : public utils::BaseObjectArgType<std::string> {
 public:
  // NOLINTNEXTLINE(google-explicit-constructor)
  /* implicit */ DeleteQueueId(std::vector<std::string> v);

  int16_t getQueueId() const {
    return queueId_;
  }

  // Optional scalar fields to reset, in command-line order. Empty together
  // with getAqmBehaviors() means "remove the whole queue".
  const std::vector<std::string>& getAttributes() const {
    return attributes_;
  }

  // AQM entries to drop, keyed by behavior.
  const std::vector<cfg::QueueCongestionBehavior>& getAqmBehaviors() const {
    return aqmBehaviors_;
  }

  bool wholeQueue() const {
    return attributes_.empty() && aqmBehaviors_.empty();
  }

 private:
  int16_t queueId_{0};
  std::vector<std::string> attributes_;
  std::vector<cfg::QueueCongestionBehavior> aqmBehaviors_;
};

struct CmdDeleteQosQueueConfigQueueIdTraits : public WriteCommandTraits {
  using ParentCmd = CmdDeleteQosQueueConfig;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    cmd.add_option(
           "queue_id",
           args,
           "<id> [<attr> ...] - omit attributes to remove the whole queue, or "
           "name the optional field(s) to reset: name, weight, "
           "reserved-bytes, shared-bytes, scaling-factor, rate-limit, "
           "active-queue-management <ECN|EARLY_DROP>")
        ->required()
        ->expected(-1);
  }
  using ObjectArgType = DeleteQueueId;
  using RetType = std::string;
};

class CmdDeleteQosQueueConfigQueueId
    : public CmdHandler<
          CmdDeleteQosQueueConfigQueueId,
          CmdDeleteQosQueueConfigQueueIdTraits> {
 public:
  using ObjectArgType = CmdDeleteQosQueueConfigQueueIdTraits::ObjectArgType;
  using RetType = CmdDeleteQosQueueConfigQueueIdTraits::RetType;

  RetType queryClient(
      const HostInfo& hostInfo,
      const utils::QueueConfigName& name,
      const ObjectArgType& queueId);

  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
