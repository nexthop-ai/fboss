// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include "fboss/agent/AgentDirectoryUtil.h"
#include "fboss/agent/SwAgentInitializer.h"

#include <atomic>

namespace facebook::fboss {

class SwitchState;
class MultiSwitchThriftHandler;

class SplitSwSwitchInitializer : public SwSwitchInitializer {
 public:
  explicit SplitSwSwitchInitializer(SwSwitch* sw) : SwSwitchInitializer(sw) {}

 private:
  void initImpl(
      HwSwitchCallback* callback,
      const HwWriteBehavior& hwWriteBehavior = HwWriteBehavior::WRITE) override;
};

class SplitSwAgentInitializer : public SwAgentInitializer {
 public:
  SplitSwAgentInitializer();
  virtual ~SplitSwAgentInitializer() override {}

  std::vector<std::shared_ptr<apache::thrift::AsyncProcessorFactory>>
  getThrifthandlers() override;

  void handleExitSignal(bool gracefulExit) override;

  void stopAgent(bool setupWarmboot, bool gracefulExit) override;

 private:
  void exitForColdBoot();
  void exitForWarmBoot(bool gracefulExit);
  AgentDirectoryUtil agentDirectoryUtil_;
  MultiSwitchThriftHandler* multiSwitchThriftHandler_{nullptr};
  // Set by the first exit signal. handleExitSignal() returns (it no longer
  // terminates the process), so a second signal delivered while the shutdown
  // is draining would re-enter it after sw_ was released and initializer_
  // reset -- guard against that instead of dereferencing null.
  std::atomic<bool> exitSignalReceived_{false};
};

} // namespace facebook::fboss
