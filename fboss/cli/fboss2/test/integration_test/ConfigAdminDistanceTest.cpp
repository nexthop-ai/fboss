/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

/**
 * End-to-end test for:
 *   fboss2-dev config admin-distance <client-id> <distance>
 *
 * Reads the current clientIdToAdminDistance map, picks an existing client,
 * changes its distance, verifies the new value round-trips through the agent's
 * running config (and that the other entries survive), then restores the
 * original. The change is HITLESS so no agent restart is needed between steps.
 */

#include <folly/json/dynamic.h>
#include <folly/logging/xlog.h>
#include <gtest/gtest.h>
#include <map>
#include <string>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

class ConfigAdminDistanceTest : public Fboss2IntegrationTest {
 protected:
  std::map<int, int> getAdminDistances() const {
    std::map<int, int> result;
    auto config = getRunningConfig();
    const auto& sw = config["sw"];
    if (!sw.count("clientIdToAdminDistance")) {
      return result;
    }
    for (const auto& [clientId, distance] :
         sw["clientIdToAdminDistance"].items()) {
      result[folly::to<int>(clientId.asString())] = distance.asInt();
    }
    return result;
  }

  void setAdminDistance(int clientId, int distance) {
    auto result = runCli(
        {"config",
         "admin-distance",
         std::to_string(clientId),
         std::to_string(distance)});
    ASSERT_EQ(result.exitCode, 0)
        << "admin-distance CLI failed: " << result.stderr;
    commitConfig();
  }
};

TEST_F(ConfigAdminDistanceTest, SetAndRestoreAdminDistance) {
  XLOG(INFO) << "[Step 1] Reading current admin distances...";
  auto original = getAdminDistances();
  ASSERT_FALSE(original.empty())
      << "Running config has no clientIdToAdminDistance entries to test with";

  // Derive the target client from the live config rather than hardcoding.
  int clientId = original.begin()->first;
  int originalDistance = original.begin()->second;
  XLOG(INFO) << "  client-id " << clientId << " -> " << originalDistance;

  // Pick a distinct, valid distance in [0, 255].
  int newDistance = (originalDistance == 42) ? 43 : 42;

  XLOG(INFO) << "[Step 2] Setting client-id " << clientId << " to "
             << newDistance << "...";
  setAdminDistance(clientId, newDistance);
  auto updated = getAdminDistances();
  EXPECT_EQ(updated[clientId], newDistance);

  // The other entries must survive untouched.
  for (const auto& [id, distance] : original) {
    if (id != clientId) {
      EXPECT_EQ(updated[id], distance)
          << "client-id " << id << " changed unexpectedly";
    }
  }

  XLOG(INFO) << "[Step 3] Restoring client-id " << clientId << " to "
             << originalDistance << "...";
  setAdminDistance(clientId, originalDistance);
  EXPECT_EQ(getAdminDistances()[clientId], originalDistance);

  XLOG(INFO) << "TEST PASSED";
}
