// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end tests for `fboss2-dev config protocol bgp global <attr> <value>`.
 *
 * Scope: the BGP *global* tunables only. Each positive test stages the change
 * AND commits it, then asserts the value landed at the correct thrift field
 * path in bgpd's own running config — fetched over its getRunningConfig RPC
 * (see ConfigBgpTestBase::setAndCommit) — which proves the daemon parsed and
 * adopted the promoted /etc/coop/bgpcpp/bgpcpp.conf after the commit-triggered
<<<<<<< HEAD
 * restart, not merely that the CLI wrote the file. Each test then restores
 * the attribute to its pre-test value as its final step, so the suite leaves
 * the DUT's BGP config as it found it. Session-lifecycle behavior
 * (clear / diff / rollback / commit-restart mechanics) lives in
 * ConfigBgpSessionTest.
 *
 *   - count-confeds-in-as-path-len <true|false>
 *       -> BgpConfig.count_confeds_in_as_path_len
 *   - graceful-restart-time <seconds>
 *       -> BgpConfig.graceful_restart_convergence_seconds
 *   - rib-allocated-path-ids <true|false>
 *       -> BgpConfig.bgp_setting_config.enable_rib_allocated_path_id
 *
 * Requirements:
 *   - The fboss2-dev binary under test (config subcommand tree).
 *   - HOME is set (the session file lives under $HOME/.fboss2).
 *   - bgpd is installed/active (commit restarts it).
 */

#include <gtest/gtest.h>
#include <string>

#include "fboss/cli/fboss2/test/integration_test/ConfigBgpTestBase.h"

using namespace facebook::fboss;

class ConfigBgpGlobalTest : public ConfigBgpTestBase {};

TEST_F(ConfigBgpGlobalTest, SetCountConfedsInAsPathLenTrue) {
  // Capture the original value (absent = the daemon's default, false).
  const bool original = readSystemBgpConfig()
                            .getDefault("count_confeds_in_as_path_len", false)
                            .asBool();
  auto config = setAndCommit("count-confeds-in-as-path-len", "true");
  ASSERT_TRUE(config.count("count_confeds_in_as_path_len"));
  EXPECT_TRUE(config["count_confeds_in_as_path_len"].asBool());
  // Restore the pre-test value.
  setAndCommit("count-confeds-in-as-path-len", original ? "true" : "false");
}

TEST_F(ConfigBgpGlobalTest, SetCountConfedsInAsPathLenFalse) {
  // Capture the original value (absent = the daemon's default, false).
  const bool original = readSystemBgpConfig()
                            .getDefault("count_confeds_in_as_path_len", false)
                            .asBool();
  auto config = setAndCommit("count-confeds-in-as-path-len", "false");
  ASSERT_TRUE(config.count("count_confeds_in_as_path_len"));
  EXPECT_FALSE(config["count_confeds_in_as_path_len"].asBool());
  // Restore the pre-test value.
  setAndCommit("count-confeds-in-as-path-len", original ? "true" : "false");
}

TEST_F(ConfigBgpGlobalTest, SetGracefulRestartTime) {
  // Capture the original value (absent = 120, what the shipped bgpcpp.conf
  // sets), restored at the end.
  const int64_t original =
      readSystemBgpConfig()
          .getDefault("graceful_restart_convergence_seconds", 120)
          .asInt();
  // Stage a value that differs from the current system config: committing an
  // unchanged config is a no-op that yields no SHA.
  const int64_t target = original == 120 ? 121 : 120;
  auto config = setAndCommit("graceful-restart-time", std::to_string(target));
  ASSERT_TRUE(config.count("graceful_restart_convergence_seconds"));
  EXPECT_EQ(config["graceful_restart_convergence_seconds"].asInt(), target);
  // Must not write the per-peer timer field name.
  EXPECT_FALSE(config.count("graceful_restart_seconds"));
  // Restore the pre-test value.
  setAndCommit("graceful-restart-time", std::to_string(original));
}

TEST_F(ConfigBgpGlobalTest, SetRibAllocatedPathIdsTrue) {
  // Capture the original value (absent = the daemon's default, false).
  const bool original =
      readSystemBgpConfig()
          .getDefault("bgp_setting_config", folly::dynamic::object)
          .getDefault("enable_rib_allocated_path_id", false)
          .asBool();
  auto config = setAndCommit("rib-allocated-path-ids", "true");
  ASSERT_TRUE(config.count("bgp_setting_config"));
  ASSERT_TRUE(
      config["bgp_setting_config"].count("enable_rib_allocated_path_id"));
  EXPECT_TRUE(
      config["bgp_setting_config"]["enable_rib_allocated_path_id"].asBool());
  // Must be nested, not at the top level.
  EXPECT_FALSE(config.count("enable_rib_allocated_path_id"));
  // Restore the pre-test value.
  setAndCommit("rib-allocated-path-ids", original ? "true" : "false");
}

TEST_F(ConfigBgpGlobalTest, SetRibAllocatedPathIdsFalse) {
  // Capture the original value (absent = the daemon's default, false).
  const bool original =
      readSystemBgpConfig()
          .getDefault("bgp_setting_config", folly::dynamic::object)
          .getDefault("enable_rib_allocated_path_id", false)
          .asBool();
  auto config = setAndCommit("rib-allocated-path-ids", "false");
  ASSERT_TRUE(config.count("bgp_setting_config"));
  ASSERT_TRUE(
      config["bgp_setting_config"].count("enable_rib_allocated_path_id"));
  EXPECT_FALSE(
      config["bgp_setting_config"]["enable_rib_allocated_path_id"].asBool());
  // Restore the pre-test value.
  setAndCommit("rib-allocated-path-ids", original ? "true" : "false");
||||||| a86baef3b7
=======
 * restart, not merely that the CLI wrote the file. Session-lifecycle behavior
 * (clear / diff / rollback / commit-restart mechanics) lives in
 * ConfigBgpSessionTest.
 *
 *   - count-confeds-in-as-path-len <true|false>
 *       -> BgpConfig.count_confeds_in_as_path_len
 *   - graceful-restart-time <seconds>
 *       -> BgpConfig.graceful_restart_convergence_seconds
 *   - rib-allocated-path-ids <true|false>
 *       -> BgpConfig.bgp_setting_config.enable_rib_allocated_path_id
 *   - switch-limit-overload-protection-mode <mode>
 *       -> BgpConfig.switch_limit_config.overload_protection_mode
 *
 * Requirements:
 *   - The fboss2-dev binary under test (config subcommand tree).
 *   - HOME is set (the session file lives under $HOME/.fboss2).
 *   - bgpd is installed/active (commit restarts it).
 */

#include <gtest/gtest.h>
#include <filesystem>
#include <string>

#include "fboss/cli/fboss2/test/integration_test/ConfigBgpTestBase.h"

using namespace facebook::fboss;
using ::testing::HasSubstr;

class ConfigBgpGlobalTest : public ConfigBgpTestBase {};

TEST_F(ConfigBgpGlobalTest, SetCountConfedsInAsPathLenTrue) {
  auto config = setAndCommit("count-confeds-in-as-path-len", "true");
  ASSERT_TRUE(config.count("count_confeds_in_as_path_len"));
  EXPECT_TRUE(config["count_confeds_in_as_path_len"].asBool());
}

TEST_F(ConfigBgpGlobalTest, SetCountConfedsInAsPathLenFalse) {
  auto config = setAndCommit("count-confeds-in-as-path-len", "false");
  ASSERT_TRUE(config.count("count_confeds_in_as_path_len"));
  EXPECT_FALSE(config["count_confeds_in_as_path_len"].asBool());
}

TEST_F(ConfigBgpGlobalTest, SetGracefulRestartTime) {
  // Stage a value that differs from the current system config: committing an
  // unchanged config is a no-op that yields no SHA, and the shipped
  // bgpcpp.conf already sets 120.
  int64_t target = 120;
  try {
    auto current = readSystemBgpConfig();
    if (current.count("graceful_restart_convergence_seconds") &&
        current["graceful_restart_convergence_seconds"].asInt() == target) {
      target = 121;
    }
  } catch (const std::exception&) {
    // No readable system config yet — any value is a change.
  }
  auto config = setAndCommit("graceful-restart-time", std::to_string(target));
  ASSERT_TRUE(config.count("graceful_restart_convergence_seconds"));
  EXPECT_EQ(config["graceful_restart_convergence_seconds"].asInt(), target);
  // Must not write the per-peer timer field name.
  EXPECT_FALSE(config.count("graceful_restart_seconds"));
}

TEST_F(ConfigBgpGlobalTest, SetRibAllocatedPathIdsTrue) {
  auto config = setAndCommit("rib-allocated-path-ids", "true");
  ASSERT_TRUE(config.count("bgp_setting_config"));
  ASSERT_TRUE(
      config["bgp_setting_config"].count("enable_rib_allocated_path_id"));
  EXPECT_TRUE(
      config["bgp_setting_config"]["enable_rib_allocated_path_id"].asBool());
  // Must be nested, not at the top level.
  EXPECT_FALSE(config.count("enable_rib_allocated_path_id"));
}

TEST_F(ConfigBgpGlobalTest, SetRibAllocatedPathIdsFalse) {
  auto config = setAndCommit("rib-allocated-path-ids", "false");
  ASSERT_TRUE(config.count("bgp_setting_config"));
  ASSERT_TRUE(
      config["bgp_setting_config"].count("enable_rib_allocated_path_id"));
  EXPECT_FALSE(
      config["bgp_setting_config"]["enable_rib_allocated_path_id"].asBool());
}

TEST_F(ConfigBgpGlobalTest, InvalidBoolValueRejected) {
  clearBgpSession();
  auto result = runCli(
      {"config",
       "protocol",
       "bgp",
       "global",
       "count-confeds-in-as-path-len",
       "maybe"});
  // The handler reports the error on stdout; ensure it did not silently
  // succeed and persist a bogus value.
  EXPECT_THAT(result.stdout, HasSubstr("Invalid value"));
  // The handler must bail out before saving, so no session file is written for
  // the rejected input.
  EXPECT_FALSE(std::filesystem::exists(bgpSessionPath()))
      << "session file should not exist after rejected input";
}

TEST_F(ConfigBgpGlobalTest, RouterIdInvalidRejected) {
  clearBgpSession();
  auto result =
      runCli({"config", "protocol", "bgp", "global", "router-id", "not-an-ip"});
  EXPECT_THAT(result.stdout, HasSubstr("Invalid router-id address"));
  EXPECT_FALSE(std::filesystem::exists(bgpSessionPath()))
      << "session file should not exist after rejected input";
}

TEST_F(ConfigBgpGlobalTest, RouterIdV6Rejected) {
  clearBgpSession();
  auto result = runCli(
      {"config", "protocol", "bgp", "global", "router-id", "2001:db8::1"});
  EXPECT_THAT(result.stdout, HasSubstr("requires an IPv4 address"));
  EXPECT_FALSE(std::filesystem::exists(bgpSessionPath()))
      << "session file should not exist after rejected input";
}

TEST_F(ConfigBgpGlobalTest, OverloadProtectionModeOutOfRangeRejected) {
  clearBgpSession();
  auto result = runCli(
      {"config",
       "protocol",
       "bgp",
       "global",
       "switch-limit-overload-protection-mode",
       "999"});
  EXPECT_THAT(result.stdout, HasSubstr("is not a valid mode"));
  EXPECT_THAT(result.stdout, HasSubstr("APPLY_GOLDEN_PREFIX_POLICY"));
  EXPECT_FALSE(std::filesystem::exists(bgpSessionPath()))
      << "session file should not exist after rejected input";
}

TEST_F(ConfigBgpGlobalTest, SetOverloadProtectionModeAndCommit) {
  auto config = setAndCommit("switch-limit-overload-protection-mode", "2");
  ASSERT_TRUE(config.count("switch_limit_config"));
  ASSERT_TRUE(config["switch_limit_config"].count("overload_protection_mode"));
  EXPECT_EQ(
      config["switch_limit_config"]["overload_protection_mode"].asInt(), 2);
}

TEST_F(ConfigBgpGlobalTest, NegativeGracefulRestartTimeRejected) {
  clearBgpSession();
  auto result = runCli(
      {"config", "protocol", "bgp", "global", "graceful-restart-time", "-1"});
  EXPECT_THAT(result.stdout, HasSubstr("non-negative"));
  EXPECT_FALSE(std::filesystem::exists(bgpSessionPath()))
      << "session file should not exist after rejected input";
>>>>>>> 7645153f2671a8414e17f720188a6810f8fcc177
}
