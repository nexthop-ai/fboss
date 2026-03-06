/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/session/CmdConfigSessionCommit.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/String.h>
#include <vector>
#include "fboss/cli/fboss2/session/ConfigSession.h"

namespace facebook::fboss {

CmdConfigSessionCommitTraits::RetType CmdConfigSessionCommit::queryClient(
    const HostInfo& hostInfo) {
  auto& session = ConfigSession::getInstance();

  if (!session.sessionExists()) {
    return "No config session exists. Make a config change first.";
  }

  auto result = session.commit(hostInfo);

  // Categorize services by action type
  std::vector<std::string> restartedServices;
  std::vector<std::string> reloadedServices;

  for (const auto& [service, level] : result.actions) {
    std::string serviceName = ConfigSession::getServiceName(service);
    switch (level) {
      case cli::ConfigActionLevel::AGENT_COLDBOOT:
        restartedServices.push_back(fmt::format("{} (coldboot)", serviceName));
        break;
      case cli::ConfigActionLevel::AGENT_WARMBOOT:
        restartedServices.push_back(fmt::format("{} (warmboot)", serviceName));
        break;
      case cli::ConfigActionLevel::HITLESS:
        reloadedServices.push_back(serviceName);
        break;
    }
  }

  // Build message based on what actions were taken
  std::string message;
  std::string shortSha = result.commitSha.substr(0, 7);
  if (restartedServices.empty() && reloadedServices.empty()) {
<<<<<<< HEAD
    message = fmt::format(
        "Config session committed successfully as {}.", result.commitSha);
||||||| 8908ebf139
    message = fmt::format(
        "Config session committed successfully as r{}.", result.revision);
=======
    message =
        fmt::format("Config session committed successfully as {}.", shortSha);
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
  } else if (restartedServices.empty()) {
    message = fmt::format(
        "Config session committed successfully as {} and config reloaded for {}.",
<<<<<<< HEAD
        result.commitSha,
||||||| 8908ebf139
        "Config session committed successfully as r{} and config reloaded for {}.",
        result.revision,
=======
        shortSha,
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
        folly::join(", ", reloadedServices));
  } else if (reloadedServices.empty()) {
    message = fmt::format(
        "Config session committed successfully as {} and {} restarted.",
<<<<<<< HEAD
        result.commitSha,
||||||| 8908ebf139
        "Config session committed successfully as r{} and {} restarted.",
        result.revision,
=======
        shortSha,
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
        folly::join(", ", restartedServices));
  } else {
    message = fmt::format(
        "Config session committed successfully as {}, {} restarted, and config reloaded for {}.",
<<<<<<< HEAD
        result.commitSha,
||||||| 8908ebf139
        "Config session committed successfully as r{}, {} restarted, and config reloaded for {}.",
        result.revision,
=======
        shortSha,
>>>>>>> c17655f13960093f57bb9baa2709891f330dd442
        folly::join(", ", restartedServices),
        folly::join(", ", reloadedServices));
  }

  return message;
}

void CmdConfigSessionCommit::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void
CmdHandler<CmdConfigSessionCommit, CmdConfigSessionCommitTraits>::run();

} // namespace facebook::fboss
