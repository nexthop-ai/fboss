// Copyright (c) Meta Platforms, Inc. and affiliates.

/**
 * End-to-end tests for 'fboss2 show traffic-counter'.
 *
 * The command has no thrift API behind it: it reads the counter names and
 * types from the agent's running config and the values from the fb303 stats
 * the agent exports for each counter (<counter>.packets / <counter>.bytes,
 * .sum and .rate.<window>). The unit test (CmdShowTrafficCounterTest) covers
 * the row building against synthetic stats, so what is left to test here is
 * what only a live agent can show: that a configured counter is listed, that
 * a counter an ACL rule's traffic-policy action names gets its values from
 * the stats the agent really exports, and that naming an unknown counter is
 * an error.
 *
 * Tests:
 *
 * 1. ConfiguredCounterListedWithoutStats
 *    A counter nothing references yet is listed with both its types and no
 *    values, both in the full listing and when named, and --filter narrows
 *    the rows.
 *
 * 2. ReferencedCounterReportsStats
 *    Once a rule's traffic-policy action names the counter, the agent
 *    programs the ASIC counter and exports its stats; the rows then carry a
 *    total and rates, and the total agrees with the raw fb303 stat read
 *    around the command. Needs an ACL table in the DUT config to attach the
 *    rule to; skipped otherwise.
 *
 * 3. UnknownCounterIsAnError
 *
 * Requirements:
 * - FBOSS agent must be running with a valid configuration.
 */

#include <fmt/format.h>
#include <folly/json/dynamic.h>
#include <folly/logging/xlog.h>
#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <chrono>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "fboss/cli/fboss2/test/integration_test/Fboss2IntegrationTest.h"

using namespace facebook::fboss;
using ::testing::HasSubstr;

namespace {
// Names unlikely to collide with anything in a production config. The SAI
// counter label allows at most 31 characters.
const std::string kTestCounter = "fboss2-it-show-ctr";
const std::string kTestRule = "fboss2-it-show-ctr-rule";
constexpr auto kPackets = "PACKETS";
constexpr auto kBytes = "BYTES";
// How long to wait for the agent to export the stats of a newly programmed
// counter: they appear with its next stats collection after the commit.
constexpr auto kStatsTimeout = std::chrono::seconds(60);
constexpr auto kStatsInterval = std::chrono::seconds(2);
} // namespace

class ShowTrafficCounterTest : public Fboss2IntegrationTest {
 protected:
  // (counter name, type) -> row
  using RowKey = std::pair<std::string, std::string>;

  // An earlier run that died mid-way would leave the test objects behind.
  // Remove them so each run exercises the create path.
  void SetUp() override {
    Fboss2IntegrationTest::SetUp();
    removeTestObjects();
  }

  void TearDown() override {
    removeTestObjects();
    Fboss2IntegrationTest::TearDown();
  }

  std::map<RowKey, folly::dynamic> showCounters(
      const std::vector<std::string>& args) const {
    auto json = runCliJson(args);
    std::map<RowKey, folly::dynamic> rows;
    // The JSON output of a show command is keyed by host; these tests run
    // against localhost only.
    for (const auto& [host, hostData] : json.items()) {
      if (!hostData.isObject() || !hostData.count("counters")) {
        continue;
      }
      for (const auto& row : hostData["counters"]) {
        RowKey key{row["name"].asString(), row["type"].asString()};
        EXPECT_TRUE(rows.emplace(key, row).second)
            << "duplicate row for " << key.first << " " << key.second;
      }
    }
    return rows;
  }

  // The raw stat behind a row's total, read the way the ticket's workaround
  // did: the fb303 dump filtered by name. On a platform with several switch
  // ASICs each HwAgent exports its own switch.<index>.-prefixed copy, which
  // the command sums, so sum here too. nullopt if the agent does not export
  // it.
  std::optional<int64_t> rawTotal(const std::string& suffix) const {
    auto statName = fmt::format("{}.{}.sum", kTestCounter, suffix);
    auto json = runCliJson(
        {"show",
         "fb303-counters",
         "--regex",
         fmt::format(R"(^(switch\.[0-9]+\.)?{}$)", statName)});
    std::optional<int64_t> total;
    for (const auto& [host, hostData] : json.items()) {
      if (!hostData.isObject() || !hostData.count("counters")) {
        continue;
      }
      for (const auto& counter : hostData["counters"]) {
        total = total.value_or(0) + counter["value"].asInt();
      }
    }
    return total;
  }

  // The first AclTable of the first AclTableGroup, the table the acl rule CLI
  // targets, or nullopt when the DUT config has none.
  std::optional<std::string> targetTable() const {
    auto config = getRunningConfig();
    const auto* sw = config.get_ptr("sw");
    const auto* groups = sw ? sw->get_ptr("aclTableGroups") : nullptr;
    if (!groups || !groups->isArray() || groups->empty()) {
      return std::nullopt;
    }
    const auto* tables = (*groups)[0].get_ptr("aclTables");
    if (!tables || !tables->isArray() || tables->empty()) {
      return std::nullopt;
    }
    return (*tables)[0]["name"].asString();
  }

  bool counterConfigured(const folly::dynamic& config) const {
    const auto* sw = config.get_ptr("sw");
    const auto* counters = sw ? sw->get_ptr("trafficCounters") : nullptr;
    if (!counters) {
      return false;
    }
    for (const auto& counter : *counters) {
      if (counter["name"].asString() == kTestCounter) {
        return true;
      }
    }
    return false;
  }

  bool ruleActionConfigured(const folly::dynamic& config) const {
    const auto* sw = config.get_ptr("sw");
    const auto* policy = sw ? sw->get_ptr("dataPlaneTrafficPolicy") : nullptr;
    const auto* actions = policy ? policy->get_ptr("matchToAction") : nullptr;
    if (!actions) {
      return false;
    }
    for (const auto& mta : *actions) {
      if (mta["matcher"].asString() == kTestRule) {
        return true;
      }
    }
    return false;
  }

  bool ruleConfigured(const folly::dynamic& config) const {
    const auto* sw = config.get_ptr("sw");
    const auto* groups = sw ? sw->get_ptr("aclTableGroups") : nullptr;
    if (!groups) {
      return false;
    }
    for (const auto& group : *groups) {
      const auto* tables = group.get_ptr("aclTables");
      if (!tables) {
        continue;
      }
      for (const auto& table : *tables) {
        const auto* entries = table.get_ptr("aclEntries");
        if (!entries) {
          continue;
        }
        for (const auto& entry : *entries) {
          if (entry["name"].asString() == kTestRule) {
            return true;
          }
        }
      }
    }
    return false;
  }

  void runOk(const std::vector<std::string>& args) const {
    auto result = runCli(args);
    ASSERT_EQ(result.exitCode, 0)
        << "stdout=" << result.stdout << " stderr=" << result.stderr;
  }

  // Deletes whichever of the test objects the running config holds, in
  // dependency order (the counter cannot go while an action names it), and
  // commits if anything was deleted. Both the rule and the counter are
  // hitless to remove.
  void removeTestObjects() {
    auto config = getRunningConfig();
    bool deleted = false;
    if (ruleActionConfigured(config)) {
      XLOG(INFO) << "Removing leftover traffic-policy action of " << kTestRule;
      runOk(
          {"delete",
           "data-plane",
           "traffic-policy",
           "match",
           kTestRule,
           "action",
           "counter"});
      deleted = true;
    }
    if (ruleConfigured(config)) {
      auto table = targetTable();
      ASSERT_TRUE(table.has_value()) << "rule present but no ACL table";
      XLOG(INFO) << "Removing leftover rule " << kTestRule;
      runOk({"delete", "acl", "rule", *table, kTestRule});
      deleted = true;
    }
    if (counterConfigured(config)) {
      XLOG(INFO) << "Removing leftover counter " << kTestCounter;
      runOk({"delete", "traffic-counter", kTestCounter});
      deleted = true;
    }
    if (deleted) {
      commitConfig();
    }
  }
};

TEST_F(ShowTrafficCounterTest, ConfiguredCounterListedWithoutStats) {
  runOk({"config", "traffic-counter", kTestCounter, "PACKETS,BYTES"});
  commitConfig();

  auto all = showCounters({"show", "traffic-counter"});
  ASSERT_TRUE(all.count({kTestCounter, kPackets}))
      << "no PACKETS row for " << kTestCounter << " in the full listing";
  ASSERT_TRUE(all.count({kTestCounter, kBytes}))
      << "no BYTES row for " << kTestCounter << " in the full listing";

  auto named = showCounters({"show", "traffic-counter", kTestCounter});
  EXPECT_EQ(named.size(), 2u) << "naming the counter must list only its rows";
  for (const auto& [key, row] : named) {
    EXPECT_EQ(key.first, kTestCounter);
    // Nothing references the counter, so the agent exports no stat for it:
    // the values are absent rather than zero.
    EXPECT_FALSE(row.count("total")) << key.second << " has a total";
    EXPECT_FALSE(row.count("rateOneMinute")) << key.second << " has a rate";
  }

  // --filter is a global option and must precede the subcommand.
  auto filtered = showCounters(
      {"--filter",
       fmt::format("type == {}", kBytes),
       "show",
       "traffic-counter",
       kTestCounter});
  EXPECT_EQ(filtered.size(), 1u);
  EXPECT_EQ(filtered.count({kTestCounter, kBytes}), 1u);
}

TEST_F(ShowTrafficCounterTest, ReferencedCounterReportsStats) {
  auto table = targetTable();
  if (!table) {
    GTEST_SKIP() << "DUT config has no aclTableGroups AclTable to attach a "
                    "rule to";
  }

  runOk({"config", "traffic-counter", kTestCounter, "PACKETS,BYTES"});
  runOk({"config", "acl", "rule", *table, kTestRule, "dscp", "10"});
  runOk({"config", "acl", "rule", *table, kTestRule, "action", "permit"});
  runOk(
      {"config",
       "data-plane",
       "traffic-policy",
       "match",
       kTestRule,
       "action",
       "counter",
       kTestCounter});
  commitConfig();

  // The HwAgent creates the ASIC counter and its stats when it programs the
  // rule; they are exported from the next stats collection on.
  std::map<RowKey, folly::dynamic> rows;
  auto deadline = std::chrono::steady_clock::now() + kStatsTimeout;
  while (true) {
    rows = showCounters({"show", "traffic-counter", kTestCounter});
    auto packets = rows.find({kTestCounter, kPackets});
    auto bytes = rows.find({kTestCounter, kBytes});
    if (packets != rows.end() && bytes != rows.end() &&
        packets->second.count("total") && bytes->second.count("total")) {
      break;
    }
    if (std::chrono::steady_clock::now() >= deadline) {
      break;
    }
    std::this_thread::sleep_for(kStatsInterval);
  }
  ASSERT_EQ(rows.size(), 2u);
  for (const auto& type : {kPackets, kBytes}) {
    const auto& row = rows.at({kTestCounter, type});
    ASSERT_TRUE(row.count("total"))
        << type << " total still absent after " << kStatsTimeout.count() << "s";
    EXPECT_GE(row["total"].asInt(), 0);
    for (const auto* rate :
         {"rateOneMinute", "rateTenMinutes", "rateOneHour"}) {
      ASSERT_TRUE(row.count(rate)) << type << " has no " << rate;
      EXPECT_GE(row[rate].asInt(), 0);
    }
  }

  // The total is the raw stat the ticket's workaround reads. Counters only
  // grow, so the command's value must lie between two reads around it.
  auto before = rawTotal("packets");
  ASSERT_TRUE(before.has_value()) << "agent exports no packets.sum stat";
  auto shown = showCounters({"show", "traffic-counter", kTestCounter})
                   .at({kTestCounter, kPackets})["total"]
                   .asInt();
  auto after = rawTotal("packets");
  ASSERT_TRUE(after.has_value());
  EXPECT_GE(shown, *before);
  EXPECT_LE(shown, *after);
}

TEST_F(ShowTrafficCounterTest, UnknownCounterIsAnError) {
  auto result = runCli({"show", "traffic-counter", "fboss2-it-no-such-ctr"});
  EXPECT_NE(result.exitCode, 0);
  EXPECT_THAT(result.stderr, HasSubstr("not configured"));
}
