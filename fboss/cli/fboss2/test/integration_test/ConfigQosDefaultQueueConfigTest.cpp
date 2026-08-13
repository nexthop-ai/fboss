// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

/**
<<<<<<< HEAD
 * End-to-end tests for:
 *   fboss2-dev config qos default-queue-config <queue-id> <attr> <value> ...
 *   fboss2-dev delete qos default-queue-config <queue-id>
||||||| d33cd384af
 * End-to-end test for:
 *   fboss2-dev config qos default-queue-config <queue-id> <attr> <value> ...
 *   fboss2-dev delete qos default-queue-config <queue-id>
=======
 * End-to-end tests for the switch-wide default queue config:
 *   fboss2-dev config qos queue-config default queue-id <id> <attr> <value> ...
 *   fboss2-dev delete qos queue-config default [queue-id <id>]
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37
 *
<<<<<<< HEAD
 * Reads the agent's live defaultPortQueues, modifies an existing queue's
 * weight, commits, verifies, and restores the original value. The delete
 * tests create a new queue entry, remove it again, and verify the running
 * config after each commit, leaving the device at its original config.
||||||| d33cd384af
 * One happy path, covering only what cannot be checked off-device: that a
 * committed config session survives the agent restart and lands in the running
 * config, and that delete takes it back out.
 *
 * Everything else already has coverage a layer down. Argument parsing,
 * attribute handling and rejection of malformed input are unit tested in
 * fboss/cli/fboss2/test/config/CmdConfigQosDefaultQueueConfigTest.cpp against a
 * seeded ConfigSession; whether the agent accepts a given cfg::PortQueue is
 * covered by fboss/agent/state/tests/PortQueueTests.cpp against the real
 * ThriftConfigApplier. Neither needs a device.
 *
 * Both commands commit at ConfigActionLevel::AGENT_COLDBOOT, so each commit
 * restarts the agent. Keep the test to the two restarts it already needs.
=======
 * `default` is the reserved queue-config name that targets
 * SwitchConfig::defaultPortQueues rather than a portQueueConfigs entry; the
 * named-config path is covered by ConfigPortQueueConfigTest.
 *
 * Each case configures one realistic queue shape rather than one queue with
 * every attribute at once, so a failure names the scheduling discipline that
 * broke instead of pointing at a single kitchen-sink queue. Only what cannot be
 * checked off-device is covered here: that a committed config session survives
 * the agent restart and lands in the running config.
 *
 * Everything else already has coverage a layer down. Argument parsing,
 * attribute handling and rejection of malformed input are unit tested in
 * fboss/cli/fboss2/test/config/CmdConfigQosQueueConfigTest.cpp against a
 * seeded ConfigSession; whether the agent accepts a given cfg::PortQueue is
 * covered by fboss/agent/state/tests/PortQueueTests.cpp against the real
 * ThriftConfigApplier. Neither needs a device.
 *
 * Every commit restarts the agent, so each case commits once to apply and once
 * to clean up, and no case programs more than one queue.
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37
 */

#include <fmt/format.h>
#include <folly/json/dynamic.h>
#include <folly/logging/xlog.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <optional>
#include <set>
#include <string>
#include <vector>
#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;

namespace {
// Enum values from switch_config.thrift
constexpr int kSchedWrr = 0;
constexpr int kSchedSp = 1;
constexpr int kScalingTwo = 9;
constexpr int kBehaviorEcn = 1;

// defaultPortQueues applies to every port with no portQueueConfigName
// override, so these cases deliberately stay away from the large MMU numbers
// ConfigPortQueueConfigTest uses on a single bound interface -- the point is to
// prove each attribute survives the CLI -> agent.conf -> ThriftConfigApplier
// round trip, not to exercise buffer capacity fleet-wide. buffer-pool-name is
// skipped because it would require creating a pool first.
constexpr int kReservedBytes = 1024;
constexpr int kWeight = 5;
constexpr int kAqmMinLength = 40000;
constexpr int kAqmMaxLength = 60000;
constexpr int kAqmProbability = 100;
} // namespace

class ConfigQosDefaultQueueConfigTest : public Fboss2IntegrationTest {
 protected:
  void SetUp() override {
    Fboss2IntegrationTest::SetUp();
    discardSession();
    baselineIds_ = defaultQueueIds(getRunningConfig());
  }

  void TearDown() override {
    // Safety net: an assertion that fires mid-case skips the case's own
    // cleanup, and the queue is already committed to the running config of a
    // shared lab device. Remove it here so the next case (and the next run)
    // starts from the baseline.
    if (createdQueueId_.has_value()) {
      XLOG(INFO) << "TearDown: removing leftover queue-id " << *createdQueueId_;
      deleteQueueAndCommit(*createdQueueId_);
    }
    discardSession();
    Fboss2IntegrationTest::TearDown();
  }

  /**
   * Lowest queue id not already present in defaultPortQueues. Keeps each case
   * independent of how many queues the ASIC already has configured, including
   * none at all.
   */
  int pickUnusedQueueId() const {
    int candidate = 0;
    while (baselineIds_.count(candidate)) {
      candidate++;
    }
    return candidate;
  }

  /**
   * Configure `queueId` with `attrs` and commit. Records the id so TearDown can
   * remove it even if the caller's assertions fail. Returns the queue as it
   * appears in the agent's running config.
   */
  const folly::dynamic* configureAndCommit(
      int queueId,
      const std::vector<std::string>& attrs) {
    std::vector<std::string> cmd = {
        "config",
        "qos",
        "queue-config",
        "default",
        "queue-id",
        std::to_string(queueId)};
    cmd.insert(cmd.end(), attrs.begin(), attrs.end());

    auto result = runCli(cmd);
    EXPECT_EQ(result.exitCode, 0)
        << "queue-id " << queueId << " failed: " << result.stderr;
    if (result.exitCode != 0) {
      return nullptr;
    }
    createdQueueId_ = queueId;

    XLOG(INFO) << "Committing queue-id " << queueId << "...";
    commitConfig();
    waitForAgentReady();

    runningConfig_ = getRunningConfig();
    return findQueueById(runningConfig_, queueId);
  }

  void deleteQueueAndCommit(int queueId) {
    discardSession();
    auto del = runCli(
        {"delete",
         "qos",
         "queue-config",
         "default",
         "queue-id",
         std::to_string(queueId)});
    EXPECT_EQ(del.exitCode, 0) << "CLI failed: " << del.stderr;
    createdQueueId_.reset();

    XLOG(INFO) << "Committing delete of queue-id " << queueId << "...";
    commitConfig();
    waitForAgentReady();
  }

  /**
   * Return the defaultPortQueues entry with the given queue id as a
   * folly::dynamic object, or nullptr if no such entry exists.
   */
  const folly::dynamic* findQueueById(const folly::dynamic& config, int queueId)
      const {
    if (!config.isObject() || !config.count("sw") ||
        !config["sw"].count("defaultPortQueues")) {
      return nullptr;
    }
    const auto& queues = config["sw"]["defaultPortQueues"];
    if (!queues.isArray()) {
      return nullptr;
    }
    for (const auto& q : queues) {
      if (q.count("id") && q["id"].asInt() == queueId) {
        return &q;
      }
    }
    return nullptr;
  }

  /**
   * Return the set of queue ids present in the running config's
   * defaultPortQueues, or an empty set if the list is absent.
   */
  std::set<int> defaultQueueIds(const folly::dynamic& config) const {
    std::set<int> ids;
    if (!config.isObject() || !config.count("sw") ||
        !config["sw"].count("defaultPortQueues")) {
      return ids;
    }
    const auto& queues = config["sw"]["defaultPortQueues"];
    if (!queues.isArray()) {
      return ids;
    }
    for (const auto& q : queues) {
      if (q.count("id")) {
        ids.insert(q["id"].asInt());
      }
    }
    return ids;
  }

  std::set<int> baselineIds_;
  std::optional<int> createdQueueId_;
  // Owns the storage the folly::dynamic* returned by configureAndCommit()
  // points into.
  folly::dynamic runningConfig_;
};

<<<<<<< HEAD
TEST_F(ConfigQosDefaultQueueConfigTest, SetWeightOnDefaultQueue) {
  XLOG(INFO) << "ConfigQosDefaultQueueConfigTest::SetWeightOnDefaultQueue";

  // Queue 0 exists on every ASIC. When defaultPortQueues has no entry for it
  // (the config command creates one), restore by deleting the entry instead
  // of writing the original weight back.
  auto config = getRunningConfig();
  const int queueId = 0;
  const auto* existingQueue = findQueueById(config, queueId);
  bool hadEntry = existingQueue != nullptr;
  int originalWeight = (hadEntry && existingQueue->count("weight"))
      ? (*existingQueue)["weight"].asInt()
      : 1;
  // Pick a new weight that differs from the original
  int newWeight = (originalWeight == 1) ? 2 : 1;

  XLOG(INFO) << fmt::format(
      "queue-id={} hadEntry={} originalWeight={} newWeight={}",
      queueId,
      hadEntry,
      originalWeight,
      newWeight);

  // Set the new weight
  auto result = runCli(
      {"config",
       "qos",
       "default-queue-config",
       std::to_string(queueId),
       "weight",
       std::to_string(newWeight)});
  XLOG(DBG1) << "stdout: " << result.stdout;
  if (!result.stderr.empty()) {
    XLOG(DBG1) << "stderr: " << result.stderr;
  }
  ASSERT_EQ(result.exitCode, 0) << "CLI failed: " << result.stderr;

  // Commit
  XLOG(INFO) << "Committing config...";
  commitConfig();
  waitForAgentReady();

  // Verify
  XLOG(INFO) << "Verifying running config...";
  auto newConfig = getRunningConfig();
  ASSERT_TRUE(newConfig.count("sw"));
  ASSERT_TRUE(newConfig["sw"].count("defaultPortQueues"));
  const auto& queues = newConfig["sw"]["defaultPortQueues"];
  ASSERT_TRUE(queues.isArray());

  bool found = false;
  for (const auto& q : queues) {
    if (q.count("id") && q["id"].asInt() == queueId) {
      found = true;
      ASSERT_TRUE(q.count("weight"))
          << "weight field missing after set for queue-id " << queueId;
      EXPECT_EQ(q["weight"].asInt(), newWeight)
          << "weight not updated for queue-id " << queueId;
      break;
    }
  }
  EXPECT_TRUE(found) << "queue-id " << queueId
                     << " not found in running config";
  XLOG(INFO) << "Weight verified.";

  // Restore: write the original weight back, or delete the entry this test
  // created when the queue had none.
  XLOG(INFO)
      << (hadEntry ? "Restoring original weight..."
                   : "Deleting created queue entry...");
  discardSession();
  auto restoreResult = hadEntry
      ? runCli(
            {"config",
             "qos",
             "default-queue-config",
             std::to_string(queueId),
             "weight",
             std::to_string(originalWeight)})
      : runCli(
            {"delete", "qos", "default-queue-config", std::to_string(queueId)});
  ASSERT_EQ(restoreResult.exitCode, 0)
      << "Restore CLI failed: " << restoreResult.stderr;
  commitConfig();
  waitForAgentReady();

  auto restoredConfig = getRunningConfig();
  const auto* restoredQueue = findQueueById(restoredConfig, queueId);
  if (hadEntry) {
    ASSERT_NE(restoredQueue, nullptr);
    EXPECT_EQ((*restoredQueue)["weight"].asInt(), originalWeight);
  } else {
    EXPECT_EQ(restoredQueue, nullptr)
        << "queue entry still present after restore delete";
  }

  XLOG(INFO) << "TEST PASSED";
}

// End-to-end for an enum-valued attribute (scheduling): thrift enums serialize
// differently from plain ints, so exercise the commit+verify+restore cycle for
// one. Runs whether or not queue 0 already exists: if it does, flip scheduling
// to a different value and restore the original; if not, create the entry and
// delete it. QueueScheduling enum ints: WRR=0, STRICT_PRIORITY=1, DRR=2.
TEST_F(ConfigQosDefaultQueueConfigTest, SetSchedulingOnDefaultQueue) {
  XLOG(INFO) << "ConfigQosDefaultQueueConfigTest::SetSchedulingOnDefaultQueue";

  auto schedName = [](int v) -> std::string {
    switch (v) {
      case 0:
        return "WEIGHTED_ROUND_ROBIN";
      case 1:
        return "STRICT_PRIORITY";
      case 2:
        return "DEFICIT_ROUND_ROBIN";
      default:
        return "";
    }
  };

  const int queueId = 0;
  auto config = getRunningConfig();
  const auto* existing = findQueueById(config, queueId);
  bool hadEntry = existing != nullptr;
  int originalSched = (hadEntry && existing->count("scheduling"))
      ? (*existing)["scheduling"].asInt()
      : 0;
  // If the pre-existing scheduling is not one we can name back (e.g. INTERNAL),
  // skip before mutating anything so the baseline is never left changed.
  if (hadEntry && schedName(originalSched).empty()) {
    GTEST_SKIP()
        << "queue 0 scheduling=" << originalSched
        << " has no restorable enum name; skipping to protect baseline";
  }
  // Pick a target that differs from the original and has a stable enum name.
  int newSched = (originalSched == 1) ? 0 : 1;

  XLOG(INFO) << fmt::format(
      "hadEntry={} originalSched={} newSched={}",
      hadEntry,
      originalSched,
      newSched);

  auto setResult = runCli(
      {"config",
       "qos",
       "default-queue-config",
       std::to_string(queueId),
       "scheduling",
       schedName(newSched)});
  ASSERT_EQ(setResult.exitCode, 0) << "CLI failed: " << setResult.stderr;

  XLOG(INFO) << "Committing scheduling change...";
  commitConfig();
  waitForAgentReady();

  // Hold the config in a named local: findQueueById returns a pointer into it,
  // so the dynamic must outlive the pointer.
  auto afterSet = getRunningConfig();
  const auto* q = findQueueById(afterSet, queueId);
  ASSERT_NE(q, nullptr) << "queue " << queueId << " missing after set";
  ASSERT_TRUE(q->count("scheduling"));
  EXPECT_EQ((*q)["scheduling"].asInt(), newSched)
      << "scheduling not updated in running config";
  XLOG(INFO) << "Scheduling verified.";

  // Restore: rewrite the original scheduling if the entry pre-existed, else
  // delete the entry this test created.
  discardSession();
  if (hadEntry) {
    XLOG(INFO) << "Restoring original scheduling...";
    auto restoreResult = runCli(
        {"config",
         "qos",
         "default-queue-config",
         std::to_string(queueId),
         "scheduling",
         schedName(originalSched)});
    ASSERT_EQ(restoreResult.exitCode, 0)
        << "restore failed: " << restoreResult.stderr;
  } else {
    XLOG(INFO) << "Deleting created entry...";
    auto delResult = runCli(
        {"delete", "qos", "default-queue-config", std::to_string(queueId)});
    ASSERT_EQ(delResult.exitCode, 0)
        << "restore delete failed: " << delResult.stderr;
  }
  commitConfig();
  waitForAgentReady();

  XLOG(INFO) << "TEST PASSED";
}

// Full create + delete cycle: add a new queue entry, commit, verify it is in
// the running config; delete it, commit, verify it is gone. The device ends
// at exactly its original config.
TEST_F(ConfigQosDefaultQueueConfigTest, CreateThenDeleteQueueEntry) {
  XLOG(INFO) << "ConfigQosDefaultQueueConfigTest::CreateThenDeleteQueueEntry";

  auto config = getRunningConfig();
  auto ids = defaultQueueIds(config);

  // Smallest id not already configured; works from an empty list too
  int candidateId = 0;
  while (ids.count(candidateId)) {
    candidateId++;
  }
  XLOG(INFO) << fmt::format("using candidate queue-id {}", candidateId);

  // Create a new entry
  auto setResult = runCli(
      {"config",
       "qos",
       "default-queue-config",
       std::to_string(candidateId),
       "weight",
       "2"});
  ASSERT_EQ(setResult.exitCode, 0) << "CLI failed: " << setResult.stderr;

  XLOG(INFO) << "Committing create...";
  commitConfig();
  waitForAgentReady();

  auto configAfterCreate = getRunningConfig();
  ASSERT_EQ(defaultQueueIds(configAfterCreate).count(candidateId), 1)
      << "created queue-id " << candidateId << " not in running config";
  XLOG(INFO) << "Create verified.";

  // Delete the entry again
  discardSession();
  auto delResult = runCli(
      {"delete", "qos", "default-queue-config", std::to_string(candidateId)});
  ASSERT_EQ(delResult.exitCode, 0) << "CLI failed: " << delResult.stderr;
  EXPECT_THAT(delResult.stdout, ::testing::HasSubstr("Successfully deleted"));

  XLOG(INFO) << "Committing delete...";
  commitConfig();
  waitForAgentReady();

  auto configAfterDelete = getRunningConfig();
  EXPECT_EQ(defaultQueueIds(configAfterDelete).count(candidateId), 0)
      << "deleted queue-id " << candidateId << " still in running config";
  EXPECT_EQ(defaultQueueIds(configAfterDelete), ids)
      << "defaultPortQueues ids differ from original after delete";

  XLOG(INFO) << "TEST PASSED";
}

// End-to-end AQM coexistence: set an ECN policy and an EARLY_DROP policy on the
// same queue, commit, and verify the running config carries BOTH aqms entries
// (the agent programs one WRED profile with both a drop ramp and an ECN-mark
// ramp). Runs on an unused queue-id and deletes it afterwards so the device
// ends at its original config. QueueCongestionBehavior ints: EARLY_DROP=0,
// ECN=1.
TEST_F(ConfigQosDefaultQueueConfigTest, AqmEcnAndEarlyDropCoexist) {
  XLOG(INFO) << "ConfigQosDefaultQueueConfigTest::AqmEcnAndEarlyDropCoexist";

  auto config = getRunningConfig();
  auto ids = defaultQueueIds(config);
||||||| d33cd384af
// Create a queue entry, commit, verify the agent's running config, then delete
// the entry and verify it is gone. Operating on an unused queue id keeps the
// test independent of how many queues the ASIC already has configured,
// including none at all.
TEST_F(ConfigQosDefaultQueueConfigTest, CreateThenDeleteQueueEntry) {
  auto config = getRunningConfig();
  auto ids = defaultQueueIds(config);
=======
// Bulk traffic queue: shares bandwidth with its peers via weighted round robin.
// `WRR` also exercises the short-name scheduling alias.
TEST_F(ConfigQosDefaultQueueConfigTest, BulkTrafficQueueUsesWrrWeight) {
  int queueId = pickUnusedQueueId();
  const auto* q = configureAndCommit(
      queueId, {"scheduling", "WRR", "weight", std::to_string(kWeight)});
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37

<<<<<<< HEAD
  int candidateId = 0;
  while (ids.count(candidateId)) {
    candidateId++;
  }
  XLOG(INFO) << fmt::format("using candidate queue-id {}", candidateId);

  // Stage an ECN policy, then an EARLY_DROP policy on the same queue. Two edits
  // in one session must produce two coexisting aqms entries.
  auto ecn = runCli(
      {"config",
       "qos",
       "default-queue-config",
       std::to_string(candidateId),
       "active-queue-management",
       "congestion-behavior",
       "ECN",
       "detection",
       "linear",
       "minimum-length",
       "40000",
       "maximum-length",
       "60000",
       "probability",
       "100"});
  ASSERT_EQ(ecn.exitCode, 0) << "ECN set failed: " << ecn.stderr;

  auto earlyDrop = runCli(
      {"config",
       "qos",
       "default-queue-config",
       std::to_string(candidateId),
       "active-queue-management",
       "congestion-behavior",
       "EARLY_DROP",
       "detection",
       "linear",
       "minimum-length",
       "30000",
       "maximum-length",
       "50000",
       "probability",
       "10"});
  ASSERT_EQ(earlyDrop.exitCode, 0)
      << "EARLY_DROP set failed: " << earlyDrop.stderr;

  XLOG(INFO) << "Committing AQM config...";
  commitConfig();
  waitForAgentReady();

  auto afterSet = getRunningConfig();
  const auto* q = findQueueById(afterSet, candidateId);
  ASSERT_NE(q, nullptr) << "queue " << candidateId << " missing after set";
  ASSERT_TRUE(q->count("aqms")) << "no aqms on queue after AQM config";
  const auto& aqms = (*q)["aqms"];
  ASSERT_TRUE(aqms.isArray());
  ASSERT_EQ(aqms.size(), 2)
      << "expected ECN and EARLY_DROP to coexist as two aqms entries";
||||||| d33cd384af
  int candidateId = 0;
  while (ids.count(candidateId)) {
    candidateId++;
  }
  XLOG(INFO) << "using candidate queue-id " << candidateId;

  ASSERT_EQ(
      runCli({"config",
              "qos",
              "default-queue-config",
              std::to_string(candidateId),
              "weight",
              "2"})
          .exitCode,
      0);

  XLOG(INFO) << "Committing create...";
  commitConfig();
  waitForAgentReady();

  auto afterCreate = getRunningConfig();
  const auto* q = findQueueById(afterCreate, candidateId);
  ASSERT_NE(q, nullptr) << "created queue-id " << candidateId
                        << " not in running config";
  ASSERT_TRUE(q->count("weight"));
  EXPECT_EQ((*q)["weight"].asInt(), 2);
  XLOG(INFO) << "Create verified.";
=======
  ASSERT_NE(q, nullptr) << "queue-id " << queueId << " not in running config";
  ASSERT_TRUE(q->count("scheduling"));
  EXPECT_EQ((*q)["scheduling"].asInt(), kSchedWrr);
  ASSERT_TRUE(q->count("weight"));
  EXPECT_EQ((*q)["weight"].asInt(), kWeight);

  deleteQueueAndCommit(queueId);
}

// Latency-sensitive traffic: drains ahead of every lower-priority queue. No
// weight -- thrift ignores it for STRICT_PRIORITY.
TEST_F(
    ConfigQosDefaultQueueConfigTest,
    PriorityTrafficQueueUsesStrictPriority) {
  int queueId = pickUnusedQueueId();
  const auto* q = configureAndCommit(queueId, {"scheduling", "SP"});

  ASSERT_NE(q, nullptr) << "queue-id " << queueId << " not in running config";
  ASSERT_TRUE(q->count("scheduling"));
  EXPECT_EQ((*q)["scheduling"].asInt(), kSchedSp);

  deleteQueueAndCommit(queueId);
}

// Loss-sensitive traffic: guaranteed buffer plus a dynamic shared threshold, so
// a burst is absorbed rather than tail-dropped.
TEST_F(ConfigQosDefaultQueueConfigTest, LossSensitiveQueueCarvesBuffer) {
  int queueId = pickUnusedQueueId();
  const auto* q = configureAndCommit(
      queueId,
      {"reserved-bytes",
       std::to_string(kReservedBytes),
       "scaling-factor",
       "TWO"});

  ASSERT_NE(q, nullptr) << "queue-id " << queueId << " not in running config";
  ASSERT_TRUE(q->count("reservedBytes"));
  EXPECT_EQ((*q)["reservedBytes"].asInt(), kReservedBytes);
  ASSERT_TRUE(q->count("scalingFactor"));
  EXPECT_EQ((*q)["scalingFactor"].asInt(), kScalingTwo);

  deleteQueueAndCommit(queueId);
}

// ECN-capable traffic: mark Congestion Experienced on the way up the ramp
// instead of dropping. active-queue-management must come last in the argv --
// it consumes all remaining arguments.
TEST_F(ConfigQosDefaultQueueConfigTest, CongestionSignallingQueueMarksEcn) {
  int queueId = pickUnusedQueueId();
  const auto* q = configureAndCommit(
      queueId,
      {"active-queue-management",
       "congestion-behavior",
       "ECN",
       "detection",
       "linear",
       "minimum-length",
       std::to_string(kAqmMinLength),
       "maximum-length",
       std::to_string(kAqmMaxLength),
       "probability",
       std::to_string(kAqmProbability)});

  ASSERT_NE(q, nullptr) << "queue-id " << queueId << " not in running config";
  ASSERT_TRUE(q->count("aqms"));
  const auto& aqms = (*q)["aqms"];
  ASSERT_TRUE(aqms.isArray());
  ASSERT_FALSE(aqms.empty());
  EXPECT_EQ(aqms[0]["behavior"].asInt(), kBehaviorEcn);
  const auto& linear = aqms[0]["detection"]["linear"];
  EXPECT_EQ(linear["minimumLength"].asInt(), kAqmMinLength);
  EXPECT_EQ(linear["maximumLength"].asInt(), kAqmMaxLength);
  EXPECT_EQ(linear["probability"].asInt(), kAqmProbability);

  deleteQueueAndCommit(queueId);
}

// Delete takes the entry back out and leaves defaultPortQueues exactly as it
// was found -- the one case that asserts on the post-delete state rather than
// just cleaning up after itself.
TEST_F(ConfigQosDefaultQueueConfigTest, DeleteRemovesQueueEntry) {
  int queueId = pickUnusedQueueId();
  ASSERT_NE(
      configureAndCommit(queueId, {"weight", std::to_string(kWeight)}), nullptr)
      << "queue-id " << queueId << " not in running config";
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37

  bool sawEcn = false, sawEarlyDrop = false;
  for (const auto& aqm : aqms) {
    ASSERT_TRUE(aqm.count("behavior"));
    int behavior = aqm["behavior"].asInt();
    if (behavior == 1) {
      sawEcn = true;
    } else if (behavior == 0) {
      sawEarlyDrop = true;
    }
    // Each entry keeps its own linear detection.
    ASSERT_TRUE(aqm.count("detection") && aqm["detection"].count("linear"))
        << "aqm entry (behavior=" << behavior << ") lost its linear detection";
  }
  EXPECT_TRUE(sawEcn) << "ECN aqms entry missing from running config";
  EXPECT_TRUE(sawEarlyDrop)
      << "EARLY_DROP aqms entry missing from running config";
  XLOG(INFO) << "AQM coexistence verified.";

  // Restore: delete the entry this test created.
  discardSession();
  auto del = runCli(
<<<<<<< HEAD
      {"delete", "qos", "default-queue-config", std::to_string(candidateId)});
  ASSERT_EQ(del.exitCode, 0) << "restore delete failed: " << del.stderr;
||||||| d33cd384af
      {"delete", "qos", "default-queue-config", std::to_string(candidateId)});
  ASSERT_EQ(del.exitCode, 0) << "CLI failed: " << del.stderr;
  EXPECT_THAT(del.stdout, ::testing::HasSubstr("Successfully deleted"));

  XLOG(INFO) << "Committing delete...";
=======
      {"delete",
       "qos",
       "queue-config",
       "default",
       "queue-id",
       std::to_string(queueId)});
  ASSERT_EQ(del.exitCode, 0) << "CLI failed: " << del.stderr;
  EXPECT_THAT(del.stdout, ::testing::HasSubstr("Successfully deleted"));
  createdQueueId_.reset();

  XLOG(INFO) << "Committing delete...";
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37
  commitConfig();
  waitForAgentReady();

<<<<<<< HEAD
  auto restored = getRunningConfig();
  EXPECT_EQ(defaultQueueIds(restored), ids)
      << "defaultPortQueues ids differ from original after restore";

  XLOG(INFO) << "TEST PASSED";
||||||| d33cd384af
  EXPECT_EQ(defaultQueueIds(getRunningConfig()), ids)
      << "defaultPortQueues ids differ from original after delete";
  XLOG(INFO) << "Delete verified.";
=======
  EXPECT_EQ(defaultQueueIds(getRunningConfig()), baselineIds_)
      << "defaultPortQueues ids differ from original after delete";
>>>>>>> a75ad2f54fd714ae4b006fc1f851e34f96df7b37
}
