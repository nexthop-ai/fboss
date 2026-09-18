/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/qos/buffer_pool/CmdDeleteQosBufferPool.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/String.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

namespace {

// Every field that can name a buffer pool. Refuse rather than cascade: the
// pool's users are scattered across queue and PG configs that the operator
// did not name on the command line.
std::vector<std::string> findReferences(
    const cfg::SwitchConfig& sw,
    const std::string& name) {
  std::vector<std::string> refs;
  auto scanQueues = [&](const auto& queues, const std::string& where) {
    for (const auto& q : queues) {
      if (q.bufferPoolName().has_value() && *q.bufferPoolName() == name) {
        refs.push_back(fmt::format("{}[queue {}]", where, *q.id()));
      }
    }
  };
  scanQueues(*sw.cpuQueues(), "cpuQueues");
  scanQueues(*sw.defaultPortQueues(), "defaultPortQueues");
  for (const auto& [cfgName, queues] : *sw.portQueueConfigs()) {
    scanQueues(queues, fmt::format("portQueueConfigs[{}]", cfgName));
  }
  if (sw.portPgConfigs().has_value()) {
    for (const auto& [pgName, pgs] : *sw.portPgConfigs()) {
      for (const auto& pg : pgs) {
        if (*pg.bufferPoolName() == name) {
          refs.push_back(
              fmt::format("portPgConfigs[{}][pg {}]", pgName, *pg.id()));
        }
      }
    }
  }
  return refs;
}

} // namespace

CmdDeleteQosBufferPoolTraits::RetType CmdDeleteQosBufferPool::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& poolName) {
  auto& session = ConfigSession::getInstance();
  auto& sw = *session.getAgentConfig().sw();
  const std::string& name = poolName.getName();

  if (!sw.bufferPoolConfigs().has_value() ||
      sw.bufferPoolConfigs()->find(name) == sw.bufferPoolConfigs()->end()) {
    throw std::runtime_error(
        fmt::format("Buffer pool '{}' does not exist", name));
  }

  auto refs = findReferences(sw, name);
  if (!refs.empty()) {
    throw std::runtime_error(
        fmt::format(
            "Cannot delete buffer pool '{}': still referenced by {}. "
            "Unset those fields first, then retry the delete.",
            name,
            folly::join(", ", refs)));
  }

  sw.bufferPoolConfigs()->erase(name);
  if (sw.bufferPoolConfigs()->empty()) {
    sw.bufferPoolConfigs().reset();
  }
  session.saveConfig();

  return fmt::format("Successfully deleted buffer pool '{}'", name);
}

void CmdDeleteQosBufferPool::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

template void
CmdHandler<CmdDeleteQosBufferPool, CmdDeleteQosBufferPoolTraits>::run();

} // namespace facebook::fboss
