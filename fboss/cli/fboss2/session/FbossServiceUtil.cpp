/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/session/FbossServiceUtil.h"

#include <fmt/format.h>
#include <folly/String.h>
#include <folly/Subprocess.h>
#include <glog/logging.h>
#include <cerrno>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include "fboss/agent/AgentDirectoryUtil.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrl.h"
#include "fboss/cli/fboss2/session/SystemdInterface.h"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace fs = std::filesystem;

namespace facebook::fboss {

FbossServiceUtil::FbossServiceUtil(
    std::map<int64_t, cfg::SwitchInfo> switchInfoMap,
    bool multiSwitch)
    : systemd_(std::make_unique<SystemdInterface>()),
      switchInfoMap_(std::move(switchInfoMap)),
      multiSwitch_(multiSwitch) {}

FbossServiceUtil::FbossServiceUtil(
    std::map<int64_t, cfg::SwitchInfo> switchInfoMap,
    bool multiSwitch,
    std::unique_ptr<SystemdInterface> systemd)
    : systemd_(std::move(systemd)),
      switchInfoMap_(std::move(switchInfoMap)),
      multiSwitch_(multiSwitch) {}

std::string FbossServiceUtil::getServiceName(cli::ServiceType service) {
  switch (service) {
    case cli::ServiceType::AGENT:
      return "wedge_agent";
  }
  throw std::runtime_error("Unknown service type");
}

bool FbossServiceUtil::isSplitMode() const {
  return multiSwitch_;
}

std::string FbossServiceUtil::getColdbootFileForService(
    const std::string& service) {
  AgentDirectoryUtil dirUtil;

  if (service == "fboss_sw_agent") {
    return dirUtil.getSwColdBootOnceFile();
  } else if (service.find("fboss_hw_agent@") == 0) {
    std::string indexStr = service.substr(strlen("fboss_hw_agent@"));
    int switchIndex = folly::to<int>(indexStr);
    return dirUtil.getHwColdBootOnceFile(switchIndex);
  } else if (service == "wedge_agent") {
    return dirUtil.getColdBootOnceFile();
  } else {
    throw std::runtime_error(
        fmt::format("Unknown service type for coldboot: {}", service));
  }
}

void FbossServiceUtil::createColdbootMarkerFile(
    const std::string& coldbootFile) {
  fs::path filePath(coldbootFile);
  std::error_code ec;
  fs::create_directories(filePath.parent_path(), ec);
  if (ec) {
    throw std::runtime_error(
        fmt::format(
            "Failed to create directory for coldboot file {}: {}",
            coldbootFile,
            ec.message()));
  }

  std::ofstream touchFile(coldbootFile);
  if (!touchFile.good()) {
    int savedErrno = errno;
    if (savedErrno == EACCES || savedErrno == EPERM) {
      if (getuid() == 0) {
        // Already root - permission error is unexpected, don't attempt sudo
        throw std::runtime_error(
            fmt::format(
                "Failed to create coldboot file {} (permission denied, running as root)",
                coldbootFile));
      }
      try {
        folly::Subprocess touchProc(
            {"/usr/bin/sudo", "/usr/bin/touch", coldbootFile});
        touchProc.waitChecked();
      } catch (const std::exception& ex) {
        throw std::runtime_error(
            fmt::format(
                "Failed to create coldboot file {} (permission denied, sudo touch also failed): {}",
                coldbootFile,
                ex.what()));
      }
    } else {
      throw std::runtime_error(
          fmt::format(
              "Failed to create coldboot file {}: {}",
              coldbootFile,
              folly::errnoStr(savedErrno)));
    }
  } else {
    touchFile.close();
  }

  if (!fs::exists(coldbootFile)) {
    throw std::runtime_error(
        fmt::format(
            "Failed to create coldboot file {}: file does not exist after creation",
            coldbootFile));
  }
}

void FbossServiceUtil::performRestartAndWait(const std::string& service) {
  systemd_->restartService(service);
  systemd_->waitForServiceActive(service);
}

void FbossServiceUtil::performColdboot(
    const std::vector<std::string>& services) {
  for (const auto& service : services) {
    LOG(INFO) << "Performing coldboot for service: " << service;
    createColdbootMarkerFile(getColdbootFileForService(service));
    performRestartAndWait(service);
    LOG(INFO) << "Coldboot completed for service: " << service;
  }
}

void FbossServiceUtil::performWarmboot(
    const std::vector<std::string>& services) {
  for (const auto& service : services) {
    LOG(INFO) << "Performing warmboot for service: " << service;
    performRestartAndWait(service);
    LOG(INFO) << "Warmboot completed for service: " << service;
  }
}

std::vector<std::string> FbossServiceUtil::getServicesToRestart(
    cli::ServiceType service) const {
  std::vector<std::string> services;

  if (isSplitMode()) {
    LOG(INFO)
        << "Detected split mode (multi_switch flag is set in agent config)";

    // Add hw_agent instances first (hw before sw ordering)
    for (const auto& [switchId, switchInfo] : switchInfoMap_) {
      if (switchInfo.switchIndex().has_value()) {
        services.emplace_back(
            fmt::format("fboss_hw_agent@{}", *switchInfo.switchIndex()));
      }
    }
    LOG(INFO) << "Found " << services.size() << " hw_agent instances";

    // Add sw_agent last so hw_agent restarts first
    services.emplace_back("fboss_sw_agent");
  } else {
    LOG(INFO) << "Detected monolithic mode (multi_switch flag is not set)";
    services.emplace_back(getServiceName(service));
  }

  return services;
}

std::vector<std::string> FbossServiceUtil::reloadConfig(
    cli::ServiceType service,
    const HostInfo& hostInfo) {
  std::vector<std::string> reloadedServices;
  switch (service) {
    case cli::ServiceType::AGENT: {
      std::string serviceName =
          isSplitMode() ? "fboss_sw_agent" : getServiceName(service);

      LOG(INFO) << "Reloading config for " << serviceName;

      auto client = utils::createClient<
          apache::thrift::Client<facebook::fboss::FbossCtrl>>(hostInfo);
      client->sync_reloadConfig();

      LOG(INFO) << "Config reloaded for " << serviceName;
      reloadedServices.emplace_back(serviceName);
      break;
    }
      // TODO: Add cases for future services (e.g., BGP)
  }
  return reloadedServices;
}

std::vector<std::string> FbossServiceUtil::restartService(
    cli::ServiceType service,
    cli::ConfigActionLevel level) {
  std::string restartType = (level == cli::ConfigActionLevel::AGENT_COLDBOOT)
      ? "coldboot"
      : "warmboot";

  auto services = getServicesToRestart(service);

  LOG(INFO) << "Restarting agents (" << restartType << ")...";

  if (level == cli::ConfigActionLevel::AGENT_COLDBOOT) {
    performColdboot(services);
  } else {
    performWarmboot(services);
  }

  return services;
}

} // namespace facebook::fboss
