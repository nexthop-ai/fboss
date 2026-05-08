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

#include "fboss/cli/fboss2/commands/config/mac/aging_time/CmdConfigMacAgingTime.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/utils/PortMap.h" // NOLINT(misc-include-cleaner)

using namespace ::testing;

namespace facebook::fboss {

// Seed reflects production default: l2AgeTimerSeconds = 300
class CmdConfigMacAgingTimeTestFixture : public CmdConfigTestBase {
 public:
  CmdConfigMacAgingTimeTestFixture()
      : CmdConfigTestBase(
            "fboss_mac_aging_test_%%%%-%%%%-%%%%-%%%%",
            R"({
  "sw": {
    "switchSettings": {
      "l2AgeTimerSeconds": 300
    }
  }
})") {}

 protected:
  const std::string cmdPrefix_ = "config mac aging-time";
};

// ==============================================================================
// MacAgingTimeArg Validation Tests
// ==============================================================================

TEST_F(CmdConfigMacAgingTimeTestFixture, argValidation) {
  // Valid values
  EXPECT_EQ(MacAgingTimeArg({"300"}).getSeconds(), 300);
  EXPECT_EQ(MacAgingTimeArg({"1"}).getSeconds(), 1);
  EXPECT_EQ(MacAgingTimeArg({"1000000"}).getSeconds(), 1000000);

  // Invalid: empty
  EXPECT_THROW(MacAgingTimeArg({}), std::invalid_argument);

  // Invalid: too many args
  EXPECT_THROW(MacAgingTimeArg({"300", "600"}), std::invalid_argument);

  // Invalid: not an integer
  EXPECT_THROW(MacAgingTimeArg({"abc"}), std::invalid_argument);
  EXPECT_THROW(MacAgingTimeArg({"30.5"}), std::invalid_argument);

  // Invalid: zero or negative
  EXPECT_THROW(MacAgingTimeArg({"0"}), std::invalid_argument);
  EXPECT_THROW(MacAgingTimeArg({"-1"}), std::invalid_argument);
  EXPECT_THROW(MacAgingTimeArg({"-300"}), std::invalid_argument);
}

// ==============================================================================
// Command Execution Tests
// ==============================================================================

TEST_F(CmdConfigMacAgingTimeTestFixture, setAgingTime) {
  setupTestableConfigSession(cmdPrefix_, "600");
  CmdConfigMacAgingTime cmd;
  HostInfo hostInfo("testhost");
  MacAgingTimeArg arg({"600"});

  auto result = cmd.queryClient(hostInfo, arg);
  EXPECT_THAT(result, HasSubstr("600"));

  auto& config = ConfigSession::getInstance().getAgentConfig();
  EXPECT_EQ(*config.sw()->switchSettings()->l2AgeTimerSeconds(), 600);
}

TEST_F(CmdConfigMacAgingTimeTestFixture, setAgingTimeToOne) {
  setupTestableConfigSession(cmdPrefix_, "1");
  CmdConfigMacAgingTime cmd;
  HostInfo hostInfo("testhost");
  MacAgingTimeArg arg({"1"});

  auto result = cmd.queryClient(hostInfo, arg);
  EXPECT_THAT(result, HasSubstr("1"));

  auto& config = ConfigSession::getInstance().getAgentConfig();
  EXPECT_EQ(*config.sw()->switchSettings()->l2AgeTimerSeconds(), 1);
}

TEST_F(CmdConfigMacAgingTimeTestFixture, alreadySet) {
  // Seed has l2AgeTimerSeconds=300; setting to 300 is a no-op
  setupTestableConfigSession(cmdPrefix_, "300");
  CmdConfigMacAgingTime cmd;
  HostInfo hostInfo("testhost");
  MacAgingTimeArg arg({"300"});

  auto result = cmd.queryClient(hostInfo, arg);
  EXPECT_THAT(result, HasSubstr("already"));
}

} // namespace facebook::fboss
