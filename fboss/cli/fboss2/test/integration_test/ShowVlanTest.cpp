// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end tests for 'fboss2 show vlan'.
 *
 * 'show vlan' has no thrift API behind it: it reads the agent's running
 * config and joins sw.vlans against sw.vlanPorts (members), sw.ports (member
 * names) and sw.interfaces (bound interface, IP addresses, DHCP relay). The
 * unit test (CmdShowVlanTest) covers that join against synthetic configs, so
 * what is left to test here is the part that only a live agent can show:
 * that the command talks to the agent, and that what it prints agrees with
 * the config the agent is actually running.
 *
 * Tests:
 *
 * 1. MatchesRunningConfig
 *    Re-derive the expected join from getRunningConfig() inside the test and
 *    compare it field by field with the command's JSON output. The
 *    re-derivation is deliberately independent of CmdShowVlan so a change in
 *    the handler that drops or mis-joins a field fails here.
 *
 * 2. FilterByVlanId
 *    --filter 'vlanID == <id>' narrows the output to one VLAN, and an invalid
 *    filter key or value is rejected.
 *
 * Requirements:
 * - FBOSS agent must be running with a valid configuration.
 */

#include <folly/json/dynamic.h>
#include <folly/logging/xlog.h>
#include <gtest/gtest.h>
#include <algorithm>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

namespace {
// cfg::InterfaceType::VLAN. Thrift's SimpleJSON serializer writes enums as
// their integer value, so the running config carries 1 here rather than the
// name. cfg::Interface.type defaults to VLAN when the field is absent.
constexpr int kInterfaceTypeVlan = 1;

int64_t asIntOr(const folly::dynamic& obj, const char* key, int64_t fallback) {
  return obj.count(key) ? obj[key].asInt() : fallback;
}

bool asBoolOr(const folly::dynamic& obj, const char* key, bool fallback) {
  return obj.count(key) ? obj[key].asBool() : fallback;
}

std::string asStringOr(
    const folly::dynamic& obj,
    const char* key,
    const std::string& fallback) {
  return obj.count(key) ? obj[key].asString() : fallback;
}

std::optional<std::string> asOptString(
    const folly::dynamic& obj,
    const char* key) {
  if (!obj.count(key)) {
    return std::nullopt;
  }
  return obj[key].asString();
}
} // namespace

class ShowVlanTest : public Fboss2IntegrationTest {
 protected:
  /**
   * What 'show vlan' is expected to report for one VLAN, derived from the
   * running config by the test itself.
   */
  struct ExpectedVlan {
    std::string name;
    bool routable{false};
    std::optional<int> intfID;
    // portName -> tagged. A map rather than a list because the ordering is
    // asserted separately.
    std::map<std::string, bool> members;
    std::set<std::string> ipAddresses;
    std::optional<std::string> dhcpRelayAddressV4;
    std::optional<std::string> dhcpRelayAddressV6;
  };

  /**
   * Run the given CLI command and return its VLAN entries keyed by VLAN ID.
   * The JSON output of a show command is keyed by host, and these tests run
   * against localhost only, so the per-host objects are merged.
   */
  std::map<int, folly::dynamic> showVlan(
      const std::vector<std::string>& args = {"show", "vlan"}) const {
    auto json = runCliJson(args);
    std::map<int, folly::dynamic> entries;
    for (const auto& [host, hostData] : json.items()) {
      if (!hostData.isObject() || !hostData.count("vlans")) {
        continue;
      }
      for (const auto& vlan : hostData["vlans"]) {
        entries.emplace(vlan["vlanID"].asInt(), vlan);
      }
    }
    return entries;
  }

  /**
   * The VLAN IDs in the order the command printed them, so the sort order can
   * be asserted (showVlan() re-keys by ID and loses it).
   */
  std::vector<int> showVlanIdsInOrder() const {
    auto json = runCliJson({"show", "vlan"});
    std::vector<int> ids;
    for (const auto& [host, hostData] : json.items()) {
      if (!hostData.isObject() || !hostData.count("vlans")) {
        continue;
      }
      for (const auto& vlan : hostData["vlans"]) {
        ids.push_back(vlan["vlanID"].asInt());
      }
    }
    return ids;
  }

  /**
   * Re-derive what 'show vlan' should report, from the agent's running config.
   *
   * This repeats the join CmdShowVlan::createModel does, on purpose: computing
   * the answer a second way from the same live source is what makes the
   * comparison meaningful. It follows the same precedence the agent's
   * ThriftConfigApplier::createVlan uses when binding a VLAN to an interface --
   * cfg::Vlan.intfID when set, otherwise the VLAN-type interface whose vlanID
   * matches.
   */
  std::map<int, ExpectedVlan> expectedFromRunningConfig(
      const folly::dynamic& config) const {
    std::map<int, ExpectedVlan> expected;
    if (!config.isObject() || !config.count("sw")) {
      return expected;
    }
    const auto& sw = config["sw"];
    if (!sw.count("vlans")) {
      return expected;
    }

    // logicalID -> port name, with the numeric id as fallback for unnamed
    // ports.
    std::map<int, std::string> portNameById;
    if (sw.count("ports")) {
      for (const auto& port : sw["ports"]) {
        int logicalId = port["logicalID"].asInt();
        portNameById[logicalId] =
            asStringOr(port, "name", std::to_string(logicalId));
      }
    }

    std::map<int, std::map<std::string, bool>> membersByVlan;
    if (sw.count("vlanPorts")) {
      for (const auto& vlanPort : sw["vlanPorts"]) {
        int logicalPort = vlanPort["logicalPort"].asInt();
        auto it = portNameById.find(logicalPort);
        auto name =
            it != portNameById.end() ? it->second : std::to_string(logicalPort);
        membersByVlan[vlanPort["vlanID"].asInt()][name] =
            asBoolOr(vlanPort, "emitTags", false);
      }
    }

    std::map<int, folly::dynamic> interfaceById;
    std::map<int, folly::dynamic> vlanInterfaceByVlanId;
    if (sw.count("interfaces")) {
      for (const auto& interface : sw["interfaces"]) {
        interfaceById.emplace(interface["intfID"].asInt(), interface);
        if (asIntOr(interface, "type", kInterfaceTypeVlan) ==
                kInterfaceTypeVlan &&
            interface.count("vlanID")) {
          vlanInterfaceByVlanId.emplace(interface["vlanID"].asInt(), interface);
        }
      }
    }

    for (const auto& vlan : sw["vlans"]) {
      ExpectedVlan entry;
      entry.name = vlan["name"].asString();
      entry.routable = asBoolOr(vlan, "routable", false);

      int vlanId = vlan["id"].asInt();
      if (auto members = membersByVlan.find(vlanId);
          members != membersByVlan.end()) {
        entry.members = members->second;
      }

      const folly::dynamic* interface = nullptr;
      if (vlan.count("intfID")) {
        entry.intfID = vlan["intfID"].asInt();
        if (auto it = interfaceById.find(*entry.intfID);
            it != interfaceById.end()) {
          interface = &it->second;
        }
      } else if (auto it = vlanInterfaceByVlanId.find(vlanId);
                 it != vlanInterfaceByVlanId.end()) {
        interface = &it->second;
        if (interface->count("intfID")) {
          entry.intfID = (*interface)["intfID"].asInt();
        }
      }

      // Legacy configs carry addresses on cfg::Vlan; current ones carry them
      // on the bound interface. Both are reported.
      if (vlan.count("ipAddresses")) {
        for (const auto& address : vlan["ipAddresses"]) {
          entry.ipAddresses.insert(address.asString());
        }
      }
      entry.dhcpRelayAddressV4 = asOptString(vlan, "dhcpRelayAddressV4");
      entry.dhcpRelayAddressV6 = asOptString(vlan, "dhcpRelayAddressV6");
      if (interface != nullptr) {
        if (interface->count("ipAddresses")) {
          for (const auto& address : (*interface)["ipAddresses"]) {
            entry.ipAddresses.insert(address.asString());
          }
        }
        // The VLAN wins when both carry a relay address.
        if (!entry.dhcpRelayAddressV4) {
          entry.dhcpRelayAddressV4 =
              asOptString(*interface, "dhcpRelayAddressV4");
        }
        if (!entry.dhcpRelayAddressV6) {
          entry.dhcpRelayAddressV6 =
              asOptString(*interface, "dhcpRelayAddressV6");
        }
      }

      expected.emplace(vlanId, entry);
    }
    return expected;
  }

  // Compare one reported VLAN entry against what the running config implies.
  void verifyEntry(
      int vlanId,
      const ExpectedVlan& expected,
      const folly::dynamic& actual) const {
    EXPECT_EQ(actual["name"].asString(), expected.name)
        << "VLAN " << vlanId << " name mismatch";
    EXPECT_EQ(actual["routable"].asBool(), expected.routable)
        << "VLAN " << vlanId << " routable mismatch";

    if (expected.intfID) {
      ASSERT_TRUE(actual.count("intfID"))
          << "VLAN " << vlanId << " should report interface "
          << *expected.intfID;
      EXPECT_EQ(actual["intfID"].asInt(), *expected.intfID)
          << "VLAN " << vlanId << " interface mismatch";
    } else {
      EXPECT_FALSE(actual.count("intfID"))
          << "VLAN " << vlanId << " reports an interface it has no config for";
    }

    std::map<std::string, bool> actualMembers;
    for (const auto& member : actual["members"]) {
      actualMembers[member["portName"].asString()] = member["tagged"].asBool();
      // Names come from sw.ports; an unresolved member would show the numeric
      // id instead, which the join is supposed to avoid.
      EXPECT_FALSE(member["portName"].asString().empty())
          << "VLAN " << vlanId << " has a member with an empty port name";
    }
    EXPECT_EQ(actualMembers, expected.members)
        << "VLAN " << vlanId << " members mismatch";

    std::set<std::string> actualAddresses;
    for (const auto& address : actual["ipAddresses"]) {
      actualAddresses.insert(address.asString());
    }
    EXPECT_EQ(actualAddresses, expected.ipAddresses)
        << "VLAN " << vlanId << " IP addresses mismatch";

    EXPECT_EQ(
        asOptString(actual, "dhcpRelayAddressV4"), expected.dhcpRelayAddressV4)
        << "VLAN " << vlanId << " DHCP relay v4 mismatch";
    EXPECT_EQ(
        asOptString(actual, "dhcpRelayAddressV6"), expected.dhcpRelayAddressV6)
        << "VLAN " << vlanId << " DHCP relay v6 mismatch";
  }
};

TEST_F(ShowVlanTest, MatchesRunningConfig) {
  auto config = getRunningConfig();
  auto expected = expectedFromRunningConfig(config);
  if (expected.empty()) {
    GTEST_SKIP() << "DUT has no VLANs configured";
  }

  auto actual = showVlan();

  // Every configured VLAN is reported, and nothing else is.
  std::set<int> expectedIds;
  for (const auto& entry : expected) {
    expectedIds.insert(entry.first);
  }
  std::set<int> actualIds;
  for (const auto& entry : actual) {
    actualIds.insert(entry.first);
  }
  EXPECT_EQ(actualIds, expectedIds)
      << "show vlan does not report exactly the VLANs in the running config";

  for (const auto& [vlanId, expectedVlan] : expected) {
    auto it = actual.find(vlanId);
    if (it == actual.end()) {
      ADD_FAILURE() << "VLAN " << vlanId << " missing from show vlan output";
      continue;
    }
    verifyEntry(vlanId, expectedVlan, it->second);
  }

  // Output is ordered by VLAN ID so it is stable across runs.
  auto ids = showVlanIdsInOrder();
  EXPECT_TRUE(std::is_sorted(ids.begin(), ids.end()))
      << "show vlan output is not ordered by VLAN ID";

  XLOG(INFO) << "Verified " << expected.size()
             << " VLANs against the running config";
}

TEST_F(ShowVlanTest, FilterByVlanId) {
  auto entries = showVlan();
  if (entries.empty()) {
    GTEST_SKIP() << "DUT has no VLANs configured";
  }
  int vlanId = entries.begin()->first;

  // --filter is a global option and must precede the subcommand.
  auto filtered = showVlan(
      {"--filter", "vlanID == " + std::to_string(vlanId), "show", "vlan"});
  EXPECT_EQ(filtered.size(), 1u) << "Filtering on vlanID == " << vlanId
                                 << " returned " << filtered.size() << " VLANs";
  EXPECT_EQ(filtered.count(vlanId), 1u)
      << "Filtered output does not contain VLAN " << vlanId;

  // A filter on a field the model does not have must be rejected.
  auto badKey = runCli({"--filter", "bogusField == 1", "show", "vlan"});
  EXPECT_NE(badKey.exitCode, 0) << "Unknown filter key was not rejected";

  // vlanID is an i32; a non-numeric value must be rejected.
  auto badValue = runCli({"--filter", "vlanID == notANumber", "show", "vlan"});
  EXPECT_NE(badValue.exitCode, 0) << "Invalid filter value was not rejected";
}
