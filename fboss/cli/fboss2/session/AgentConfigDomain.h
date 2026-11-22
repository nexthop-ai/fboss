// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <vector>
#include "fboss/agent/gen-cpp2/agent_config_types_fwd.h"
#include "fboss/agent/if/gen-cpp2/ctrl_types_fwd.h"
#include "fboss/cli/fboss2/session/TypedConfigDomain.h"

namespace facebook::fboss {

class AgentServiceController;
class SystemdInterface;

class AgentConfigDomain : public TypedConfigDomain<cfg::AgentConfig> {
 public:
  AgentConfigDomain(
      const std::string& sessionConfigDir,
      const std::string& systemConfigDir);
  // Out of line: the controller type is only forward-declared here.
  ~AgentConfigDomain() override;

  std::string queryCurrentPath(const HostInfo& hostInfo) const override;
  bool requiresConfig() const override {
    return true;
  }
  void prepare(cli::ConfigActionLevel level, const HostInfo& hostInfo) override;
  // A restart also waits until the agent can take config commands again.
  std::vector<std::string> apply(
      cli::ConfigActionLevel level,
      const HostInfo& hostInfo) override;
  std::string actionName(cli::ConfigActionLevel level) const override;

 protected:
  // Accepts an AgentConfig, or a bare SwitchConfig as its "sw".
  cfg::AgentConfig parse(std::string_view json) const override;

  // Builds the controller from the running agent's multi-switch state. If
  // the agent cannot be reached and hostInfo is the local host, falls back to
  // what systemd knows, so a commit or rollback still works while the agent
  // is crash-looping on a bad config. Throws for an unreachable remote agent,
  // since systemd cannot be driven remotely.
  virtual std::unique_ptr<AgentServiceController> makeController(
      const HostInfo& hostInfo) const;

  // The controller for an agent that cannot be reached over thrift.
  virtual std::unique_ptr<AgentServiceController> makeOfflineController(
      std::unique_ptr<SystemdInterface> systemd) const;

  virtual MultiSwitchRunState queryMultiSwitchRunState(
      const HostInfo& hostInfo) const;

  virtual std::unique_ptr<SystemdInterface> makeSystemdInterface() const;

  std::unique_ptr<AgentServiceController> controller_;
};

} // namespace facebook::fboss
