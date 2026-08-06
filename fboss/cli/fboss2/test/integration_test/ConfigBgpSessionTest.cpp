// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end tests for BGP config *session* management, mirroring the agent
 * config session tests (e.g. ConfigSessionClearTest) but for the BGP domain.
 *
 * BGP global edits stage ~/.fboss2/bgp_config.json (no agent.conf), and
 * `config session commit` promotes it to /etc/coop/bgpcpp/bgpcpp.conf and
 * restarts bgpd. These tests exercise the session lifecycle around that:
 *   - commit (bgpd is restarted)
 *   - commit of an unchanged config (no restart)
 *   - rollback (the bgpd system config is restored)
 *
 * Per-attribute global config behavior lives in ConfigBgpGlobalTest. Each
 * test restores whatever it committed (the graceful-restart timer, an
 * interface description) as its final step, so the suite leaves the DUT's
 * config as it found it.
 *
 * Requirements:
 *   - The fboss2-dev binary under test (config subcommand tree).
 *   - HOME is set (the session file lives under $HOME/.fboss2).
 *   - bgpd installed; commit/rollback tests skip if bgpd is not active.
 */

#include <gtest/gtest.h>
#include <filesystem>
#include <string>

#include "fboss/cli/fboss2/test/integration_test/ConfigBgpTestBase.h"

namespace fs = std::filesystem;

using namespace facebook::fboss;
using ::testing::HasSubstr;

class ConfigBgpSessionTest : public ConfigBgpTestBase {};

// Committing a staged BGP change restarts the bgpd daemon.
TEST_F(ConfigBgpSessionTest, CommitRestartsBgpDaemon) {
  if (bgpDaemonActiveState() != "active") {
    GTEST_SKIP() << "bgpd is not active on this DUT; skipping commit/restart "
                    "verification";
  }
  discardSession();
  // Capture the original graceful-restart time (absent = 120, what the
  // shipped bgpcpp.conf sets); restored at the end.
  const int64_t original =
      readSystemBgpConfig()
          .getDefault("graceful_restart_convergence_seconds", 120)
          .asInt();
  const std::string pidBefore = bgpDaemonMainPid();

  runBgpGlobal("graceful-restart-time", "123");
  ASSERT_FALSE(commitAndGetSha().empty());

  EXPECT_TRUE(waitForBgpDaemonActive())
      << "bgpd did not return to active after commit; state="
      << bgpDaemonActiveState();

  const std::string pidAfter = bgpDaemonMainPid();
  EXPECT_NE(pidAfter, "0") << "bgpd has no MainPID after commit";
  EXPECT_NE(pidAfter, pidBefore) << "bgpd MainPID unchanged (" << pidBefore
                                 << "); expected a restart on commit";

  // Restore the pre-test graceful-restart time.
  setAndCommit("graceful-restart-time", std::to_string(original));
}

// Rolling back a committed BGP change restores the bgpd system config and
// restarts bgpd (not just the agent config).
TEST_F(ConfigBgpSessionTest, RollbackRestoresBgpConfig) {
  if (bgpDaemonActiveState() != "active") {
    GTEST_SKIP() << "bgpd is not active on this DUT; skipping rollback "
                    "verification";
  }
  discardSession();
  // Capture the original graceful-restart time (absent = 120, what the
  // shipped bgpcpp.conf sets); restored at the end.
  const int64_t original =
      readSystemBgpConfig()
          .getDefault("graceful_restart_convergence_seconds", 120)
          .asInt();

  auto convergenceSeconds = [&]() {
    return readSystemBgpConfig()["graceful_restart_convergence_seconds"]
        .asInt();
  };

  // Commit A (111), then commit B (222).
  runBgpGlobal("graceful-restart-time", "111");
  std::string shaA = commitAndGetSha();
  ASSERT_FALSE(shaA.empty()) << "could not parse commit A sha";
  ASSERT_TRUE(waitForBgpDaemonActive());

  runBgpGlobal("graceful-restart-time", "222");
  ASSERT_FALSE(commitAndGetSha().empty()) << "could not parse commit B sha";
  ASSERT_TRUE(waitForBgpDaemonActive());

  EXPECT_EQ(convergenceSeconds(), 222)
      << "system bgp config should reflect the latest commit";

  // Roll back to commit A -> system bgp config restored to 111, bgpd restart.
  resetBgpDaemonLimit(); // avoid systemd start-limit on the rollback's restart
  auto rb = runCli({"config", "rollback", shaA});
  EXPECT_EQ(rb.exitCode, 0) << "stderr=" << rb.stderr;
  ASSERT_TRUE(waitForBgpDaemonActive())
      << "bgpd did not return active after rollback";

  EXPECT_EQ(convergenceSeconds(), 111)
      << "rollback must restore the bgpd system config";

  // Restore the pre-test graceful-restart time.
  setAndCommit("graceful-restart-time", std::to_string(original));
}

// Committing a BGP config identical to what is already running must be a no-op:
// "Nothing to commit" and, crucially, NO bgpd restart (a restart is traffic
// affecting). saveBgpConfig() always records BGP_RESTART, so commit() has to
// compare the staged config against the running one.
TEST_F(ConfigBgpSessionTest, CommitUnchangedBgpConfigDoesNotRestart) {
  if (bgpDaemonActiveState() != "active") {
    GTEST_SKIP() << "bgpd is not active on this DUT; skipping no-op restart "
                    "verification";
  }
  discardSession();
  // Capture the original graceful-restart time (absent = 120, what the
  // shipped bgpcpp.conf sets); restored at the end.
  const int64_t original =
      readSystemBgpConfig()
          .getDefault("graceful_restart_convergence_seconds", 120)
          .asInt();

  // Establish a known running value.
  runBgpGlobal("graceful-restart-time", "88");
  ASSERT_FALSE(commitAndGetSha().empty());
  ASSERT_TRUE(waitForBgpDaemonActive());
  const std::string pidBefore = bgpDaemonMainPid();
  ASSERT_NE(pidBefore, "0");

  // Stage the SAME value and commit again -> nothing to commit, no restart.
  runBgpGlobal("graceful-restart-time", "88");
  auto result = runCli({"config", "session", "commit"});
  EXPECT_EQ(result.exitCode, 0) << "stderr=" << result.stderr;
  EXPECT_THAT(result.stdout, HasSubstr("Nothing to commit"))
      << "an unchanged BGP commit should report nothing to commit";

  EXPECT_EQ(bgpDaemonMainPid(), pidBefore)
      << "bgpd was restarted for an unchanged BGP config (pidBefore="
      << pidBefore << ")";

  // Restore the pre-test graceful-restart time.
  setAndCommit("graceful-restart-time", std::to_string(original));
}

// An agent-only commit (no BGP staged) must still snapshot the running bgpd
// config, so a rollback to it restores BGP instead of wiping it. Pre-fix,
// bgpcpp.conf was untracked at such commits and rollback deleted it.
TEST_F(ConfigBgpSessionTest, AgentCommitSnapshotsBgpAndRollbackPreservesIt) {
  if (bgpDaemonActiveState() != "active") {
    GTEST_SKIP() << "bgpd is not active on this DUT; skipping cross-domain "
                    "rollback verification";
  }
  discardSession();
  clearBgpSession();

  // The running (default) BGP config that must survive a rollback unchanged.
  ASSERT_TRUE(fs::exists(systemBgpConfigPath()))
      << "expected a running bgpd config on an active-BGP DUT";
  const folly::dynamic defaultBgp = readSystemBgpConfig();

  // Step 1: an agent-only commit (interface description). No BGP is staged.
  Interface intf = getInterfaceInfo(getRandomInterfacePortName());
  const std::string originalDescription = intf.description;
  auto setRes =
      runCli({"config", "interface", intf.name, "description", "bgp-rb-test"});
  ASSERT_EQ(setRes.exitCode, 0) << "stderr=" << setRes.stderr;
  ASSERT_FALSE(fs::exists(bgpSessionPath()))
      << "an interface-description change must not stage a BGP session";
  resetBgpDaemonLimit();
  commitConfig();
  waitForAgentReady();
  const std::string agentSha = gitHead();
  ASSERT_FALSE(agentSha.empty())
      << "could not read git HEAD after agent commit";

  // The fix: bgpcpp.conf must be tracked at the agent-only commit, so a later
  // rollback to it has a faithful BGP snapshot to restore.
  EXPECT_TRUE(bgpTrackedAtRevision(agentSha))
      << "agent-only commit " << agentSha
      << " did not snapshot bgpcpp.conf; a rollback to it would wipe BGP";

  // Step 2: stage + commit a BGP change so the running config diverges from the
  // snapshot captured at agentSha.
  runBgpGlobal("graceful-restart-time", "222");
  ASSERT_FALSE(commitAndGetSha().empty()) << "BGP commit produced no SHA";
  ASSERT_TRUE(waitForBgpDaemonActive());
  EXPECT_EQ(
      readSystemBgpConfig()["graceful_restart_convergence_seconds"].asInt(),
      222);

  // Step 3: roll back to the agent-only commit. BGP must be RESTORED to the
  // original default snapshot (not deleted), and bgpd must come back.
  resetBgpDaemonLimit();
  auto rb = runCli({"config", "rollback", agentSha});
  EXPECT_EQ(rb.exitCode, 0) << "stderr=" << rb.stderr;
  ASSERT_TRUE(waitForBgpDaemonActive())
      << "bgpd did not return active after rollback";

  EXPECT_TRUE(fs::exists(systemBgpConfigPath()))
      << "rollback to an agent-era commit wiped the running bgpd config";
  EXPECT_EQ(readSystemBgpConfig(), defaultBgp)
      << "rollback did not restore the original (default) bgpd config";

  // Step 4: restore the interface description set in step 1 (the rollback
  // target agentSha still contains it). The BGP change from step 2 was
  // already reverted by the step-3 rollback, as asserted above.
  auto restoreRes = runCli(
      {"config", "interface", intf.name, "description", originalDescription});
  EXPECT_EQ(restoreRes.exitCode, 0) << "stderr=" << restoreRes.stderr;
  commitConfig();
  waitForAgentReady();
}
