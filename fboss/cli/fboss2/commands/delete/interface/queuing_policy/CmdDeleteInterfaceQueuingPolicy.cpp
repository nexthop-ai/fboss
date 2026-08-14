/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/interface/queuing_policy/CmdDeleteInterfaceQueuingPolicy.h"

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
#include "fboss/cli/fboss2/utils/InterfaceList.h"

namespace facebook::fboss {

CmdDeleteInterfaceQueuingPolicyTraits::RetType
CmdDeleteInterfaceQueuingPolicy::queryClient(
    const HostInfo& /* hostInfo */,
    const utils::InterfaceList& interfaces) {
  if (interfaces.empty()) {
    throw std::invalid_argument("No interface name provided");
  }

  auto& session = ConfigSession::getInstance();

  std::vector<std::string> cleared;
  for (const utils::Intf& intf : interfaces) {
    cfg::Port* port = intf.getPort();
    if (!port) {
      throw std::invalid_argument(
          fmt::format("Interface '{}' is not a physical port.", intf.name()));
    }
    if (!port->portQueueConfigName().has_value()) {
      continue;
    }
    port->portQueueConfigName().reset();
    cleared.push_back(intf.name());
  }

  if (cleared.empty()) {
    return fmt::format(
        "No queuing-policy set on interface(s) {}",
        folly::join(", ", interfaces.getNames()));
  }

  session.saveConfig();

  return fmt::format(
      "Deleted queuing-policy of interface(s) {}; they now use the default "
      "port queue config",
      folly::join(", ", cleared));
}

void CmdDeleteInterfaceQueuingPolicy::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<
    CmdDeleteInterfaceQueuingPolicy,
    CmdDeleteInterfaceQueuingPolicyTraits>::run();

} // namespace facebook::fboss
