/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include "fboss/cli/fboss2/test/TestableConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/test/config/MockSystemdInterface.h"

using ::testing::_; // NOLINT(bugprone-reserved-identifier)
using ::testing::Contains;
using ::testing::InSequence;
using ::testing::Return;
using ::testing::Throw;

namespace facebook::fboss {

class ConfigSessionSystemdTest : public CmdConfigTestBase {
 public:
  ConfigSessionSystemdTest()
      : CmdConfigTestBase("systemd_test_%%%%-%%%%-%%%%", kMonoConfig) {}

 protected:
  // Write a config to the system config path to change mode for a test
  void writeSystemConfig(const std::string& content) {
    createTestConfig(getCliConfigDir() / "agent.conf", content);
  }

  // Monolithic config: no multi_switch flag (default)
  static constexpr auto kMonoConfig = R"({
  "sw": {
    "switchSettings": {
      "switchIdToSwitchInfo": {
        "0": {
          "switchType": 0,
          "asicType": 13,
          "switchIndex": 0
        }
      }
    }
  }
})";

  // Split mode config: multi_switch flag set in defaultCommandLineArgs
  static constexpr auto kSplitConfig = R"({
  "defaultCommandLineArgs": {
    "multi_switch": "true"
  },
  "sw": {
    "switchSettings": {
      "switchIdToSwitchInfo": {
        "0": {
          "switchType": 0,
          "asicType": 13,
          "switchIndex": 0
        }
      }
    }
  }
})";
};

// Test: isSplitMode() returns true when multi_switch flag is set in agent conf
TEST_F(ConfigSessionSystemdTest, IsSplitMode_ReturnsTrueWhenMultiSwitchSet) {
  writeSystemConfig(kSplitConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  EXPECT_TRUE(session.isSplitMode());
}

// Test: isSplitMode() returns false when multi_switch flag is not set
TEST_F(
    ConfigSessionSystemdTest,
    IsSplitMode_ReturnsFalseWhenMultiSwitchNotSet) {
  writeSystemConfig(kMonoConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  EXPECT_FALSE(session.isSplitMode());
}

// Test: isSplitMode() returns false when defaultCommandLineArgs has
// multi_switch set to something other than "true"
TEST_F(ConfigSessionSystemdTest, IsSplitMode_ReturnsFalseWhenMultiSwitchFalse) {
  static constexpr auto kFalseMultiSwitchConfig = R"({
  "defaultCommandLineArgs": {
    "multi_switch": "false"
  },
  "sw": {
    "switchSettings": {
      "switchIdToSwitchInfo": {
        "0": {
          "switchType": 0,
          "asicType": 13,
          "switchIndex": 0
        }
      }
    }
  }
})";
  writeSystemConfig(kFalseMultiSwitchConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  EXPECT_FALSE(session.isSplitMode());
}

// Test: Monolithic mode warmboot restart
TEST_F(ConfigSessionSystemdTest, RestartService_MonolithicMode_Warmboot) {
  writeSystemConfig(kMonoConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  // Expect restart of wedge_agent
  EXPECT_CALL(*mockSystemd, restartService("wedge_agent")).Times(1);

  // Expect wait for service to become active
  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _)).Times(1);

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  auto services = session.restartService(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);

  // Verify returned service names
  EXPECT_EQ(services.size(), 1);
  EXPECT_EQ(services[0], "wedge_agent");
}

// Test: Monolithic mode coldboot restart
TEST_F(ConfigSessionSystemdTest, RestartService_MonolithicMode_Coldboot) {
  writeSystemConfig(kMonoConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  // Expect stop, then start (not restart) for coldboot
  InSequence seq;
  EXPECT_CALL(*mockSystemd, stopService("wedge_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, startService("wedge_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _)).Times(1);

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  auto services = session.restartService(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_COLDBOOT);

  EXPECT_EQ(services.size(), 1);
  EXPECT_EQ(services[0], "wedge_agent");
}

// Test: Split mode warmboot restart (single hw_agent)
TEST_F(
    ConfigSessionSystemdTest,
    RestartService_SplitMode_Warmboot_SingleHwAgent) {
  writeSystemConfig(kSplitConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  // Expect restart of sw_agent and hw_agent@0
  EXPECT_CALL(*mockSystemd, restartService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, restartService("fboss_hw_agent@0")).Times(1);

  // Expect wait for both services
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  auto services = session.restartService(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT);

  // Verify returned service names
  EXPECT_EQ(services.size(), 2);
  EXPECT_THAT(services, Contains("fboss_sw_agent"));
  EXPECT_THAT(services, Contains("fboss_hw_agent@0"));
}

// Test: Split mode coldboot restart (single hw_agent)
TEST_F(
    ConfigSessionSystemdTest,
    RestartService_SplitMode_Coldboot_SingleHwAgent) {
  writeSystemConfig(kSplitConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  // Expect sequential coldboot: stop -> start -> wait for each service
  InSequence seq;
  // First service: fboss_sw_agent
  EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);
  // Second service: fboss_hw_agent@0
  EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0")).Times(1);
  EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  auto services = session.restartService(
      cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_COLDBOOT);

  EXPECT_EQ(services.size(), 2);
  EXPECT_THAT(services, Contains("fboss_sw_agent"));
  EXPECT_THAT(services, Contains("fboss_hw_agent@0"));
}

// Test: Service restart failure is propagated
TEST_F(ConfigSessionSystemdTest, RestartService_PropagatesFailure) {
  writeSystemConfig(kMonoConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, restartService("wedge_agent"))
      .WillOnce(Throw(std::runtime_error("Failed to restart wedge_agent")));

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  EXPECT_THROW(
      session.restartService(
          cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT),
      std::runtime_error);
}

// Test: Service fails to become active within timeout
TEST_F(ConfigSessionSystemdTest, RestartService_ServiceFailsToStart) {
  writeSystemConfig(kMonoConfig);

  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, restartService("wedge_agent")).Times(1);

  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _))
      .WillOnce(Throw(
          std::runtime_error(
              "wedge_agent did not become active within 60 seconds")));

  TestableConfigSession session(
      (getTestHomeDir() / ".fboss2").string(),
      (getTestEtcDir() / "coop").string(),
      std::move(mockSystemd));

  EXPECT_THROW(
      session.restartService(
          cli::ServiceType::AGENT, cli::ConfigActionLevel::AGENT_WARMBOOT),
      std::runtime_error);
}

} // namespace facebook::fboss
