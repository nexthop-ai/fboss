/**
<<<<<<< HEAD
 * E2E tests for 'fboss2-dev config vlan default <vlan-id>'.
 *
 * SetDefaultVlanTo300: mirrors the production workflow — move ports from the
 *   current default VLAN to a new one, set the default VLAN, commit, then
 *   verify via thrift that defaultVlan in the running config matches the
 *   target. The test then manually restores the original VLAN membership and
 *   defaultVlan via CLI commands and a second commit.
 *
 * ChangeDefaultVlanWithPortInNonDefaultVlan: regression test that ensures the
 *   command does not crash when a port's ingressVlan differs from the current
 *   default VLAN. It also manually restores the original config at the end of
 *   the test via CLI commands and a second commit.
 */

#include <folly/json/dynamic.h>
#include <folly/json/json.h>
#include <folly/logging/xlog.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <string>
#include "fboss/agent/if/gen-cpp2/FbossCtrlAsyncClient.h"
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

using namespace facebook::fboss;

class ConfigVlanDefaultTest : public Fboss2IntegrationTest {
 protected:
  folly::dynamic getRunningConfig() const {
    HostInfo hostInfo("localhost");
    auto client =
        utils::createClient<apache::thrift::Client<FbossCtrl>>(hostInfo);
    std::string configStr;
    client->sync_getRunningConfig(configStr);
    return folly::parseJson(configStr);
  }
};

/**
 * Test setting default VLAN to 300 (or 301 if 300 is already the default).
 * All changes are batched into a single session and committed once — avoids
 * the double-commit / empty-session problem that the two-commit design had.
 * Post-commit verification reads the running config directly via thrift so
 * it doesn't depend on ASIC port-programming completing first.
 */
TEST_F(ConfigVlanDefaultTest, SetDefaultVlanTo300) {
  waitForAgentReady();

  // Pick a target that differs from the current default so the commit is
  // never a no-op.
  auto initialConfig = getRunningConfig();
  int32_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();
  const std::string targetVlan = (currentDefault == 300) ? "301" : "300";
  XLOG(INFO) << "[Test] currentDefault=" << currentDefault
             << " targetVlan=" << targetVlan;

  // Step 1: Move all eth ports whose ingressVlan matches the current default
  // VLAN
  for (const auto& port : initialConfig["sw"]["ports"]) {
    auto name = port.getDefault("name", "").asString();
    if (name.rfind("eth", 0) != 0) {
      continue;
    }
    if (port.getDefault("ingressVlan", currentDefault).asInt() !=
        currentDefault) {
      continue;
    }
    auto result = runCli(
        {"config",
         "interface",
         name,
         "switchport",
         "access",
         "vlan",
         targetVlan});
    if (result.exitCode != 0) {
      XLOG(WARN) << "Skipping " << name << ": " << result.stderr;
      continue;
    }
  }
  // Step 2: Set default VLAN
  auto setResult = runCli({"config", "vlan", "default", targetVlan});
  ASSERT_EQ(setResult.exitCode, 0) << setResult.stderr;
  EXPECT_THAT(
      setResult.stdout,
      ::testing::HasSubstr("Successfully set default VLAN to " + targetVlan));
  XLOG(INFO) << "[Step 2] " << setResult.stdout;

  // Step 3: Single commit — one restart, then wait only for the thrift server
  // to load the config (not full ASIC init, which takes much longer).
  commitConfig();
  waitForAgentReady();
  // Step 4: Verify via running config.
  // sync_getRunningConfig reflects the committed config as soon as the agent
  // loads it, independently of ASIC programming progress.
  auto config = getRunningConfig();
  EXPECT_EQ(config["sw"]["defaultVlan"].asInt(), std::stoi(targetVlan));
  XLOG(INFO) << "[Step 4] Verified defaultVlan="
             << config["sw"]["defaultVlan"].asInt();

  // Restore: move every eth port that originally had ingressVlan ==
  // currentDefault back to its original VLAN, reset defaultVlan, and commit so
  // the next test starts from the original state.
  XLOG(INFO) << "[Restore] Reverting ports and defaultVlan to "
             << currentDefault;
  for (const auto& port : initialConfig["sw"]["ports"]) {
    auto name = port.getDefault("name", "").asString();
    if (name.rfind("eth", 0) != 0) {
      continue;
    }
    auto origVlan = port.getDefault("ingressVlan", currentDefault).asInt();
    if (origVlan != currentDefault) {
      continue;
    }
    auto r = runCli(
        {"config",
         "interface",
         name,
         "switchport",
         "access",
         "vlan",
         std::to_string(origVlan)});
    if (r.exitCode != 0) {
      XLOG(WARN) << "[Restore] Failed to move " << name << " back to VLAN "
                 << origVlan << ": " << r.stderr;
    }
  }

  auto restoreDefault =
      runCli({"config", "vlan", "default", std::to_string(currentDefault)});
  ASSERT_EQ(restoreDefault.exitCode, 0)
      << "[Restore] Failed to reset default VLAN: " << restoreDefault.stderr;

  commitConfig();
  waitForAgentReady();
  discardSession();
}

/**
 * Idempotency test: setting the default VLAN to its current value should be a
 * no-op and return a clear message, without changing the running config.
 */
TEST_F(ConfigVlanDefaultTest, NoOpWhenDefaultVlanUnchanged) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int32_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  auto result =
      runCli({"config", "vlan", "default", std::to_string(currentDefault)});
  ASSERT_EQ(result.exitCode, 0) << result.stderr;
  EXPECT_THAT(
      result.stdout,
      ::testing::HasSubstr(
          "Default VLAN is already set to " + std::to_string(currentDefault)));

  // No commit needed (command is a no-op), but ensure we don't leave a stale
  // session lying around for subsequent tests.
  discardSession();
}

/**
 * Validation guard: if the current default VLAN has at least one port whose
 * ingressVlan equals it but has no matching interface, the command must refuse
 * with a descriptive message and leave the config unchanged.
 *
 * This is the path guarded by `oldVlanUsedAsIngress && !oldVlanHasInterface`
 * in CmdConfigVlanDefault::queryClient.
 *
 * To keep the test simple, we do not try to synthesize this "dangerous" state.
 * Instead, we only run the negative test when the running config already has
 * a default VLAN that is used as ingressVlan by at least one port and has no
 * interface. If those conditions are not met, the test is skipped.
 */
TEST_F(ConfigVlanDefaultTest, RefuseWhenPortOnDefaultVlanWithNoInterface) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int32_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  // Check if any port uses the current default VLAN as its ingressVlan.
  bool portOnDefault = false;
  for (const auto& port : initialConfig["sw"]["ports"]) {
    if (port.getDefault("ingressVlan", currentDefault).asInt() ==
        currentDefault) {
      portOnDefault = true;
      break;
    }
  }
  if (!portOnDefault) {
    GTEST_SKIP() << "No port uses the default VLAN as ingressVlan — cannot "
                    "exercise guard";
  }

  // Check that there is *no* interface mapped to the current default VLAN.
  bool interfaceOnDefault = false;
  if (initialConfig["sw"].count("interfaces")) {
    for (const auto& intf : initialConfig["sw"]["interfaces"]) {
      if (intf.getDefault("vlanID", -1).asInt() == currentDefault) {
        interfaceOnDefault = true;
        break;
      }
    }
  }
  if (interfaceOnDefault) {
    GTEST_SKIP() << "Default VLAN has an interface — dangerous state not "
                    "present";
  }

  // At this point the running config matches the guard's precondition:
  //  - At least one port has ingressVlan == currentDefault
  //  - No interface has vlanID == currentDefault
  // Any attempt to change the default VLAN must be refused.
  const std::string nextVlan = (currentDefault == 300) ? "301" : "300";
  auto result = runCli({"config", "vlan", "default", nextVlan});
  EXPECT_THAT(
      result.stdout, ::testing::HasSubstr("Refusing to change default VLAN"));
  XLOG(INFO) << "[NegativeGuard] stdout='" << result.stdout << "'";

  // Nothing was committed — discard is sufficient to restore state.
  discardSession();
}

/**
 * Regression test: changing the default VLAN must not crash when at least one
 * port has an ingressVlan that differs from the current defaultVlan.
 *
 * Reproduces the crash path where the command iterated over vlans looking for
 * the "default"-named entry and dereferenced a past-the-end iterator when no
 * such entry existed (or when the VLAN table was in an unexpected state).
 *
 * Uses an existing VLAN (one with an interface already mapped) so the VLAN
 * table entry is guaranteed to exist when we set it as the new default.
 */
TEST_F(ConfigVlanDefaultTest, ChangeDefaultVlanWithPortInNonDefaultVlan) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int32_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  // Find a VLAN that exists in the VLAN table and is not the current default —
  // used as the destination when moving ports off the default VLAN.
  int32_t sideVlan = -1;
  for (const auto& vlan : initialConfig["sw"]["vlans"]) {
    int32_t vid = vlan.getDefault("id", -1).asInt();
    if (vid > 0 && vid != currentDefault) {
      sideVlan = vid;
      break;
    }
  }
  if (sideVlan == -1) {
    GTEST_SKIP() << "No VLAN other than the default found in the VLAN table";
  }
  XLOG(INFO) << "currentDefault=" << currentDefault << " sideVlan=" << sideVlan;

  // Step 1: Move every eth port whose ingressVlan == currentDefault to
  // sideVlan. After this, no port has ingressVlan == currentDefault — the exact
  // condition that triggered the past-the-end iterator crash.
  int portsMoved = 0;
  for (const auto& port : initialConfig["sw"]["ports"]) {
    auto name = port.getDefault("name", "").asString();
    if (name.rfind("eth", 0) != 0) {
      continue;
    }
    if (port.getDefault("ingressVlan", currentDefault).asInt() !=
        currentDefault) {
      continue;
    }
    auto r = runCli(
        {"config",
         "interface",
         name,
         "switchport",
         "access",
         "vlan",
         std::to_string(sideVlan)});
    if (r.exitCode == 0) {
      ++portsMoved;
    }
  }
  if (portsMoved == 0) {
    GTEST_SKIP() << "No eth ports on the default VLAN to move";
  }
  XLOG(INFO) << "[Step 1] Moved " << portsMoved << " ports from VLAN "
             << currentDefault << " to " << sideVlan;

  // Step 2: Set a new default VLAN that does not exist in the VLAN table.
  // No port has ingressVlan == currentDefault anymore, so the command must
  // handle the case where the old "default"-named VLAN entry has no ports —
  // this is the condition that caused the past-the-end iterator crash.
  const int32_t newDefault = 4093;
  auto result =
      runCli({"config", "vlan", "default", std::to_string(newDefault)});
  ASSERT_EQ(result.exitCode, 0)
      << "config vlan default crashed: " << result.stderr;
  XLOG(INFO) << "[Step 2] " << result.stdout;

  // Step 3: Commit and verify.
  commitConfig();
  waitForAgentReady();
  auto postCommitConfig = getRunningConfig();
  EXPECT_EQ(postCommitConfig["sw"]["defaultVlan"].asInt(), newDefault);

  // Restore: move every eth port currently on sideVlan back to currentDefault
  // and reset defaultVlan, then commit so the next test starts from the
  // original state.
  XLOG(INFO) << "[Restore] Moving ports from VLAN " << sideVlan << " back to "
             << currentDefault;
  for (const auto& port : postCommitConfig["sw"]["ports"]) {
    auto name = port.getDefault("name", "").asString();
    if (name.rfind("eth", 0) != 0) {
      continue;
    }
    if (port.getDefault("ingressVlan", sideVlan).asInt() != sideVlan) {
      continue;
    }
    auto r = runCli(
        {"config",
         "interface",
         name,
         "switchport",
         "access",
         "vlan",
         std::to_string(currentDefault)});
    if (r.exitCode != 0) {
      XLOG(WARN) << "[Restore] Failed to move " << name << " back to VLAN "
                 << currentDefault << ": " << r.stderr;
    }
  }
||||||| cd4e0b49f5
=======
 * End-to-end tests for 'fboss2-dev config vlan default <vlan-id>'.
 *
 * Covers the happy-path workflow (move ports, set default, commit, verify via
 * thrift), the no-op case when the target equals the current default, a safety
 * guard that refuses the command when the precondition is unsafe, and the case
 * where ports have already been moved off the current default VLAN.
 */

#include <folly/json/dynamic.h>
#include <folly/json/json.h>
#include <folly/logging/xlog.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <string>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

class ConfigVlanDefaultTest : public Fboss2IntegrationTest {};

/**
 * Sets a new default VLAN, commits, verifies via thrift, and restores.
 *
 * CmdConfigVlanDefault::queryClient auto-creates the target VLAN if it
 * doesn't exist, so no manual VLAN creation is needed. We just need to
 * ensure ports on the old default VLAN are moved off first (the command
 * refuses to change when ports use the old default but it has no interface).
 */
TEST_F(ConfigVlanDefaultTest, SetDefaultVlanTo300) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int64_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();
  const std::string targetVlan = (currentDefault == 300) ? "301" : "300";
  XLOG(INFO) << "[Test] currentDefault=" << currentDefault
             << " targetVlan=" << targetVlan;

  // Step 1: Move all eth ports whose ingressVlan matches the current default
  // VLAN to an existing non-default VLAN. This is required because the
  // command refuses to change when ports use the old default but it has no
  // interface (safety guard against agent crash).
  int64_t sideVlan = -1;
  for (const auto& vlan : initialConfig["sw"]["vlans"]) {
    int64_t vid = vlan.getDefault("id", -1).asInt();
    if (vid > 0 && vid != currentDefault) {
      sideVlan = vid;
      break;
    }
  }

  std::vector<std::string> movedPorts;
  if (sideVlan > 0) {
    for (const auto& port : initialConfig["sw"]["ports"]) {
      auto name = port.getDefault("name", "").asString();
      if (name.rfind("eth", 0) != 0) {
        continue;
      }
      if (port.getDefault("ingressVlan", -1).asInt() != currentDefault) {
        continue;
      }
      auto result = runCli(
          {"config",
           "interface",
           name,
           "switchport",
           "access",
           "vlan",
           std::to_string(sideVlan)});
      if (result.exitCode == 0) {
        movedPorts.push_back(name);
      }
    }
  }
  XLOG(INFO) << "[Step 1] Moved " << movedPorts.size()
             << " ports off default VLAN";

  // Step 2: Set default VLAN — the command auto-creates the VLAN if needed
  auto setResult = runCli({"config", "vlan", "default", targetVlan});
  ASSERT_EQ(setResult.exitCode, 0) << setResult.stderr;
  EXPECT_THAT(
      setResult.stdout,
      ::testing::HasSubstr("Successfully set default VLAN to " + targetVlan));
  XLOG(INFO) << "[Step 2] " << setResult.stdout;

  // Step 3: Commit and verify
  commitConfig();
  waitForAgentReady();
  EXPECT_EQ(getSwConfigField<int>("defaultVlan"), std::stoi(targetVlan));
  XLOG(INFO) << "[Step 3] Verified defaultVlan="
             << getSwConfigField<int>("defaultVlan");

  // Restore: move ports back, reset defaultVlan
  XLOG(INFO) << "[Restore] Reverting ports and defaultVlan to "
             << currentDefault;
  for (const auto& name : movedPorts) {
    runCli(
        {"config",
         "interface",
         name,
         "switchport",
         "access",
         "vlan",
         std::to_string(currentDefault)});
  }

  auto restoreDefault =
      runCli({"config", "vlan", "default", std::to_string(currentDefault)});
  ASSERT_EQ(restoreDefault.exitCode, 0)
      << "[Restore] Failed to reset default VLAN: " << restoreDefault.stderr;

  commitConfig();
  waitForAgentReady();
  discardSession();
}

/**
 * Idempotency test: setting the default VLAN to its current value should be a
 * no-op and return a clear message, without changing the running config.
 */
TEST_F(ConfigVlanDefaultTest, NoOpWhenDefaultVlanUnchanged) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int64_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  auto result =
      runCli({"config", "vlan", "default", std::to_string(currentDefault)});
  ASSERT_EQ(result.exitCode, 0) << result.stderr;
  EXPECT_THAT(
      result.stdout,
      ::testing::HasSubstr(
          "Default VLAN is already set to " + std::to_string(currentDefault)));

  // No commit needed (command is a no-op), but ensure we don't leave a stale
  // session lying around for subsequent tests.
  discardSession();
}

/**
 * Validation guard: if the current default VLAN has at least one port whose
 * ingressVlan equals it but has no matching interface, the command must refuse
 * with a descriptive message and leave the config unchanged.
 *
 * This is the path guarded by `oldVlanUsedAsIngress && !oldVlanHasInterface`
 * in CmdConfigVlanDefault::queryClient.
 *
 * The test sets up the precondition by moving an eth port onto the default
 * VLAN using `switchport access vlan`. Since the default VLAN typically has
 * no interface, this creates the "dangerous" state the guard protects against.
 */
TEST_F(ConfigVlanDefaultTest, RefuseWhenPortOnDefaultVlanWithNoInterface) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int64_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  // Check that the default VLAN has no interface (required precondition).
  bool interfaceOnDefault = false;
  if (initialConfig["sw"].count("interfaces")) {
    for (const auto& intf : initialConfig["sw"]["interfaces"]) {
      if (intf.getDefault("vlanID", -1).asInt() == currentDefault) {
        interfaceOnDefault = true;
        break;
      }
    }
  }
  if (interfaceOnDefault) {
    GTEST_SKIP() << "Default VLAN has an interface — dangerous state cannot "
                    "be created";
  }

  // Move one eth port onto the default VLAN to create the precondition.
  auto testPort = findFirstEthInterface();
  int64_t originalPortVlan = -1;
  for (const auto& port : initialConfig["sw"]["ports"]) {
    if (port.getDefault("name", "").asString() == testPort.name) {
      originalPortVlan = port.getDefault("ingressVlan", -1).asInt();
      break;
    }
  }
  ASSERT_NE(originalPortVlan, -1) << "Could not find port " << testPort.name;

  if (originalPortVlan != currentDefault) {
    auto moveResult = runCli(
        {"config",
         "interface",
         testPort.name,
         "switchport",
         "access",
         "vlan",
         std::to_string(currentDefault)});
    ASSERT_EQ(moveResult.exitCode, 0)
        << "Failed to move " << testPort.name
        << " to default VLAN: " << moveResult.stderr;
    XLOG(INFO) << "[Setup] Moved " << testPort.name << " to VLAN "
               << currentDefault;
  }

  // Now the guard should refuse: port on default VLAN, no interface.
  const std::string nextVlan = (currentDefault == 300) ? "301" : "300";
  auto result = runCli({"config", "vlan", "default", nextVlan});
  EXPECT_NE(result.exitCode, 0);
  EXPECT_THAT(
      result.stderr, ::testing::HasSubstr("Refusing to change default VLAN"));
  XLOG(INFO) << "[NegativeGuard] stderr='" << result.stderr << "'";

  // Restore the port to its original VLAN.
  if (originalPortVlan != currentDefault) {
    runCli(
        {"config",
         "interface",
         testPort.name,
         "switchport",
         "access",
         "vlan",
         std::to_string(originalPortVlan)});
  }
  discardSession();
}

/**
 * Verifies that changing the default VLAN succeeds when ports have already
 * been moved off the current default VLAN (ingressVlan != defaultVlan).
 *
 * Sets up the precondition by first moving a port onto the default VLAN,
 * then moving it off to a side VLAN, ensuring at least one port's
 * ingressVlan differs from defaultVlan.
 */
TEST_F(ConfigVlanDefaultTest, ChangeDefaultVlanWithPortInNonDefaultVlan) {
  waitForAgentReady();

  auto initialConfig = getRunningConfig();
  int64_t currentDefault =
      initialConfig["sw"].getDefault("defaultVlan", 1).asInt();

  // Find an existing non-default VLAN to use as the side VLAN.
  int64_t sideVlan = -1;
  for (const auto& vlan : initialConfig["sw"]["vlans"]) {
    int64_t vid = vlan.getDefault("id", -1).asInt();
    if (vid > 0 && vid != currentDefault) {
      sideVlan = vid;
      break;
    }
  }
  if (sideVlan == -1) {
    GTEST_SKIP() << "No VLAN other than the default found in the VLAN table";
  }
  XLOG(INFO) << "currentDefault=" << currentDefault << " sideVlan=" << sideVlan;

  // Pick a test port and record its original VLAN.
  auto testPort = findFirstEthInterface();
  int64_t originalPortVlan = -1;
  for (const auto& port : initialConfig["sw"]["ports"]) {
    if (port.getDefault("name", "").asString() == testPort.name) {
      originalPortVlan = port.getDefault("ingressVlan", -1).asInt();
      break;
    }
  }
  ASSERT_NE(originalPortVlan, -1) << "Could not find port " << testPort.name;

  // Move the port onto the default VLAN first, then off to the side VLAN.
  // This ensures at least one port has ingressVlan != defaultVlan.
  if (originalPortVlan != currentDefault) {
    auto r = runCli(
        {"config",
         "interface",
         testPort.name,
         "switchport",
         "access",
         "vlan",
         std::to_string(currentDefault)});
    ASSERT_EQ(r.exitCode, 0)
        << "Failed to move " << testPort.name << " to default VLAN";
  }
  auto moveOff = runCli(
      {"config",
       "interface",
       testPort.name,
       "switchport",
       "access",
       "vlan",
       std::to_string(sideVlan)});
  ASSERT_EQ(moveOff.exitCode, 0)
      << "Failed to move " << testPort.name << " to side VLAN " << sideVlan;
  XLOG(INFO) << "[Step 1] Moved " << testPort.name << " to VLAN " << sideVlan;

  // Set a new default VLAN — the command must succeed even when no ports
  // remain on the old default VLAN.
  const int64_t newDefault = 4093;
  auto result =
      runCli({"config", "vlan", "default", std::to_string(newDefault)});
  ASSERT_EQ(result.exitCode, 0)
      << "failed to set default VLAN: " << result.stderr;
  XLOG(INFO) << "[Step 2] " << result.stdout;

  // Step 3: Commit and verify.
  commitConfig();
  waitForAgentReady();
  EXPECT_EQ(getSwConfigField<int>("defaultVlan"), newDefault);

  // Restore: move the port back and reset defaultVlan.
  XLOG(INFO) << "[Restore] Moving " << testPort.name << " back to VLAN "
             << originalPortVlan;
  runCli(
      {"config",
       "interface",
       testPort.name,
       "switchport",
       "access",
       "vlan",
       std::to_string(originalPortVlan)});
>>>>>>> fa2cbb1024bde6617e7ebcc238ccc8f618ffc5af

  auto restoreDefault =
      runCli({"config", "vlan", "default", std::to_string(currentDefault)});
  ASSERT_EQ(restoreDefault.exitCode, 0)
      << "[Restore] Failed to reset default VLAN: " << restoreDefault.stderr;

  commitConfig();
  waitForAgentReady();
  discardSession();
}
