// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "fboss/cli/fboss2/session/AgentServiceController.h"

#include <fmt/format.h>
#include <folly/Conv.h>
#include <folly/String.h>
#include <folly/logging/xlog.h>
#include <algorithm>
#include <chrono>
#include <exception>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>
#include "fboss/agent/AgentDirectoryUtil.h"
#include "fboss/agent/SwitchInfoUtils.h"
#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrl.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrlAsyncClient.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/BgpServiceController.h"
#include "fboss/cli/fboss2/session/SystemdInterface.h"
#include "fboss/cli/fboss2/session/SystemdSequencer.h"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/lib/CommonFileUtils.h"

namespace {
constexpr std::string_view kWedgeAgent = "wedge_agent";
constexpr std::string_view kSwAgent = "fboss_sw_agent";
constexpr std::string_view kHwAgentPrefix = "fboss_hw_agent@";
constexpr std::string_view kOpenr = "openr";
constexpr std::string_view kBgpdBb = "bgpd-bb";
constexpr std::string_view kNetosSwAgent = "netos.service.fboss_sw_agent";
constexpr std::string_view kNetosHwAgentPrefix =
    "netos.service.fboss_wedge_agent_";
constexpr std::string_view kSystemdServiceSuffix = ".service";

// Whether a systemd unit is the sw_agent, under its classic or NetOS name.
bool isSwAgentUnit(std::string_view service) {
  return service == kSwAgent || service == kNetosSwAgent;
}

// The switch index of a hw_agent unit, under its classic
// (fboss_hw_agent@<N>) or NetOS (netos.service.fboss_wedge_agent_<vendor>_<N>)
// name; nullopt for any other unit.
std::optional<int> hwAgentSwitchIndex(std::string_view service) {
  if (service.starts_with(kHwAgentPrefix)) {
    return folly::to<int>(service.substr(kHwAgentPrefix.size()));
  }
  if (service.starts_with(kNetosHwAgentPrefix)) {
    return folly::to<int>(service.substr(service.rfind('_') + 1));
  }
  return std::nullopt;
}
} // namespace

namespace facebook::fboss {

AgentServiceController::AgentServiceController(
    const cfg::AgentConfig& agentConfig) {
  const auto& args = *agentConfig.defaultCommandLineArgs();
  // Parse multi_switch from the on-disk config rather than calling
  // utils::isMultiSwitchEnabled(hostInfo), so this works independently of
  // the agent's state without requiring a live thrift connection.
  multiSwitch_ =
      args.count("multi_switch") && args.at("multi_switch") == "true";
  for (const auto& [_, info] : getSwitchInfoFromConfig(&(*agentConfig.sw()))) {
    switchIndexes_.push_back(*info.switchIndex());
  }
  std::sort(switchIndexes_.begin(), switchIndexes_.end());
}

AgentServiceController::AgentServiceController(
    std::vector<int> switchIndexes,
    bool multiSwitch)
    : switchIndexes_(std::move(switchIndexes)), multiSwitch_(multiSwitch) {}

AgentServiceController::AgentServiceController(
    std::vector<int> switchIndexes,
    bool multiSwitch,
    std::unique_ptr<SystemdInterface> systemd,
    AgentDirectoryUtil dirUtil)
    : sequencer_(std::move(systemd)),
      dirUtil_(std::move(dirUtil)),
      switchIndexes_(std::move(switchIndexes)),
      multiSwitch_(multiSwitch) {}

AgentServiceController::Mode AgentServiceController::detectFromSystemd(
    SystemdInterface& systemd) {
  std::vector<int> switchIndexes;
  // --all in getMatchingServices() includes inactive/failed units, which is
  // what we need here since the agent is down.
  for (const auto& unit : systemd.getMatchingServices(
           fmt::format("{}*{}", kHwAgentPrefix, kSystemdServiceSuffix))) {
    // "fboss_hw_agent@0.service" -> 0
    std::string instance = unit.substr(kHwAgentPrefix.size());
    auto dot = instance.find('.');
    if (dot != std::string::npos) {
      instance.erase(dot);
    }
    auto idx = folly::tryTo<int>(instance);
    if (idx.hasValue()) {
      switchIndexes.push_back(*idx);
    } else {
      XLOG(WARN) << "Ignoring systemd unit with non-numeric instance: " << unit;
    }
  }
  std::sort(switchIndexes.begin(), switchIndexes.end());

  bool multiSwitch = !switchIndexes.empty();
  if (!multiSwitch) {
    if (systemd.isServiceEnabled(std::string(kSwAgent))) {
      throw std::runtime_error(
          fmt::format(
              "{} is enabled but systemd knows no {}<N> unit; cannot "
              "determine which hw_agent instances to manage while the agent "
              "is down",
              kSwAgent,
              kHwAgentPrefix));
    }
    if (!systemd.isServiceEnabled(std::string(kWedgeAgent))) {
      throw std::runtime_error(
          fmt::format(
              "Neither {} nor {} is known to systemd; cannot determine the "
              "agent mode while the agent is down",
              kSwAgent,
              kWedgeAgent));
    }
  }
  XLOG(INFO) << "Agent mode detected via systemd: "
             << (multiSwitch ? fmt::format(
                                   "split ({} hw_agent instance(s))",
                                   switchIndexes.size())
                             : "monolithic");

  return {std::move(switchIndexes), multiSwitch};
}

bool AgentServiceController::isSplitMode() const {
  return multiSwitch_;
}

std::string AgentServiceController::getColdbootFileForService(
    const std::string& service) const {
  if (isSwAgentUnit(service)) {
    return dirUtil_.getSwColdBootOnceFile();
  }
  if (const auto switchIndex = hwAgentSwitchIndex(service)) {
    return dirUtil_.getHwColdBootOnceFile(*switchIndex);
  }
  if (service == kWedgeAgent) {
    return dirUtil_.getColdBootOnceFile();
  }
  throw std::runtime_error(
      fmt::format("Unknown service type for coldboot: {}", service));
}

std::optional<std::string> AgentServiceController::getCanWarmBootFileForService(
    const std::string& service) const {
  if (isSwAgentUnit(service) || service == kWedgeAgent) {
    return dirUtil_.getSwSwitchCanWarmBootFile();
  }
  if (const auto switchIndex = hwAgentSwitchIndex(service)) {
    return dirUtil_.getHwSwitchCanWarmBootFile(*switchIndex);
  }
  // bgpd and anything else outside the agent do not warm boot.
  return std::nullopt;
}

void AgentServiceController::createColdbootMarkerFile(
    const std::string& coldbootFile) {
  createDir(parentDirectoryTree(coldbootFile));
  touchFile(coldbootFile);
}

std::vector<std::string>
AgentServiceController::findServicesMissingWarmBootState(
    const std::vector<std::string>& services) const {
  std::vector<std::string> missing;
  for (const auto& service : services) {
    auto canWarmBootFile = getCanWarmBootFileForService(service);
    if (canWarmBootFile.has_value() && !checkFileExists(*canWarmBootFile)) {
      missing.push_back(service);
    }
  }
  return missing;
}

void AgentServiceController::logServicesMissingWarmBootState(
    const std::vector<std::string>& services) const {
  auto missing = findServicesMissingWarmBootState(services);
  if (!missing.empty()) {
    XLOG(ERR)
        << "No warm boot state was saved by: " << folly::join(", ", missing)
        << ". These services will cold boot on start. The usual cause is "
        << "systemd SIGKILLing them for exceeding TimeoutStopSec before their "
        << "graceful exit finished.";
  }
}

void AgentServiceController::performColdboot(
    const std::vector<std::string>& services) {
  auto markColdboot = [this, &services]() {
    for (const auto& service : services) {
      XLOG(DBG1) << "Marking coldboot for service: " << service;
      createColdbootMarkerFile(getColdbootFileForService(service));
    }
  };

  if (services.size() == 1) {
    // Nothing to order against, so keep the smaller restart window.
    markColdboot();
    sequencer_.restartAndWait(services[0]);
    return;
  }
  // Markers are written between the stop and start phases so a service's own
  // shutdown cannot clobber them.
  sequencer_.stopAllThenStart(services, markColdboot);
}

void AgentServiceController::performWarmboot(
    const std::vector<std::string>& services) {
  if (services.size() == 1) {
    // Nothing to order against, so keep the smaller restart window.
    sequencer_.restartAndWait(services[0]);
    return;
  }
  sequencer_.stopAllThenStart(services, [this, &services]() {
    logServicesMissingWarmBootState(services);
  });
}

std::vector<std::string> AgentServiceController::getServicesToRestart() const {
  if (!isSplitMode()) {
    XLOG(DBG1)
        << "Detected monolithic mode (multi-switch not enabled on running agent)";
    return {std::string(kWedgeAgent)};
  }
  XLOG(DBG1) << "Detected split mode (multi-switch enabled on running agent)";

  std::vector<std::string> services;
  services.reserve(switchIndexes_.size() + 1);
  for (const auto& switchIndex : switchIndexes_) {
    // Native HW-agent units include a platform-specific vendor component
    // (for example, brcm or csco). Discover it from systemd so this OSS code
    // does not duplicate or depend on NetOS vendor metadata.
    services.emplace_back(sequencer_.resolveUnit(
        fmt::format("{}{}", kHwAgentPrefix, switchIndex),
        fmt::format("{}*_{}", kNetosHwAgentPrefix, switchIndex)));
  }
  XLOG(DBG1) << "Found " << services.size() << " hw_agent instances";

  // sw_agent goes last: it is started last and stopped first. Stopping a
  // hw_agent while the sw_agent is still up looks to the sw_agent like a
  // hw_agent crash: HwSwitchConnectionStatusTable::disconnected() writes
  // sw_cold_boot_once and hw_cold_boot_once_<idx> markers and forces both
  // sides cold on the way back up.
  services.emplace_back(sequencer_.resolveUnit(
      std::string(kSwAgent), std::string(kNetosSwAgent)));
  return services;
}

std::vector<std::string> AgentServiceController::reloadConfig(
    const HostInfo& hostInfo) {
  if (!agentReachable_) {
    // A hitless reload needs a live agent. The agent is down (typically
    // crash-looping on the config we are replacing), so bounce it: it
    // reads the new config from disk on start. Warm boot is requested but
    // a crashed agent left no warm boot state, so it will cold boot.
    XLOG(WARN) << "Agent is not reachable; applying the config with a service "
               << "restart instead of a hitless reload";
    auto services = restart(cli::ConfigActionLevel::SERVICE_RESTART);
    waitForAgentConfigured(hostInfo);
    return services;
  }
  std::string serviceName(isSplitMode() ? kSwAgent : kWedgeAgent);

  XLOG(DBG1) << "Reloading config for " << serviceName;

  auto client =
      utils::createClient<apache::thrift::Client<facebook::fboss::FbossCtrl>>(
          hostInfo);
  client->sync_reloadConfig();

  XLOG(DBG1) << "Config reloaded for " << serviceName;
  return {serviceName};
}

std::string AgentServiceController::restartTypeName(
    cli::ConfigActionLevel level) {
  switch (level) {
    case cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART:
      return "coldboot";
    case cli::ConfigActionLevel::SERVICE_RESTART:
      return "warmboot";
    case cli::ConfigActionLevel::HITLESS:
      return "reload";
  }
  return "restart";
}

// Same check as SwSwitch::isFullyConfigured().
bool AgentServiceController::isAgentConfigured(const HostInfo& hostInfo) {
  try {
    auto client =
        utils::createClient<apache::thrift::Client<FbossCtrl>>(hostInfo);
    auto runState = client->sync_getSwitchRunState();
    return runState >= SwitchRunState::CONFIGURED &&
        runState != SwitchRunState::EXITING;
  } catch (const std::exception&) {
    // Expected while the agent is still starting up.
    return false;
  }
}

void AgentServiceController::waitForAgentConfigured(
    const HostInfo& hostInfo,
    int maxWaitSeconds,
    int pollIntervalMs) {
  int waitedMs = 0;
  while (waitedMs < maxWaitSeconds * 1000) {
    if (isAgentConfigured(hostInfo)) {
      return;
    }
    // NOLINTNEXTLINE(facebook-hte-BadCall-sleep_for)
    std::this_thread::sleep_for(std::chrono::milliseconds(pollIntervalMs));
    waitedMs += pollIntervalMs;
  }
  throw std::runtime_error(
      fmt::format(
          "Agent did not become configured within {} seconds", maxWaitSeconds));
}

std::vector<std::string> AgentServiceController::restart(
    cli::ConfigActionLevel level) {
  auto services = getServicesToRestart();

  XLOG(DBG1) << "Restarting " << folly::join(", ", services) << " ("
             << restartTypeName(level) << ")...";

  if (level == cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART) {
    performColdboot(services);
    return services;
  }

  // BGP sessions time out while the agent is down. Add each active routing
  // unit to the end of the list: openr, then the BGP units. This gives the
  // warm boot order that Meta confirmed: stop BGP, openr, sw_agent,
  // hw_agent, and start in reverse.
  // A unit that is not active, including one that is still starting (state
  // activating), is not touched. The caller gets the agent units only.
  std::vector<std::string> allServices = services;
  std::vector<std::string> routingUnits;
  for (const auto& unit : {kOpenr, kBgpdUnit, kBgpdBb, kNetosBgpdUnit}) {
    if (sequencer_.isServiceActive(std::string(unit))) {
      routingUnits.emplace_back(unit);
    }
  }
  if (!routingUnits.empty()) {
    XLOG(DBG1) << "Stopping routing units around the warmboot, then "
               << "starting them again: " << folly::join(", ", routingUnits);
  }
  allServices.insert(
      allServices.end(), routingUnits.begin(), routingUnits.end());
  performWarmboot(allServices);
  return services;
}

} // namespace facebook::fboss
