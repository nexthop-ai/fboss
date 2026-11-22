// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "fboss/cli/fboss2/session/SystemdSequencer.h"

#include <fmt/format.h>
#include <folly/Range.h>
#include <folly/String.h>
#include <folly/logging/xlog.h>
#include <exception>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace {
constexpr std::string_view kSystemdServiceSuffix = ".service";
} // namespace

namespace facebook::fboss {

SystemdSequencer::SystemdSequencer()
    : systemd_(std::make_unique<SystemdInterface>()) {}

SystemdSequencer::SystemdSequencer(std::unique_ptr<SystemdInterface> systemd)
    : systemd_(std::move(systemd)) {}

void SystemdSequencer::restartAndWait(const std::string& unit) {
  systemd_->restartService(unit);
  systemd_->waitForServiceActive(unit);
}

void SystemdSequencer::stopAllThenStart(
    const std::vector<std::string>& units,
    const std::function<void()>& beforeStart) {
  bool beforeStartDone = false;
  try {
    const std::vector<std::string> stopOrder(units.rbegin(), units.rend());
    for (const auto& unit : stopOrder) {
      XLOG(DBG1) << "Stopping service: " << unit;
      systemd_->stopService(unit);
      systemd_->waitForServiceInactive(unit);
    }

    beforeStart();
    beforeStartDone = true;

    for (const auto& unit : units) {
      XLOG(DBG1) << "Starting service: " << unit;
      systemd_->startService(unit);
      systemd_->waitForServiceActive(unit);
    }
  } catch (const std::exception& ex) {
    // systemd does not restart a unit we stopped explicitly, so propagating
    // straight out of here would leave the box with none of these services
    // and nothing to recover them. Best effort: start everything back up
    // first.
    XLOG(ERR) << "Restart sequence failed: " << ex.what()
              << ". Attempting to start all services back up";
    if (!beforeStartDone) {
      // The pre-start step may have been left half done (e.g. only some
      // coldboot markers written).
      XLOG(ERR)
          << "The pre-start step did not complete, so the services below may "
          << "not come up with the requested boot type. Verify the boot type "
          << "before relying on this switch.";
    }
    for (const auto& unit : units) {
      try {
        systemd_->startService(unit);
        systemd_->waitForServiceActive(unit);
      } catch (const std::exception& recoveryEx) {
        XLOG(ERR) << "Failed to bring " << unit
                  << " back up while recovering: " << recoveryEx.what();
      }
    }
    throw;
  }
}

std::string SystemdSequencer::resolveUnit(
    const std::string& classic,
    const std::string& netosPattern) const {
  if (!systemd_
           ->getMatchingServices(
               fmt::format("{}{}", classic, kSystemdServiceSuffix))
           .empty()) {
    return classic;
  }

  auto matches = systemd_->getMatchingServices(
      fmt::format("{}{}", netosPattern, kSystemdServiceSuffix));
  if (matches.size() > 1) {
    throw std::runtime_error(
        fmt::format(
            "Found multiple systemd services matching {}: {}",
            netosPattern,
            folly::join(", ", matches)));
  }
  if (matches.size() == 1) {
    auto resolved = std::move(matches.front());
    if (folly::StringPiece(resolved).endsWith(kSystemdServiceSuffix)) {
      resolved.resize(resolved.size() - kSystemdServiceSuffix.size());
    }
    return resolved;
  }
  throw std::runtime_error(
      fmt::format(
          "No systemd service found for {} and {}", classic, netosPattern));
}

} // namespace facebook::fboss
