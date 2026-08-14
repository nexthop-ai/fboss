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
#include <stdexcept>
#include <string>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/delete/interface/queuing_policy/CmdDeleteInterfaceQueuingPolicy.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

using namespace ::testing;

namespace facebook::fboss {

// Seed config mirrors the portQueueConfigs shape a production agent.conf uses:
// a named queuing policy holding per-queue scheduling, with only some ports
// pointing at it. eth1/1/1 and eth1/2/1 name the policy, eth1/3/1 names none
// (so it already falls back to defaultPortQueues), and eth1/4/1 names a second
// policy that must be left alone.
class CmdDeleteInterfaceQueuingPolicyTestFixture : public CmdConfigTestBase {
 public:
  CmdDeleteInterfaceQueuingPolicyTestFixture()
      : CmdConfigTestBase(
            "fboss_delete_intf_queuing_policy_test_%%%%-%%%%-%%%%-%%%%",
            R"({
  "sw": {
    "ports": [
      {
        "logicalID": 1,
        "name": "eth1/1/1",
        "state": 2,
        "speed": 100000,
        "portQueueConfigName": "uplink"
      },
      {
        "logicalID": 2,
        "name": "eth1/2/1",
        "state": 2,
        "speed": 100000,
        "portQueueConfigName": "uplink"
      },
      {
        "logicalID": 3,
        "name": "eth1/3/1",
        "state": 2,
        "speed": 100000
      },
      {
        "logicalID": 4,
        "name": "eth1/4/1",
        "state": 2,
        "speed": 100000,
        "portQueueConfigName": "downlink"
      }
    ],
    "portQueueConfigs": {
      "uplink": [
        { "id": 0, "streamType": 0, "scheduling": 1, "weight": 10 },
        { "id": 7, "streamType": 0, "scheduling": 0 }
      ],
      "downlink": [
        { "id": 0, "streamType": 0, "scheduling": 1, "weight": 40 }
      ]
    }
  }
})") {}

 protected:
  const std::string cmdPrefix_ = "delete interface";

  // Current portQueueConfigName of a port, or nullopt when unset.
  std::optional<std::string> queuingPolicyOf(const std::string& portName) {
    auto& ports = *ConfigSession::getInstance().getAgentConfig().sw()->ports();
    for (const auto& port : ports) {
      if (port.name().has_value() && *port.name() == portName) {
        return port.portQueueConfigName().has_value()
            ? std::optional<std::string>(*port.portQueueConfigName())
            : std::nullopt;
      }
    }
    throw std::runtime_error("No such port in seed config: " + portName);
  }
};

TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, clearsSinglePort) {
  setupTestableConfigSession(cmdPrefix_, "eth1/1/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/1/1"});

  ASSERT_EQ(queuingPolicyOf("eth1/1/1"), "uplink");
  auto result = cmd.queryClient(localhost(), interfaces);

  EXPECT_THAT(result, HasSubstr("Deleted queuing-policy"));
  EXPECT_THAT(result, HasSubstr("eth1/1/1"));
  EXPECT_EQ(queuingPolicyOf("eth1/1/1"), std::nullopt);

  // Siblings untouched.
  EXPECT_EQ(queuingPolicyOf("eth1/2/1"), "uplink");
  EXPECT_EQ(queuingPolicyOf("eth1/4/1"), "downlink");
}

TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, clearsMultiplePorts) {
  setupTestableConfigSession(cmdPrefix_, "eth1/1/1,eth1/2/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/1/1", "eth1/2/1"});

  auto result = cmd.queryClient(localhost(), interfaces);

  EXPECT_THAT(result, HasSubstr("eth1/1/1"));
  EXPECT_THAT(result, HasSubstr("eth1/2/1"));
  EXPECT_EQ(queuingPolicyOf("eth1/1/1"), std::nullopt);
  EXPECT_EQ(queuingPolicyOf("eth1/2/1"), std::nullopt);
  EXPECT_EQ(queuingPolicyOf("eth1/4/1"), "downlink");
}

// The policy definition itself must survive; only the port's pointer is
// cleared. Deleting the definition is `delete qos queuing-policy`.
TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, leavesPolicyDefinition) {
  setupTestableConfigSession(cmdPrefix_, "eth1/1/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/1/1"});

  cmd.queryClient(localhost(), interfaces);

  auto& configs =
      *ConfigSession::getInstance().getAgentConfig().sw()->portQueueConfigs();
  EXPECT_NE(configs.find("uplink"), configs.end());
  EXPECT_NE(configs.find("downlink"), configs.end());
}

TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, noPolicySetIsANoOp) {
  setupTestableConfigSession(cmdPrefix_, "eth1/3/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/3/1"});

  auto result = cmd.queryClient(localhost(), interfaces);

  EXPECT_THAT(result, HasSubstr("No queuing-policy set"));
  EXPECT_EQ(queuingPolicyOf("eth1/3/1"), std::nullopt);
}

// Repeating the delete is safe and reports the no-op rather than throwing.
TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, secondDeleteIsANoOp) {
  setupTestableConfigSession(cmdPrefix_, "eth1/1/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/1/1"});

  EXPECT_THAT(
      cmd.queryClient(localhost(), interfaces),
      HasSubstr("Deleted queuing-policy"));
  EXPECT_THAT(
      cmd.queryClient(localhost(), interfaces), HasSubstr("No queuing-policy"));
}

// A mixed selection clears only the ports that had a policy, and names just
// those in the success message.
TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, mixedSelectionNamesCleared) {
  setupTestableConfigSession(cmdPrefix_, "eth1/1/1,eth1/3/1 queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({"eth1/1/1", "eth1/3/1"});

  auto result = cmd.queryClient(localhost(), interfaces);

  EXPECT_THAT(result, HasSubstr("eth1/1/1"));
  EXPECT_THAT(result, Not(HasSubstr("eth1/3/1")));
  EXPECT_EQ(queuingPolicyOf("eth1/1/1"), std::nullopt);
}

TEST_F(CmdDeleteInterfaceQueuingPolicyTestFixture, emptyInterfaceListThrows) {
  setupTestableConfigSession(cmdPrefix_, "queuing-policy");
  auto cmd = CmdDeleteInterfaceQueuingPolicy();
  utils::InterfaceList interfaces({});

  EXPECT_THROW(cmd.queryClient(localhost(), interfaces), std::invalid_argument);
}

} // namespace facebook::fboss
