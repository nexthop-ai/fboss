// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <memory>
#include <string>
#include <utility>
#include <vector>

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
=======
#include "fboss/agent/AgentDirectoryUtil.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types_fwd.h"
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
#include "fboss/cli/fboss2/session/SystemdInterface.h"
#include "fboss/cli/fboss2/session/SystemdSequencer.h"

namespace facebook::fboss {

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
=======
namespace cfg {
class AgentConfig;
} // namespace cfg

class HostInfo;

>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
/**
 * Restarts and reloads the FBOSS agent.
 *
 * Encapsulates everything specific to the agent's deployment:
 * - Split mode (fboss_sw_agent + fboss_hw_agent@N) or monolithic (wedge_agent)
 * - Coldboot marker file creation
<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
 * - Correct restart ordering (hw_agent before sw_agent)
=======
 * - Correct restart ordering (stop sw_agent first, start hw_agent first)
 * - Stopping the routing daemons around a warm boot
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
 */
class AgentServiceController {
 public:
<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
=======
  // Construct from an AgentConfig: infers multi_switch mode and switch indices.
  explicit AgentServiceController(const cfg::AgentConfig& agentConfig);

>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
  // Production constructor: creates its own SystemdInterface.
  AgentServiceController(std::vector<int> switchIndexes, bool multiSwitch);

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
  // Test constructor: accepts an injected SystemdInterface mock.
  FbossServiceUtil(
      std::vector<int> switchIndexes,
      bool multiSwitch,
      std::unique_ptr<SystemdInterface> systemd);
=======
  // Test constructor: accepts an injected SystemdInterface mock, and
  // optionally an AgentDirectoryUtil rooted at a scratch directory so tests do
  // not read or write the real /dev/shm marker and warm boot flag files.
  AgentServiceController(
      std::vector<int> switchIndexes,
      bool multiSwitch,
      std::unique_ptr<SystemdInterface> systemd,
      AgentDirectoryUtil dirUtil = AgentDirectoryUtil());

  // Offline constructor for when the agent cannot be reached over thrift
  // (e.g. it is crash-looping on a bad config): derives the mode and the
  // hw_agent instances from what systemd knows instead of asking the agent.
  // Split mode if any fboss_hw_agent@<N> unit exists (or fboss_sw_agent is
  // enabled), monolithic if wedge_agent is enabled; throws if neither can be
  // established. The returned object treats the agent as unreachable, so
  // reloadConfig() applies changes with a restart instead of a thrift call.
  template <class C = AgentServiceController>
  static std::unique_ptr<C> fromSystemd(
      std::unique_ptr<SystemdInterface> systemd,
      AgentDirectoryUtil dirUtil = AgentDirectoryUtil()) {
    auto mode = detectFromSystemd(*systemd);
    auto controller = std::make_unique<C>(
        std::move(mode.switchIndexes),
        mode.multiSwitch,
        std::move(systemd),
        std::move(dirUtil));
    static_cast<AgentServiceController&>(*controller).agentReachable_ = false;
    return controller;
  }
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h

  virtual ~AgentServiceController() = default;

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
  // Restart services for the given service type and action level.
  // Returns the list of actual systemd service names that were restarted.
  virtual std::vector<std::string> restartService(
      cli::ServiceType service,
      cli::ConfigActionLevel level);
=======
  struct Mode {
    std::vector<int> switchIndexes;
    bool multiSwitch{false};
  };
  // What systemd knows about how the agent is deployed. Throws if neither
  // split nor monolithic mode can be established.
  static Mode detectFromSystemd(SystemdInterface& systemd);

  // Restarts the agent: a coldboot for DISRUPTIVE_SERVICE_RESTART, otherwise
  // a warmboot. Returns the agent units that were restarted. A routing unit
  // that is restarted around a warm boot is logged and is not in the list.
  virtual std::vector<std::string> restart(cli::ConfigActionLevel level);
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h

  // Waits until the agent at hostInfo can take config commands; systemd
  // reports it active well before that. Throws on timeout.
  void waitForAgentConfigured(
      const HostInfo& hostInfo,
      int maxWaitSeconds = 300,
      int pollIntervalMs = 1000);

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
  virtual bool isAgentConfigured(const HostInfo& hostInfo);

  // Reload config for a service without restart (for HITLESS changes).
  // Calls sync_reloadConfig() on the primary service (sw_agent in split mode,
  // wedge_agent in monolithic mode).
  // Returns the list of actual service names that were reloaded.
  virtual std::vector<std::string> reloadConfig(
      cli::ServiceType service,
      const HostInfo& hostInfo);

  // Returns true if running in split mode (multi_switch flag was set).
  virtual bool isSplitMode() const;

  // Returns the systemd service name for a given service type.
  static std::string getServiceName(cli::ServiceType service);

  // Human-readable restart kind for a (service, level) pair, e.g. the agent
  // restarts by "warmboot" or "coldboot", bgpd (no warmboot) by "restart".
  static std::string restartTypeName(
      cli::ServiceType service,
      cli::ConfigActionLevel level);

 private:
  std::unique_ptr<SystemdInterface> systemd_;
=======
  // Reload the config without a restart (for HITLESS changes).
  // Calls sync_reloadConfig() on the primary service (sw_agent in split mode,
  // wedge_agent in monolithic mode). If the agent was not reachable when this
  // object was built (see fromSystemd()), a hitless reload is impossible, so
  // this instead restarts the agent services (SERVICE_RESTART, i.e. a
  // warmboot), waits for the agent to be configured and returns those names.
  // Returns the list of actual service names that were reloaded.
  virtual std::vector<std::string> reloadConfig(const HostInfo& hostInfo);

  // "coldboot", "warmboot" or "reload".
  static std::string restartTypeName(cli::ConfigActionLevel level);

 protected:
  // One poll of waitForAgentConfigured(); virtual so tests can stand in for
  // the agent.
  virtual bool isAgentConfigured(const HostInfo& hostInfo);

  // Returns true if running in split mode (multi_switch flag was set).
  virtual bool isSplitMode() const;

  // Given services that have just been stopped, returns those that left no
  // warm boot state behind and will therefore cold boot on the next start.
  // The usual cause is systemd SIGKILLing a service for exceeding
  // TimeoutStopSec before its graceful exit finished. Units outside the
  // agent (e.g. bgpd) never warm boot and are never reported.
  std::vector<std::string> findServicesMissingWarmBootState(
      const std::vector<std::string>& services) const;

 private:
  SystemdSequencer sequencer_;
  AgentDirectoryUtil dirUtil_;
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
  std::vector<int> switchIndexes_;
  bool multiSwitch_;

<<<<<<< HEAD:fboss/cli/fboss2/session/FbossServiceUtil.h
  // Returns ordered list of services to restart (hw_agent first, sw_agent last)
  std::vector<std::string> getServicesToRestart(cli::ServiceType service) const;

  // Prefers classic unit names and falls back to the installed NetOS unit.
  std::string resolveSystemdServiceName(const std::string& service) const;

  // Shared per-service helper: restart and wait for active.
  void performRestartAndWait(const std::string& service);

  // Coldboot: create marker file, then restart and wait for each service.
=======
  // Returns services in start order (hw_agent first, sw_agent last). The stop
  // phase walks this list backwards.
  std::vector<std::string> getServicesToRestart() const;

  // Coldboot: bounce every service, creating the marker files in between the
  // stop and start phases.
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081)):fboss/cli/fboss2/session/AgentServiceController.h
  void performColdboot(const std::vector<std::string>& services);

  // Warmboot: restart and wait for each service (no marker file).
  void performWarmboot(const std::vector<std::string>& services);

  // Returns the coldboot marker file path for a given service name.
  static std::string getColdbootFileForService(const std::string& service);

  // Creates the coldboot marker file, handling permissions via sudo if needed.
  static void createColdbootMarkerFile(const std::string& coldbootFile);
};

} // namespace facebook::fboss
