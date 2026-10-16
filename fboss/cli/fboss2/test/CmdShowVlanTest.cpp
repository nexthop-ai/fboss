// (c) Meta Platforms, Inc. and its affiliates. Confidential and proprietary.

#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <cstdint>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/show/vlan/CmdShowVlan.h"
#include "fboss/cli/fboss2/commands/show/vlan/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/test/CmdHandlerTestBase.h"

using namespace ::testing;

namespace facebook::fboss {

namespace {

// Mirrors the shape a deployed switch runs: a loopback VLAN with no member
// ports whose addresses live on its bound interface, a data VLAN with one
// tagged and one untagged member plus DHCP relay, and a VLAN with neither
// members nor an interface (the case `show interface` cannot surface).
cfg::SwitchConfig createTestConfig() {
  cfg::SwitchConfig config;

  // logicalIDs deliberately do NOT follow port-name order -- these are the
  // real ids from a Wedge800, where eth1/2/1 is 264 but eth1/1/1
  // is 266. Members must still be listed in port-name order.
  cfg::Port port1;
  port1.logicalID() = 266;
  port1.name() = "eth1/1/1";
  cfg::Port port2;
  port2.logicalID() = 264;
  port2.name() = "eth1/2/1";
  cfg::Port port3;
  port3.logicalID() = 277;
  port3.name() = "eth1/3/1";
  // Double-digit slot: must sort after eth1/3/1, not between eth1/1/1 and
  // eth1/2/1 as a plain lexicographic sort would place it.
  cfg::Port port4;
  port4.logicalID() = 290;
  port4.name() = "eth1/10/1";
  // Deliberately unnamed, to prove the fallback to the numeric id.
  cfg::Port port5;
  port5.logicalID() = 300;
  config.ports() = {port1, port2, port3, port4, port5};

  cfg::Vlan loopbackVlan;
  loopbackVlan.id() = 10;
  loopbackVlan.name() = "fbossLoopback0";
  loopbackVlan.routable() = true;

  cfg::Vlan dataVlan;
  dataVlan.id() = 2000;
  dataVlan.name() = "downlink";
  dataVlan.routable() = true;
  dataVlan.dhcpRelayAddressV4() = "10.1.1.1";

  cfg::Vlan emptyVlan;
  emptyVlan.id() = 3000;
  emptyVlan.name() = "unused";
  emptyVlan.routable() = false;

  // Out of id order, to prove createModel sorts.
  config.vlans() = {dataVlan, emptyVlan, loopbackVlan};

  auto member = [](int32_t logicalPort, bool tagged) {
    cfg::VlanPort vlanPort;
    vlanPort.vlanID() = 2000;
    vlanPort.logicalPort() = logicalPort;
    vlanPort.emitTags() = tagged;
    return vlanPort;
  };
  // Inserted out of order, to prove createModel sorts.
  config.vlanPorts() = {
      member(290, false), // eth1/10/1
      member(266, true), // eth1/1/1, tagged
      member(300, false), // unnamed
      member(277, false), // eth1/3/1
      member(264, false), // eth1/2/1
  };

  cfg::Interface loopbackIntf;
  loopbackIntf.intfID() = 10;
  loopbackIntf.vlanID() = 10;
  loopbackIntf.type() = cfg::InterfaceType::VLAN;
  loopbackIntf.isVirtual() = true;
  loopbackIntf.ipAddresses() = {"10.254.113.31/32", "fc00:0:0:31::/128"};

  cfg::Interface dataIntf;
  dataIntf.intfID() = 2000;
  dataIntf.vlanID() = 2000;
  dataIntf.type() = cfg::InterfaceType::VLAN;
  dataIntf.ipAddresses() = {"192.168.0.1/24"};
  dataIntf.dhcpRelayAddressV6() = "2401:db00::1";

  config.interfaces() = {loopbackIntf, dataIntf};

  return config;
}

const cli::VlanEntry& entryForVlan(
    const cli::ShowVlanModel& model,
    int32_t vlanId) {
  for (const auto& entry : *model.vlans()) {
    if (*entry.vlanID() == vlanId) {
      return entry;
    }
  }
  throw std::runtime_error("no entry for VLAN " + std::to_string(vlanId));
}

} // namespace

class CmdShowVlanTestFixture : public CmdHandlerTestBase {};

TEST_F(CmdShowVlanTestFixture, listsEveryVlanSortedById) {
  auto model = CmdShowVlan().createModel(createTestConfig());

  ASSERT_EQ(model.vlans()->size(), 3);
  EXPECT_EQ(*model.vlans()[0].vlanID(), 10);
  EXPECT_EQ(*model.vlans()[1].vlanID(), 2000);
  EXPECT_EQ(*model.vlans()[2].vlanID(), 3000);
}

TEST_F(CmdShowVlanTestFixture, resolvesMemberPortsToNames) {
  auto model = CmdShowVlan().createModel(createTestConfig());
  const auto& dataVlan = entryForVlan(model, 2000);

  ASSERT_EQ(dataVlan.members()->size(), 5);
  // The unnamed port falls back to its numeric id, and tagging travels with
  // the port it belongs to.
  EXPECT_EQ(*dataVlan.members()[0].portName(), "eth1/1/1");
  EXPECT_TRUE(*dataVlan.members()[0].tagged());
  EXPECT_EQ(*dataVlan.members()[1].portName(), "eth1/2/1");
  EXPECT_FALSE(*dataVlan.members()[1].tagged());
  EXPECT_EQ(*dataVlan.members()[4].portName(), "300");
}

// Members are ordered by utils::comparePortNameOrId, not by logicalPort: on
// real hardware the ids do not follow name order (eth1/2/1 is 264, eth1/1/1 is
// 266), and a double-digit slot must not sort lexicographically between the
// single-digit ones. Names that do not parse as a physical port sort last,
// ordered by id.
TEST_F(CmdShowVlanTestFixture, ordersMembersByPortNameOrId) {
  auto model = CmdShowVlan().createModel(createTestConfig());
  const auto& dataVlan = entryForVlan(model, 2000);

  std::vector<std::string> names;
  for (const auto& m : *dataVlan.members()) {
    names.push_back(*m.portName());
  }
  EXPECT_THAT(
      names,
      ElementsAre("eth1/1/1", "eth1/2/1", "eth1/3/1", "eth1/10/1", "300"));
}

TEST_F(CmdShowVlanTestFixture, reportsVlanWithNoMembers) {
  auto model = CmdShowVlan().createModel(createTestConfig());

  const auto& emptyVlan = entryForVlan(model, 3000);
  EXPECT_TRUE(emptyVlan.members()->empty());
  EXPECT_TRUE(emptyVlan.ipAddresses()->empty());
  EXPECT_FALSE(emptyVlan.intfID().has_value());
  EXPECT_FALSE(*emptyVlan.routable());

  // The loopback has an interface and addresses, but still no member ports.
  const auto& loopbackVlan = entryForVlan(model, 10);
  EXPECT_TRUE(loopbackVlan.members()->empty());
  EXPECT_EQ(*loopbackVlan.intfID(), 10);
}

// ThriftConfigApplier::createVlan honours cfg::Vlan.intfID when set and only
// derives the interface from sw.interfaces otherwise, so an explicit intfID
// must win over a same-vlanID interface that happens to match.
TEST_F(CmdShowVlanTestFixture, prefersExplicitVlanIntfIDOverDerivedInterface) {
  auto config = createTestConfig();

  // A second interface carrying the VLAN's real addresses, reachable only via
  // the VLAN's explicit intfID -- its own vlanID deliberately points nowhere.
  cfg::Interface explicitIntf;
  explicitIntf.intfID() = 4242;
  explicitIntf.vlanID() = 9999;
  explicitIntf.type() = cfg::InterfaceType::VLAN;
  explicitIntf.ipAddresses() = {"10.42.42.1/24"};
  explicitIntf.dhcpRelayAddressV6() = "2401:db00::42";
  config.interfaces()->push_back(explicitIntf);

  for (auto& vlan : *config.vlans()) {
    if (*vlan.id() == 2000) {
      vlan.intfID() = 4242;
    }
  }

  auto model = CmdShowVlan().createModel(config);
  const auto& dataVlan = entryForVlan(model, 2000);

  // Not intfID 2000, which the derive-by-vlanID path would have picked.
  EXPECT_EQ(*dataVlan.intfID(), 4242);
  EXPECT_THAT(*dataVlan.ipAddresses(), ElementsAre("10.42.42.1/24"));
  EXPECT_EQ(*dataVlan.dhcpRelayAddressV6(), "2401:db00::42");
}

// An intfID naming an interface that is not in the config still reports the
// id the VLAN declares; there are simply no addresses to show for it.
TEST_F(CmdShowVlanTestFixture, reportsDanglingVlanIntfID) {
  auto config = createTestConfig();
  for (auto& vlan : *config.vlans()) {
    if (*vlan.id() == 2000) {
      vlan.intfID() = 7777;
    }
  }

  auto model = CmdShowVlan().createModel(config);
  const auto& dataVlan = entryForVlan(model, 2000);

  EXPECT_EQ(*dataVlan.intfID(), 7777);
  EXPECT_TRUE(dataVlan.ipAddresses()->empty());
}

TEST_F(CmdShowVlanTestFixture, takesAddressesFromBoundInterface) {
  auto model = CmdShowVlan().createModel(createTestConfig());
  const auto& loopbackVlan = entryForVlan(model, 10);

  EXPECT_THAT(
      *loopbackVlan.ipAddresses(),
      ElementsAre("10.254.113.31/32", "fc00:0:0:31::/128"));
}

TEST_F(CmdShowVlanTestFixture, mergesLegacyVlanAddresses) {
  auto config = createTestConfig();
  // A legacy config carrying the address on the VLAN itself, plus one that is
  // already on the interface -- the duplicate must not be reported twice.
  for (auto& vlan : *config.vlans()) {
    if (*vlan.id() == 10) {
      vlan.ipAddresses() = {"10.0.0.1/32", "10.254.113.31/32"};
    }
  }

  auto model = CmdShowVlan().createModel(config);
  EXPECT_THAT(
      *entryForVlan(model, 10).ipAddresses(),
      ElementsAre("10.0.0.1/32", "10.254.113.31/32", "fc00:0:0:31::/128"));
}

TEST_F(CmdShowVlanTestFixture, readsDhcpRelayFromVlanThenInterface) {
  auto model = CmdShowVlan().createModel(createTestConfig());
  const auto& dataVlan = entryForVlan(model, 2000);

  // V4 is set on the VLAN, V6 only on its interface.
  EXPECT_EQ(*dataVlan.dhcpRelayAddressV4(), "10.1.1.1");
  EXPECT_EQ(*dataVlan.dhcpRelayAddressV6(), "2401:db00::1");

  const auto& emptyVlan = entryForVlan(model, 3000);
  EXPECT_FALSE(emptyVlan.dhcpRelayAddressV4().has_value());
  EXPECT_FALSE(emptyVlan.dhcpRelayAddressV6().has_value());
}

TEST_F(CmdShowVlanTestFixture, printOutputRendersMembersAndPlaceholders) {
  auto model = CmdShowVlan().createModel(createTestConfig());

  std::stringstream ss;
  CmdShowVlan().printOutput(model, ss);
  const std::string output = ss.str();

  EXPECT_THAT(output, HasSubstr("fbossLoopback0"));
  EXPECT_THAT(output, HasSubstr("eth1/1/1"));
  EXPECT_THAT(output, HasSubstr("tagged"));
  EXPECT_THAT(output, HasSubstr("untagged"));
  EXPECT_THAT(output, HasSubstr("10.1.1.1"));
  // The member-less VLAN still gets a row, with placeholder cells.
  EXPECT_THAT(output, HasSubstr("unused"));
  EXPECT_THAT(output, HasSubstr("--"));
}

TEST_F(CmdShowVlanTestFixture, handlesEmptyConfig) {
  auto model = CmdShowVlan().createModel(cfg::SwitchConfig());
  EXPECT_TRUE(model.vlans()->empty());

  std::stringstream ss;
  CmdShowVlan().printOutput(model, ss);
  EXPECT_THAT(ss.str(), HasSubstr("VLAN ID"));
}

TEST_F(CmdShowVlanTestFixture, wikiDocHooks) {
  EXPECT_FALSE(CmdShowVlanTraits::description().empty());
  EXPECT_FALSE(CmdShowVlan::sampleModel().vlans()->empty());
}

} // namespace facebook::fboss
