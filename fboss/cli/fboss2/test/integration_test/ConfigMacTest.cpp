// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end test for:
 *   fboss2-dev config mac aging-time <seconds>
 *
 * Reads the current l2AgeTimerSeconds, changes it, verifies the new value
 * round-trips through the agent's running config, then restores the original.
 * The change is HITLESS so no agent restart is needed between steps.
 */

#include <folly/json/dynamic.h>
#include <folly/logging/xlog.h>
#include <gtest/gtest.h>
#include <string>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

namespace {
constexpr int kDefaultAgingSeconds = 300;
} // namespace

class ConfigMacTest : public Fboss2IntegrationTest {
 protected:
  int getAgingTime() const {
    auto config = getRunningConfig();
    const auto& sw = config["sw"];
    if (!sw.count("switchSettings")) {
      return kDefaultAgingSeconds;
    }
    const auto& settings = sw["switchSettings"];
    if (!settings.count("l2AgeTimerSeconds")) {
      return kDefaultAgingSeconds;
    }
    return settings["l2AgeTimerSeconds"].asInt();
  }

  void setAgingTime(int seconds) {
    auto result =
        runCli({"config", "mac", "aging-time", std::to_string(seconds)});
    ASSERT_EQ(result.exitCode, 0) << "aging-time CLI failed: " << result.stderr;
    commitConfig();
  }
};

TEST_F(ConfigMacTest, SetAndRestoreAgingTime) {
  XLOG(INFO) << "[Step 1] Reading current MAC aging time...";
  int originalSeconds = getAgingTime();
  XLOG(INFO) << "  Current: " << originalSeconds << "s";

  // Pick a target value different from current
  int newSeconds = (originalSeconds == 600) ? 300 : 600;

  XLOG(INFO) << "[Step 2] Setting aging-time to " << newSeconds << "s...";
  setAgingTime(newSeconds);
  EXPECT_EQ(getAgingTime(), newSeconds);

  XLOG(INFO) << "[Step 3] Restoring original aging-time " << originalSeconds
             << "s...";
  setAgingTime(originalSeconds);
  EXPECT_EQ(getAgingTime(), originalSeconds);

  XLOG(INFO) << "TEST PASSED";
}
