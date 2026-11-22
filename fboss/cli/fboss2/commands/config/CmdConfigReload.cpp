/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/CmdConfigReload.h"

#include "fboss/agent/if/gen-cpp2/FbossCtrlAsyncClient.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"

#include <iostream>

namespace facebook::fboss {

CmdConfigReloadTraits::RetType CmdConfigReload::queryClient(
    const HostInfo& hostInfo) {
  auto client =
      utils::createClient<facebook::fboss::FbossCtrlAsyncClient>(hostInfo);

<<<<<<< HEAD
  client->sync_reloadConfig();
  return "Config reloaded successfully";
=======
  // warmboot / coldboot dispatch to local systemctl, so reject non-local
  // hosts to avoid restarting the wrong machine.
  if (!hostInfo.isLocalHost()) {
    throw std::invalid_argument(
        fmt::format(
            "config reload {} is local-only; remove --host or run on the switch.",
            (bootType.level() ==
             cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART)
                ? "coldboot"
                : "warmboot"));
  }

  // Warn (don't refuse) if the operator has an active session on disk; this
  // command operates on /etc/coop/agent.conf only and will not apply session
  // changes. The static check avoids creating a singleton.
  if (ConfigSession::hasStagedConfig()) {
    std::cerr << "Warning: an active config session exists in ~/.fboss2/; this "
              << "command operates on /etc/coop/agent.conf only and will not "
              << "apply session changes." << std::endl;
  }

  return performLocalRestart(bootType.level(), hostInfo);
>>>>>>> 36db926676 (NOS-23962: [fboss2] Replace ConfigSession's per-service accessors (6/6) (#3090))
}

void CmdConfigReload::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdConfigReload, CmdConfigReloadTraits>::run();

} // namespace facebook::fboss
