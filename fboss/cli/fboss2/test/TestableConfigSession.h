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

#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

<<<<<<< HEAD
=======
#include "fboss/agent/if/gen-cpp2/ctrl_types.h"
#include "fboss/cli/fboss2/session/AgentConfigDomain.h"
#include "fboss/cli/fboss2/session/AgentServiceController.h"
#include "fboss/cli/fboss2/session/BgpConfigDomain.h"
#include "fboss/cli/fboss2/session/BgpServiceController.h"
#include "fboss/cli/fboss2/session/ConfigDomainRegistry.h"
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/session/SystemdInterface.h"

namespace facebook::fboss {

// Real agent orchestration against a mock systemd; there is no agent to
// poll, so it always reports configured.
class NoAgentServiceController : public AgentServiceController {
 public:
  using AgentServiceController::AgentServiceController;
  bool isAgentConfigured(const HostInfo& /*hostInfo*/) override {
    return true;
  }
};

using SystemdFactory = std::function<std::unique_ptr<SystemdInterface>()>;

// Agent domain whose service controller the test chooses: an injected one, or
// one built from the overrides below instead of from a live agent.
class TestableAgentConfigDomain : public AgentConfigDomain {
 public:
  using AgentConfigDomain::AgentConfigDomain;

  void setController(std::unique_ptr<AgentServiceController> controller) {
    controller_ = std::move(controller);
  }

  bool agentUnreachable{false};
  bool multiSwitch{false};
  std::vector<int> switchIndexes{0};
  SystemdFactory systemdFactory;

 protected:
  std::unique_ptr<AgentServiceController> makeController(
      const HostInfo& hostInfo) const override {
    if (agentUnreachable) {
      // The real detection runs: its thrift probe throws and the systemd
      // fallback is served by systemdFactory.
      return AgentConfigDomain::makeController(hostInfo);
    }
    if (systemdFactory) {
      return std::make_unique<NoAgentServiceController>(
          switchIndexes, multiSwitch, systemdFactory());
    }
    return std::make_unique<AgentServiceController>(switchIndexes, multiSwitch);
  }

  std::unique_ptr<AgentServiceController> makeOfflineController(
      std::unique_ptr<SystemdInterface> systemd) const override {
    return AgentServiceController::fromSystemd<NoAgentServiceController>(
        std::move(systemd));
  }

  MultiSwitchRunState queryMultiSwitchRunState(
      const HostInfo& hostInfo) const override {
    if (agentUnreachable) {
      throw std::runtime_error(
          "simulated: AsyncSocketException: connect failed, errno = 111 "
          "(Connection refused)");
    }
    return AgentConfigDomain::queryMultiSwitchRunState(hostInfo);
  }

  std::unique_ptr<SystemdInterface> makeSystemdInterface() const override {
    if (systemdFactory) {
      return systemdFactory();
    }
    return AgentConfigDomain::makeSystemdInterface();
  }
};

class TestableBgpConfigDomain : public BgpConfigDomain {
 public:
  using BgpConfigDomain::BgpConfigDomain;

  SystemdFactory systemdFactory;

 protected:
  std::unique_ptr<RestartOnlyServiceController> makeController()
      const override {
    if (systemdFactory) {
      return std::make_unique<BgpServiceController>(systemdFactory());
    }
    return BgpConfigDomain::makeController();
  }
};

// Test-only derived class that exposes the protected constructor and methods
// This allows tests to inject custom paths and control the singleton instance
class TestableConfigSession : public ConfigSession {
 public:
  using ConfigPathResolver =
      std::function<std::string(cli::ServiceType service)>;

  TestableConfigSession(
      const std::string& sessionConfigDir,
      const std::string& systemConfigDir,
      SessionInit init = SessionInit::CreateIfAbsent)
      : TestableConfigSession(
            makeDomains(sessionConfigDir, systemConfigDir),
            sessionConfigDir,
            systemConfigDir,
            init) {}

  // Constructor with a mock agent controller. Does not initialize the session.
  TestableConfigSession(
      const std::string& sessionConfigDir,
      const std::string& systemConfigDir,
      std::unique_ptr<AgentServiceController> agentController)
      : TestableConfigSession(
            makeDomains(sessionConfigDir, systemConfigDir),
            sessionConfigDir,
            systemConfigDir) {
    agentDomain_->setController(std::move(agentController));
  }

  // Expose protected setInstance() for testing
  using ConfigSession::setInstance;

  // Expose protected applyServiceActions() for testing
  using ConfigSession::applyServiceActions;

  void setMultiSwitchOverride(
      bool multiSwitch,
      std::vector<int> switchIndexes = {0}) {
    agentDomain_->multiSwitch = multiSwitch;
    agentDomain_->switchIndexes = std::move(switchIndexes);
  }

  void setMockSystemdFactory(SystemdFactory factory) {
    agentDomain_->systemdFactory = factory;
    bgpDomain_->systemdFactory = std::move(factory);
  }

  void setConfigPathResolver(ConfigPathResolver resolver) {
    configPathResolver_ = std::move(resolver);
  }

<<<<<<< HEAD
  void ensureFbossServiceUtil(
      const HostInfo& /*hostInfo*/,
      bool /*needsAgentState*/) override {
    if (!fbossServiceUtil_) {
      if (mockSystemdFactory_) {
        fbossServiceUtil_ = std::make_unique<NoAgentServiceUtil>(
            switchIndexesOverride_,
            multiSwitchOverride_,
            mockSystemdFactory_());
      } else {
        fbossServiceUtil_ = std::make_unique<FbossServiceUtil>(
            switchIndexesOverride_, multiSwitchOverride_);
      }
    }
=======
  // Simulate an agent that is down.
  void setAgentUnreachable(bool unreachable) {
    agentDomain_->agentUnreachable = unreachable;
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
  }

  // Set the command line to return from readCommandLineFromProc().
  // This allows tests to simulate CLI commands without /proc/self/cmdline.
  void setCommandLine(const std::string& commandLine) {
    commandLine_ = commandLine;
  }

  // Override to return the mock command line set by setCommandLine().
  std::string readCommandLineFromProc() const override {
    return commandLine_;
  }

  std::string queryLocalServiceConfigPath(
      cli::ServiceType service) const override {
    if (configPathResolver_) {
      return configPathResolver_(service);
    }
    switch (service) {
      case cli::ServiceType::AGENT:
        return systemConfigDir_ + "/agent.conf";
      case cli::ServiceType::BGP:
        return systemConfigDir_ + "/bgpcpp.conf";
    }
    throw std::runtime_error("Unknown service type");
  }

 private:
  struct Domains {
    ConfigDomainRegistry registry;
    TestableAgentConfigDomain* agent;
    TestableBgpConfigDomain* bgp;
  };

  static Domains makeDomains(
      const std::string& sessionConfigDir,
      const std::string& systemConfigDir) {
    auto agent = std::make_unique<TestableAgentConfigDomain>(
        sessionConfigDir, systemConfigDir);
    auto bgp = std::make_unique<TestableBgpConfigDomain>(
        sessionConfigDir, systemConfigDir);
    Domains domains{{}, agent.get(), bgp.get()};
    domains.registry.add(std::move(agent));
    domains.registry.add(std::move(bgp));
    return domains;
  }

  TestableConfigSession(
      Domains domains,
      std::string sessionConfigDir,
      std::string systemConfigDir,
      SessionInit init)
      : ConfigSession(
            std::move(sessionConfigDir),
            systemConfigDir,
            std::move(domains.registry),
            init),
        systemConfigDir_(std::move(systemConfigDir)),
        agentDomain_(domains.agent),
        bgpDomain_(domains.bgp) {}

  // Does not initialize the session.
  TestableConfigSession(
      Domains domains,
      std::string sessionConfigDir,
      std::string systemConfigDir)
      : ConfigSession(
            std::move(sessionConfigDir),
            systemConfigDir,
            std::move(domains.registry)),
        systemConfigDir_(std::move(systemConfigDir)),
        agentDomain_(domains.agent),
        bgpDomain_(domains.bgp) {}

  std::string systemConfigDir_;
  ConfigPathResolver configPathResolver_;
  std::string commandLine_;
<<<<<<< HEAD
  bool multiSwitchOverride_{false};
  std::vector<int> switchIndexesOverride_{0};
  std::function<std::unique_ptr<SystemdInterface>()> mockSystemdFactory_;
=======
  TestableAgentConfigDomain* agentDomain_;
  TestableBgpConfigDomain* bgpDomain_;
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
};

} // namespace facebook::fboss
