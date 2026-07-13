// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
 * End-to-end tests for `fboss2-dev config arp <attr> <value>` commands.
 *
 * Covers the 4 hitless ARP/NDP tunables:
 *   - timeout         -> arpTimeoutSeconds
 *   - age-interval    -> arpAgerInterval
 *   - max-probes      -> maxNeighborProbes
 *   - stale-interval  -> staleEntryInterval
 *
 * Each test runs 6 steps:
 *   1. Read current value from running config + switch state
 *   2. Set a new value via `config arp <attr> <new>`
 *   3. Commit (HITLESS — no agent restart)
 *   4. Verify running config reflects the new value
 *   5. Verify agent switch state reflects the new value
 *   6. Restore original value
 *
 * Requirements:
 *   - FBOSS agent is running with a valid configuration
 *   - Test is run as root (or with sudo) on a DUT
 */

#include <folly/logging/xlog.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <string>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;
using ::testing::HasSubstr;

class ConfigArpTest : public Fboss2IntegrationTest {
 protected:
  void setAndVerify(
      const std::string& attr,
      const std::string& swField,
      const std::string& switchStateField,
      int64_t newValue) {
    XLOG(INFO) << "========================================";
    XLOG(INFO) << "  arp " << attr << " -> " << newValue;
    XLOG(INFO) << "========================================";

    auto originalValue = getSwConfigField<int64_t>(swField);
    XLOG(INFO) << "[Step 1] Original " << swField << " = " << originalValue;
    // Use EXPECT (not ASSERT) so the restore step still runs even if the DUT
    // already has newValue from a prior crashed run. ASSERT would abort here
    // and leave the DUT permanently in the modified state.
    EXPECT_NE(originalValue, newValue)
        << "Test value " << newValue << " must differ from original "
        << originalValue << "; DUT may have been left in modified state by a "
        << "prior crashed run — restore manually if this test keeps failing";

    XLOG(INFO) << "[Step 2] Running: config arp " << attr << " " << newValue;
    auto result = runCli({"config", "arp", attr, std::to_string(newValue)});
    ASSERT_EQ(result.exitCode, 0)
        << "stdout=" << result.stdout << " stderr=" << result.stderr;
    EXPECT_THAT(result.stdout, HasSubstr(attr));

    XLOG(INFO) << "[Step 3] Committing (expect HITLESS, no restart)...";
    commitConfig();

    XLOG(INFO) << "[Step 4] Verifying running config...";
    int64_t observed = getSwConfigField<int64_t>(swField);
    EXPECT_EQ(observed, newValue) << "Expected running config " << swField
                                  << "=" << newValue << ", got " << observed;

    XLOG(INFO) << "[Step 5] Verifying switch state switchSettings."
               << switchStateField << " across all switches";
    verifySwitchSettingsField<int64_t>(switchStateField, newValue);

    XLOG(INFO) << "[Step 6] Restoring original value " << originalValue;
    result = runCli({"config", "arp", attr, std::to_string(originalValue)});
    ASSERT_EQ(result.exitCode, 0) << result.stderr;
    commitConfig();
    EXPECT_EQ(getSwConfigField<int64_t>(swField), originalValue);
    verifySwitchSettingsField<int64_t>(switchStateField, originalValue);

    XLOG(INFO) << "  PASSED: " << attr;
  }
};

TEST_F(ConfigArpTest, SetTimeout) {
  setAndVerify("timeout", "arpTimeoutSeconds", "arpTimeout", 75);
}

TEST_F(ConfigArpTest, SetAgeInterval) {
  setAndVerify("age-interval", "arpAgerInterval", "arpAgerInterval", 8);
}

TEST_F(ConfigArpTest, SetMaxProbes) {
  setAndVerify("max-probes", "maxNeighborProbes", "maxNeighborProbes", 250);
}

TEST_F(ConfigArpTest, SetStaleInterval) {
  setAndVerify(
      "stale-interval", "staleEntryInterval", "staleEntryInterval", 15);
}
