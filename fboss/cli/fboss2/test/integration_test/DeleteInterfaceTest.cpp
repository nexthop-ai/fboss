// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end tests for 'fboss2-dev delete interface <name|intfID>
 * [<attr> ...]'
 *
 * The attribute tests:
 *  1. Pick an interface from the running system
 *  2. Set one or more attributes via the config CLI
 *  3. Delete (reset to defaults) via the delete CLI
 *  4. Verify the command succeeds (exit code 0)
 *
 * The bare (no-attribute) tests cover whole-object deletes: a port by name,
 * and an L3 interface by its interface ID.
 *
 * Requirements:
 *  - FBOSS agent must be running with a valid configuration
 *  - The test must be run as root (or with appropriate permissions)
 */

<<<<<<< HEAD
=======
#include <folly/Conv.h>
#include <folly/ScopeGuard.h>
>>>>>>> 21e9a9423f (NOS-5557: Support deleting an L3 interface with delete interface (#1615))
#include <folly/logging/xlog.h>
#include <gtest/gtest.h>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

class DeleteInterfaceTest : public Fboss2IntegrationTest {
 protected:
  // Interface ID of the SVI backing `vlanId` in a running config, if any.
  static std::optional<int> interfaceIdForVlan(
      const folly::dynamic& config,
      int vlanId) {
    if (!config.isObject() || !config.count("sw") ||
        !config["sw"].count("interfaces")) {
      return std::nullopt;
    }
    for (const auto& i : config["sw"]["interfaces"]) {
      if (i.count("vlanID") && i["vlanID"].asInt() == vlanId &&
          i.count("intfID")) {
        return i["intfID"].asInt();
      }
    }
    return std::nullopt;
  }

  static bool hasVlan(const folly::dynamic& config, int vlanId) {
    if (!config.isObject() || !config.count("sw") ||
        !config["sw"].count("vlans")) {
      return false;
    }
    for (const auto& v : config["sw"]["vlans"]) {
      if (v.count("id") && v["id"].asInt() == vlanId) {
        return true;
      }
    }
    return false;
  }

  static bool vlanPresent(const folly::dynamic& config, int vlanId) {
    return hasVlan(config, vlanId) &&
        interfaceIdForVlan(config, vlanId).has_value();
  }

  static bool vlanGone(const folly::dynamic& config, int vlanId) {
    return !hasVlan(config, vlanId) &&
        !interfaceIdForVlan(config, vlanId).has_value();
  }

  // First VLAN ID in [2, 4094] unused in the running config. Mirrors the
  // picker in DeleteVlanTest — the harness has no shared one.
  int pickUnusedVlanId() const {
    auto config = getRunningConfig();
    std::set<int> used;
    if (config.isObject() && config.count("sw")) {
      const auto& sw = config["sw"];
      if (sw.count("defaultVlan")) {
        used.insert(sw["defaultVlan"].asInt());
      }
      for (const auto& [array, field] :
           {std::pair<const char*, const char*>{"ports", "ingressVlan"},
            {"vlanPorts", "vlanID"},
            {"interfaces", "vlanID"},
            {"vlans", "id"}}) {
        if (!sw.count(array)) {
          continue;
        }
        for (const auto& item : sw[array]) {
          if (item.count(field)) {
            used.insert(item[field].asInt());
          }
        }
      }
    }
    for (int id = 2; id <= 4094; ++id) {
      if (!used.count(id)) {
        return id;
      }
    }
    return 0;
  }

  // Drops a VLAN left behind by an aborted run. The happy path has already
  // cascaded it away, so this is normally a no-op. Must not throw: callers
  // invoke this from SCOPE_EXIT during test teardown.
  void deleteVlanIfPresent(int vlanId) const noexcept {
    try {
      if (!hasVlan(getRunningConfig(), vlanId)) {
        return;
      }
      auto result = runCli({"delete", "vlan", std::to_string(vlanId)});
      if (result.exitCode != 0) {
        XLOG(WARN) << "cleanup: delete vlan " << vlanId
                   << " failed, discarding session: " << result.stderr;
        discardSession();
        return;
      }
      auto commit = runCli({"config", "session", "commit"});
      if (commit.exitCode != 0) {
        XLOG(WARN) << "cleanup: commit after delete vlan " << vlanId
                   << " failed, discarding session: " << commit.stderr;
        discardSession();
      }
    } catch (const std::exception& e) {
      XLOG(WARN) << "cleanup: delete vlan " << vlanId << " threw: " << e.what();
      discardSession();
    } catch (...) {
      XLOG(WARN) << "cleanup: delete vlan " << vlanId
                 << " threw an unknown exception";
      discardSession();
    }
  }

  // Setters record what they touch so TearDown can reset the attribute via
  // the delete CLI even when a test fails midway, keeping the shared DUT
  // clean. The delete command is idempotent, so re-deleting an attribute the
  // test already deleted is harmless.
  void setLoopbackMode(
      const std::string& interfaceName,
      const std::string& mode) {
    touched_.emplace_back(interfaceName, "loopback-mode");
    auto result =
        runCli({"config", "interface", interfaceName, "loopback-mode", mode});
    ASSERT_EQ(result.exitCode, 0)
        << "Failed to set loopback-mode=" << mode << ": " << result.stderr;
    commitConfig();
  }

  void setLldpExpectedValue(
      const std::string& interfaceName,
      const std::string& value) {
    touched_.emplace_back(interfaceName, "lldp-expected-value");
    auto result = runCli(
        {"config", "interface", interfaceName, "lldp-expected-value", value});
    ASSERT_EQ(result.exitCode, 0)
        << "Failed to set lldp-expected-value=" << value << ": "
        << result.stderr;
    commitConfig();
  }

  void deleteInterfaceAttrs(
      const std::string& interfaceName,
      const std::vector<std::string>& attrs) {
    std::vector<std::string> args = {"delete", "interface", interfaceName};
    for (const auto& attr : attrs) {
      args.push_back(attr);
    }
    auto result = runCli(args);
    ASSERT_EQ(result.exitCode, 0)
        << "Failed to delete interface attrs: " << result.stderr;
    commitConfig();
  }

  void TearDown() override {
    if (!touched_.empty()) {
      bool reset = false;
      for (const auto& [interfaceName, attr] : touched_) {
        auto result = runCli({"delete", "interface", interfaceName, attr});
        if (result.exitCode != 0) {
          XLOG(WARN) << "TearDown failed to delete " << attr << " on "
                     << interfaceName << ": " << result.stderr;
        } else {
          reset = true;
        }
      }
      if (reset) {
        commitConfig();
      }
    }
    Fboss2IntegrationTest::TearDown();
  }

 private:
  // (interfaceName, attr) pairs set by this test, deleted in TearDown
  std::vector<std::pair<std::string, std::string>> touched_;
};

// ---------------------------------------------------------------------------
// Test: set loopback-mode=PHY then delete it (reset to NONE)
//
// Disabled: committing loopback-mode=PHY triggers an agent restart on
// NH-4010-F + Broadcom SAI 1.16.1 (the SAI driver returns FAILURE for
// SAI_PORT_ATTR_LOOPBACK_MODE=PHY and SaiPortManager::changePortImpl does
// not catch the SaiApiError, crashing the hw_agent). Same root cause as
// the disabled ConfigInterfaceLoopbackModeTest.SetAndVerifyLoopbackMode.
// Re-enable once the agent contains SaiApiError on the change-port path.
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DISABLED_DeleteLoopbackModePHY) {
  XLOG(INFO) << "[Step 1] Finding an interface to test...";
  std::string ifName = getRandomInterfacePortName();
  XLOG(INFO) << "  Using interface: " << ifName;

  XLOG(INFO) << "[Step 2] Setting loopback-mode=PHY...";
  setLoopbackMode(ifName, "PHY");

  XLOG(INFO) << "[Step 3] Deleting loopback-mode (reset to NONE)...";
  deleteInterfaceAttrs(ifName, {"loopback-mode"});

  XLOG(INFO)
      << "  loopback-mode deleted successfully (exit 0, config committed)";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: delete loopback-mode is idempotent (no loopback-mode set beforehand)
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DeleteLoopbackModeIdempotent) {
  XLOG(INFO) << "[Step 1] Finding an interface to test...";
  std::string ifName = getRandomInterfacePortName();
  XLOG(INFO) << "  Using interface: " << ifName;

  XLOG(INFO) << "[Step 2] Deleting loopback-mode without setting it first...";
  deleteInterfaceAttrs(ifName, {"loopback-mode"});

  XLOG(INFO) << "  Idempotent delete succeeded (exit 0)";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: set lldp-expected-value then delete it
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DeleteLldpExpectedValue) {
  XLOG(INFO) << "[Step 1] Finding an interface to test...";
  std::string ifName = getRandomInterfacePortName();
  XLOG(INFO) << "  Using interface: " << ifName;

  XLOG(INFO) << "[Step 2] Setting lldp-expected-value=ge-0/0/0...";
  setLldpExpectedValue(ifName, "ge-0/0/0");

  XLOG(INFO)
      << "[Step 3] Deleting lldp-expected-value (removing PORT entry)...";
  deleteInterfaceAttrs(ifName, {"lldp-expected-value"});

  XLOG(INFO)
      << "  lldp-expected-value deleted successfully (exit 0, config committed)";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: delete lldp-expected-value is idempotent
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DeleteLldpExpectedValueIdempotent) {
  XLOG(INFO) << "[Step 1] Finding an interface to test...";
  std::string ifName = getRandomInterfacePortName();
  XLOG(INFO) << "  Using interface: " << ifName;

  XLOG(INFO)
      << "[Step 2] Deleting lldp-expected-value without setting it first...";
  deleteInterfaceAttrs(ifName, {"lldp-expected-value"});

  XLOG(INFO) << "  Idempotent delete succeeded (exit 0)";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: delete both loopback-mode and lldp-expected-value in one call
//
// Disabled: same agent-restart issue as DISABLED_DeleteLoopbackModePHY
// (loopback-mode=PHY crashes the hw_agent on NH-4010-F).
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DISABLED_DeleteLoopbackModeAndLldpExpectedValue) {
  XLOG(INFO) << "[Step 1] Finding an interface to test...";
  std::string ifName = getRandomInterfacePortName();
  XLOG(INFO) << "  Using interface: " << ifName;

  XLOG(INFO) << "[Step 2] Setting loopback-mode=PHY and lldp-expected-value...";
  setLoopbackMode(ifName, "PHY");
  setLldpExpectedValue(ifName, "ge-0/0/0");

  XLOG(INFO)
      << "[Step 3] Deleting both loopback-mode and lldp-expected-value in one call...";
  deleteInterfaceAttrs(ifName, {"loopback-mode", "lldp-expected-value"});

  XLOG(INFO) << "  Combined delete succeeded (exit 0, config committed)";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: bare 'delete interface <port>' removes a whole port.
//
// Break a controlling port into two lower-speed ports (create the freed subport
// via a single combined command, as in
// ConfigInterfaceProfileTest.CreateFreedPortSucceeds), then delete that subport
// as a whole port and confirm the agent no longer reports it. Finally re-create
// the original controlling port by widening it back to its starting profile,
// leaving the DUT as we found it.
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DeleteWholePortRemovesCreatedSubport) {
  auto cand = findFreeableCandidate();
  if (!cand) {
    GTEST_SKIP()
        << "No absent subport freeable by narrowing its controlling port";
  }
  XLOG(INFO) << "[Step 1] controlling=" << cand->controllingName << " ("
             << cand->controllingProfile << ") -> " << cand->narrowProfile
             << "; subport=" << cand->subportName;

  XLOG(INFO)
      << "[Step 2] Breaking the controlling port into two (single command)...";
  auto create = runCli(
      {"config",
       "interface",
       cand->controllingName,
       cand->subportName,
       "profile",
       cand->narrowProfile});
  ASSERT_EQ(create.exitCode, 0) << create.stderr;
  commitConfig();

  auto created = waitForPortRunningInfo(
      cand->subportName,
      [&cand](const auto& i) { return i.profileId == cand->narrowProfile; });
  ASSERT_EQ(created.profileId, cand->narrowProfile)
      << "subport " << cand->subportName << " was not created";

  XLOG(INFO) << "[Step 3] Deleting the whole subport " << cand->subportName
             << "...";
  auto del = runCli({"delete", "interface", cand->subportName});
  ASSERT_EQ(del.exitCode, 0) << del.stderr;
  commitConfig();

  EXPECT_TRUE(waitForPortAbsent(cand->subportName))
      << cand->subportName << " should be removed after 'delete interface'";

  XLOG(INFO) << "[Step 4] Re-creating the original controlling port...";
  auto restore = runCli(
      {"config",
       "interface",
       cand->controllingName,
       "profile",
       cand->controllingProfile});
  ASSERT_EQ(restore.exitCode, 0) << restore.stderr;
  commitConfig();

  auto restored =
      waitForPortRunningInfo(cand->controllingName, [&cand](const auto& i) {
        return i.profileId == cand->controllingProfile;
      });
  EXPECT_EQ(restored.profileId, cand->controllingProfile)
      << "controlling port should be restored to its original profile";
  XLOG(INFO) << "TEST PASSED";
}

// ---------------------------------------------------------------------------
// Test: delete a portless L3 interface by its interface ID
//
// Programs a VLAN (which brings a backing SVI with it), deletes that SVI by
// bare interface ID, and checks the VLAN goes with it. Covers what no unit
// test can: that a bare ID resolves against a real generated agent.conf and
// that the agent accepts the resulting config.
//
// The refusal paths are unit-tested in CmdDeleteWholeL3InterfaceTestFixture
// and not repeated here. A PORT-type router interface cannot be created
// through the CLI at all, so it could only ever be an IT on a DUT that
// happened to have one.
// ---------------------------------------------------------------------------

TEST_F(DeleteInterfaceTest, DeleteL3InterfaceByIdCascadesVlan) {
  const int vlanId = pickUnusedVlanId();
  ASSERT_NE(vlanId, 0) << "No VLAN ID free in [2, 4094] on this switch";
  // Guards an abort between the commit below and the delete, which would
  // otherwise leave the VLAN and its interface's TUN device on the DUT.
  SCOPE_EXIT {
    deleteVlanIfPresent(vlanId);
  };
  const std::string id = std::to_string(vlanId);

  XLOG(INFO) << "[Step 1] Program VLAN " << id << " and commit";
  auto created = runCli({"config", "vlan", id});
  ASSERT_EQ(created.exitCode, 0) << created.stderr;
  commitConfig();
  waitForAgentReady();

  XLOG(INFO) << "[Step 2] Find the interface backing VLAN " << id;
  auto config = waitForRunningConfig(
      [vlanId](const folly::dynamic& c) { return vlanPresent(c, vlanId); });
  auto intfId = interfaceIdForVlan(config, vlanId);
  ASSERT_TRUE(intfId.has_value())
      << "VLAN " << id << " has no backing interface in the running config";
  XLOG(INFO) << "  interface ID: " << *intfId;

  XLOG(INFO) << "[Step 3] Delete interface " << *intfId << " and commit";
  auto result = runCli({"delete", "interface", std::to_string(*intfId)});
  if (result.exitCode != 0) {
    discardSession();
  }
  ASSERT_EQ(result.exitCode, 0)
      << "stdout=" << result.stdout << " stderr=" << result.stderr;
  commitConfig();
  waitForAgentReady();

  XLOG(INFO) << "[Step 4] Check the interface and VLAN " << id << " are gone";
  config = waitForRunningConfig(
      [vlanId](const folly::dynamic& c) { return vlanGone(c, vlanId); });
  EXPECT_TRUE(vlanGone(config, vlanId))
      << "VLAN " << id << " or its interface still in running config";
  XLOG(INFO) << "TEST PASSED";
}
