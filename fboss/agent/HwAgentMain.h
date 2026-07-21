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
#include <atomic>
#include <memory>

#include <string>

#include "fboss/agent/CommonInit.h"
#include "fboss/agent/FbossInit.h"
#include "fboss/agent/HwAgent.h"

namespace facebook::fboss {

class SplitAgentThriftSyncer;

class SplitHwAgentSignalHandler : public SignalHandler {
 public:
  SplitHwAgentSignalHandler(
      folly::EventBase* eventBase,
      SignalHandler::StopServices stopServices,
      std::unique_ptr<HwAgent> hwAgent,
      SplitAgentThriftSyncer* syncer)
      : SignalHandler(eventBase, std::move(stopServices)),
        hwAgent_(std::move(hwAgent)),
        syncer_(syncer) {}

  void signalReceived(int /*signum*/) noexcept override;

 private:
  std::unique_ptr<HwAgent> hwAgent_;
  SplitAgentThriftSyncer* syncer_;
  // Set by the first exit signal. signalReceived() returns (it no longer
  // terminates the process), so a second signal delivered while the shutdown
  // is draining would re-enter it -- after gracefulExit() already tore down
  // the SAI switch (warm) or hwAgent_ was reset (cold). Guard against that
  // instead of re-driving the teardown.
  std::atomic<bool> exitSignalReceived_{false};
};

void setSDKVersionInfo();

std::string getSDKVersion();

int hwAgentMain(
    int argc,
    char** argv,
    uint32_t hwFeaturesDesired,
    PlatformInitFn initPlatformFn);

} // namespace facebook::fboss
