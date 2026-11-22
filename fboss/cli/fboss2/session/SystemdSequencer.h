// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "fboss/cli/fboss2/session/SystemdInterface.h"

namespace facebook::fboss {

// Ordered restarts of systemd units. Knows nothing about which service a unit
// belongs to.
class SystemdSequencer {
 public:
  SystemdSequencer();
  explicit SystemdSequencer(std::unique_ptr<SystemdInterface> systemd);

  bool isServiceActive(const std::string& unit) const {
    return systemd_->isServiceActive(unit);
  }

  // Restarts one unit and waits until it is active.
  void restartAndWait(const std::string& unit);

  // Stops the units last to first, runs beforeStart, then starts them first
  // to last, waiting for each transition. On failure it tries to start every
  // unit again before rethrowing.
  void stopAllThenStart(
      const std::vector<std::string>& units,
      const std::function<void()>& beforeStart);

  // The classic unit name if that unit is installed, otherwise the one
  // installed unit matching netosPattern. Throws if neither exists or the
  // pattern matches several.
  std::string resolveUnit(
      const std::string& classic,
      const std::string& netosPattern) const;

 private:
  std::unique_ptr<SystemdInterface> systemd_;
};

} // namespace facebook::fboss
