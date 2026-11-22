// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"

#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <algorithm>
#include <stdexcept>
#include <string>

#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/agent/types.h"
#include "fboss/cli/fboss2/commands/config/interface/switchport/access/vlan/CmdConfigInterfaceSwitchportAccessVlan.h"
#include "fboss/cli/fboss2/commands/config/vlan/VlanManager.h"
#include "fboss/cli/fboss2/session/AgentConfigDomain.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

using namespace ::testing;

namespace facebook::fboss {

class CmdConfigInterfaceSwitchportAccessVlanTestFixture
    : public CmdConfigTestBase {
 public:
  CmdConfigInterfaceSwitchportAccessVlanTestFixture()
      : CmdConfigTestBase(
            "fboss_switchport_test_%%%%-%%%%-%%%%-%%%%",
            R"({
  "sw": {
    "ports": [
      {
        "logicalID": 1,
        "name": "eth1/1/1",
        "state": 2,
        "speed": 100000,
        "ingressVlan": 1
      },
      {
        "logicalID": 2,
        "name": "eth1/2/1",
        "state": 2,
        "speed": 100000,
        "ingressVlan": 1
      }
    ],
    "vlanPorts": [
      {
        "vlanID": 1,
        "logicalPort": 1,
        "spanningTreeState": 2,
        "emitTags": false
      },
      {
        "vlanID": 1,
        "logicalPort": 2,
        "spanningTreeState": 2,
        "emitTags": false
      }
    ],
    "defaultVlan": 4000,
    "vlans": [
      {"id": 1, "name": "vlan1", "routable": true, "intfID": 1},
      {"id": 2001, "name": "vlan2001", "routable": true, "intfID": 2001},
      {"id": 3000, "name": "vlan3000", "routable": true, "intfID": 0},
      {"id": 4000, "name": "vlan4000", "routable": false, "intfID": 0}
    ],
    "interfaces": [
      {"intfID": 1, "vlanID": 1, "routerID": 0, "type": 1, "mtu": 9412},
      {"intfID": 2001, "vlanID": 2001, "routerID": 0, "type": 1, "mtu": 9412}
    ]
  }
})") {}

  void SetUp() override {
    CmdConfigTestBase::SetUp();

    setupTestableConfigSession(
        "config interface switchport access vlan eth1/1/1", "100");
  }
<<<<<<< HEAD
=======

  // All vlanPorts entries for the given logical port in the session config.
  static std::vector<cfg::VlanPort> vlanPortEntriesFor(int32_t logicalPort) {
    auto& swConfig =
        *ConfigSession::getInstance().config<AgentConfigDomain>().sw();
    std::vector<cfg::VlanPort> entries;
    for (const auto& vp : *swConfig.vlanPorts()) {
      if (*vp.logicalPort() == logicalPort) {
        entries.push_back(vp);
      }
    }
    return entries;
  }
>>>>>>> 36db926676 (NOS-23962: [fboss2] Replace ConfigSession's per-service accessors (6/6) (#3090))
};

// Tests for VlanIdValue validation

TEST_F(CmdConfigInterfaceSwitchportAccessVlanTestFixture, vlanIdValidMin) {
  VlanIdValue vlanId({"1"});
  EXPECT_EQ(vlanId.getVlanId(), 1);
}

TEST_F(CmdConfigInterfaceSwitchportAccessVlanTestFixture, vlanIdValidMax) {
  VlanIdValue vlanId({"4094"});
  EXPECT_EQ(vlanId.getVlanId(), 4094);
}

TEST_F(CmdConfigInterfaceSwitchportAccessVlanTestFixture, vlanIdValidMid) {
  VlanIdValue vlanId({"100"});
  EXPECT_EQ(vlanId.getVlanId(), 100);
}

TEST_F(CmdConfigInterfaceSwitchportAccessVlanTestFixture, vlanIdZeroInvalid) {
  EXPECT_THROW(VlanIdValue({"0"}), std::invalid_argument);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdTooHighInvalid) {
  EXPECT_THROW(VlanIdValue({"4095"}), std::invalid_argument);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdNegativeInvalid) {
  EXPECT_THROW(VlanIdValue({"-1"}), std::invalid_argument);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdNonNumericInvalid) {
  EXPECT_THROW(VlanIdValue({"abc"}), std::invalid_argument);
}

TEST_F(CmdConfigInterfaceSwitchportAccessVlanTestFixture, vlanIdEmptyInvalid) {
  EXPECT_THROW(VlanIdValue({}), std::invalid_argument);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdMultipleValuesInvalid) {
  EXPECT_THROW(VlanIdValue({"100", "200"}), std::invalid_argument);
}

// Test error message format
TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdOutOfRangeErrorMessage) {
  try {
    auto unused = VlanIdValue({"9999"});
    (void)unused;
    FAIL() << "Expected std::invalid_argument";
  } catch (const std::invalid_argument& e) {
    std::string errorMsg = e.what();
    EXPECT_THAT(errorMsg, HasSubstr("VLAN ID must be between 1 and 4094"));
    EXPECT_THAT(errorMsg, HasSubstr("9999"));
  }
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    vlanIdNonNumericErrorMessage) {
  try {
    auto unused = VlanIdValue({"notanumber"});
    (void)unused;
    FAIL() << "Expected std::invalid_argument";
  } catch (const std::invalid_argument& e) {
    std::string errorMsg = e.what();
    EXPECT_THAT(errorMsg, HasSubstr("Invalid VLAN ID"));
    EXPECT_THAT(errorMsg, HasSubstr("notanumber"));
  }
}

// Tests for queryClient

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientSetsIngressVlanMultiplePorts) {
  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  VlanIdValue vlanId({"2001"});

  utils::InterfaceList interfaces({"eth1/1/1", "eth1/2/1"});

  auto result = cmd.queryClient(localhost(), interfaces, vlanId);

  EXPECT_THAT(result, HasSubstr("Successfully set access VLAN"));
  EXPECT_THAT(result, HasSubstr("eth1/1/1"));
  EXPECT_THAT(result, HasSubstr("eth1/2/1"));
  EXPECT_THAT(result, HasSubstr("2001"));

  // Verify the ingressVlan was updated for both ports
  auto& session = ConfigSession::getInstance();
  auto& config = session.config<AgentConfigDomain>();
  auto& switchConfig = *config.sw();
  auto& ports = *switchConfig.ports();
  for (const auto& port : ports) {
    if (*port.name() == "eth1/1/1" || *port.name() == "eth1/2/1") {
      EXPECT_EQ(*port.ingressVlan(), 2001);
    }
  }

  // Verify the vlanPorts entries were also updated
  auto& vlanPorts = *switchConfig.vlanPorts();
  for (const auto& vlanPort : vlanPorts) {
    if (*vlanPort.logicalPort() == 1 || *vlanPort.logicalPort() == 2) {
      EXPECT_EQ(*vlanPort.vlanID(), 2001);
    }
  }
<<<<<<< HEAD
=======
  EXPECT_TRUE(foundUntagged2001);
  EXPECT_TRUE(foundTagged3000);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientInsertsVlanPortWhenMissing) {
  // eth1/3/1 (logical port 3) has no vlanPorts entry in the fixture config;
  // the command must insert one rather than leave the port with an
  // ingressVlan it is not a member of.
  ASSERT_TRUE(vlanPortEntriesFor(3).empty());

  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  utils::InterfaceList interfaces({"eth1/3/1"});
  VlanIdValue vlanId({"2001"});

  auto result = cmd.queryClient(localhost(), interfaces, vlanId);
  EXPECT_THAT(result, HasSubstr("Successfully set access VLAN"));

  auto entries = vlanPortEntriesFor(3);
  ASSERT_EQ(entries.size(), 1);
  EXPECT_EQ(*entries[0].vlanID(), 2001);
  EXPECT_FALSE(*entries[0].emitTags());
  EXPECT_EQ(
      *entries[0].spanningTreeState(), cfg::SpanningTreeState::FORWARDING);

  auto& swConfig =
      *ConfigSession::getInstance().config<AgentConfigDomain>().sw();
  for (const auto& port : *swConfig.ports()) {
    if (*port.name() == "eth1/3/1") {
      EXPECT_EQ(*port.ingressVlan(), 2001);
    }
  }
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientDeduplicatesConflictingEntries) {
  // eth1/2/1 (logical port 2) starts with an untagged membership in VLAN 1
  // and a tagged membership in VLAN 3000. Setting access VLAN 3000 must not
  // leave duplicate (vlan, port) entries: both old entries are replaced by a
  // single untagged membership in VLAN 3000.
  ASSERT_EQ(vlanPortEntriesFor(2).size(), 2);

  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  utils::InterfaceList interfaces({"eth1/2/1"});
  VlanIdValue vlanId({"3000"});

  auto result = cmd.queryClient(localhost(), interfaces, vlanId);
  EXPECT_THAT(result, HasSubstr("Successfully set access VLAN"));

  auto entries = vlanPortEntriesFor(2);
  ASSERT_EQ(entries.size(), 1);
  EXPECT_EQ(*entries[0].vlanID(), 3000);
  EXPECT_FALSE(*entries[0].emitTags());
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientIsIdempotent) {
  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  utils::InterfaceList interfaces({"eth1/1/1"});
  VlanIdValue vlanId({"2001"});

  cmd.queryClient(localhost(), interfaces, vlanId);
  cmd.queryClient(localhost(), interfaces, vlanId);

  // Running the command twice must not accumulate duplicate entries
  auto entries = vlanPortEntriesFor(1);
  ASSERT_EQ(entries.size(), 1);
  EXPECT_EQ(*entries[0].vlanID(), 2001);
  EXPECT_FALSE(*entries[0].emitTags());
>>>>>>> 36db926676 (NOS-23962: [fboss2] Replace ConfigSession's per-service accessors (6/6) (#3090))
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientThrowsOnEmptyInterfaceList) {
  setupTestableConfigSession();
  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  utils::InterfaceList emptyInterfaces({});
  VlanIdValue vlanId({"100"});
  EXPECT_THROW(
      cmd.queryClient(localhost(), emptyInterfaces, vlanId),
      std::invalid_argument);
}

TEST_F(
    CmdConfigInterfaceSwitchportAccessVlanTestFixture,
    queryClientCreatesVlanWhenMissing) {
  auto cmd = CmdConfigInterfaceSwitchportAccessVlan();
  utils::InterfaceList interfaces({"eth1/1/1"});
  VlanIdValue vlanId({"4094"});

  auto result = cmd.queryClient(localhost(), interfaces, vlanId);

  EXPECT_THAT(result, HasSubstr("Successfully set access VLAN"));
  EXPECT_THAT(result, HasSubstr("(VLAN 4094 created)"));

  auto& config = ConfigSession::getInstance().config<AgentConfigDomain>();
  auto& swConfig = *config.sw();

  // The VLAN and its barebone interface were created
  EXPECT_NE(VlanManager::findVlan(swConfig, VlanID(4094)), nullptr);
  bool intfFound = std::any_of(
      swConfig.interfaces()->cbegin(),
      swConfig.interfaces()->cend(),
      [](const auto& intf) { return *intf.vlanID() == 4094; });
  EXPECT_TRUE(intfFound);

  // And the port was moved to it
  for (const auto& port : *swConfig.ports()) {
    if (*port.name() == "eth1/1/1") {
      EXPECT_EQ(*port.ingressVlan(), 4094);
    }
  }
}

} // namespace facebook::fboss
