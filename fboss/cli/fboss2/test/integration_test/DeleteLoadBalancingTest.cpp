// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end test for `fboss2-dev delete load-balancing ecmp`:
 *   check the running config has an ECMP load-balancer → delete → check gone.
 * TearDown restores the original config with a cold boot.
 *
 * Re-adding the entry through `config load-balancing ecmp` is
 * ConfigLoadBalancingTest's coverage. The lag subcommand shares the removal
 * implementation and is covered by CmdDeleteLoadBalancing unit tests.
 *
 * Requirements:
 *   - FBOSS agent is running with a valid configuration that already contains
 *     an ECMP load balancer entry (true for every real DUT)
 */

#include <folly/logging/xlog.h>
#include <gtest/gtest.h>
#include <string>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"
#include "folly/json/dynamic.h"

using namespace facebook::fboss;

namespace {

constexpr int kEcmpIdValue = 1;

} // namespace

class DeleteLoadBalancingTest : public Fboss2IntegrationTest {
 protected:
  // Returns the load balancer entry with the given id, or nullptr.
  static const folly::dynamic* findLoadBalancer(
      const folly::dynamic& config,
      int idValue) {
    if (!config.isObject() || !config.count("sw") ||
        !config["sw"].count("loadBalancers")) {
      return nullptr;
    }
    for (const auto& lb : config["sw"]["loadBalancers"]) {
      if (lb.count("id") && lb["id"].asInt() == idValue) {
        return &lb;
      }
    }
    return nullptr;
  }

  void SetUp() override {
    Fboss2IntegrationTest::SetUp();
    configSnapshotJson_ = snapshotConfig();
  }

  void TearDown() override {
    try {
      restoreConfig(
          configSnapshotJson_,
          cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);
    } catch (const std::exception& e) {
      XLOG(ERR) << "TearDown: failed to restore config snapshot: " << e.what();
    }
    Fboss2IntegrationTest::TearDown();
  }

 private:
  // Full config captured in SetUp, restored in TearDown.
  std::string configSnapshotJson_;
};

TEST_F(DeleteLoadBalancingTest, DeleteThenRestoreEcmp) {
  XLOG(INFO) << "[Step 1] Check the running config has an ECMP load-balancer";
  ASSERT_NE(findLoadBalancer(getRunningConfig(), kEcmpIdValue), nullptr)
      << "no ECMP load balancer in running config";

  XLOG(INFO) << "[Step 2] Delete the ECMP load-balancer and commit";
  auto result = runCli({"delete", "load-balancing", "ecmp"});
  ASSERT_EQ(result.exitCode, 0)
      << "stdout=" << result.stdout << " stderr=" << result.stderr;
  commitConfig();
  waitForAgentReady();

  XLOG(INFO) << "[Step 3] Check the ECMP load-balancer is gone";
  auto config = waitForRunningConfig([&](const folly::dynamic& c) {
    return findLoadBalancer(c, kEcmpIdValue) == nullptr;
  });
  EXPECT_EQ(findLoadBalancer(config, kEcmpIdValue), nullptr)
      << "ECMP load balancer still in running config";
  // TearDown restores the original ECMP load-balancer.
}
