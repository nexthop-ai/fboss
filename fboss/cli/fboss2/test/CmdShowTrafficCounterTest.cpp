// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <re2/re2.h>
#include <cstdint>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/show/traffic_counter/CmdShowTrafficCounter.h"
#include "fboss/cli/fboss2/commands/show/traffic_counter/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/test/CmdHandlerTestBase.h"

using namespace ::testing;

namespace facebook::fboss {

namespace {

cfg::TrafficCounter makeCounter(
    const std::string& name,
    std::vector<cfg::CounterType> types) {
  cfg::TrafficCounter counter;
  counter.name() = name;
  counter.types() = std::move(types);
  return counter;
}

// Shaped like a deployed switch: a counter a traffic-policy action names
// (both types exported), one declared BYTES before PACKETS whose byte stat
// is not exported, and one nothing references yet, so the agent exports no
// stat for it. Deliberately not in name order.
std::vector<cfg::TrafficCounter> createTestConfig() {
  return {
      makeCounter(
          "demo_counter", {cfg::CounterType::PACKETS, cfg::CounterType::BYTES}),
      makeCounter(
          "cpu_q3", {cfg::CounterType::BYTES, cfg::CounterType::PACKETS}),
      makeCounter("acl-unused", {cfg::CounterType::PACKETS}),
  };
}

// demo_counter's values are from a lab switch's
// `show fb303-counters --regex demo_counter`. The .sum.<window> and all-time
// .rate series it also exports, and the stat of a counter whose name merely
// starts with a configured one, must not reach the rows.
std::map<std::string, int64_t> createTestStats() {
  return {
      {"demo_counter.bytes.rate", 2033676},
      {"demo_counter.bytes.rate.3600", 2009180},
      {"demo_counter.bytes.rate.60", 2064952},
      {"demo_counter.bytes.rate.600", 2047873},
      {"demo_counter.bytes.sum", 19673785088},
      {"demo_counter.bytes.sum.3600", 7130583552},
      {"demo_counter.bytes.sum.60", 121834240},
      {"demo_counter.bytes.sum.600", 1226678528},
      {"demo_counter.packets.rate", 7944},
      {"demo_counter.packets.rate.3600", 7848},
      {"demo_counter.packets.rate.60", 8066},
      {"demo_counter.packets.rate.600", 7999},
      {"demo_counter.packets.sum", 76850722},
      {"demo_counter.packets.sum.3600", 27853842},
      {"demo_counter.packets.sum.60", 475914},
      {"demo_counter.packets.sum.600", 4791712},
      {"demo_counter_old.packets.sum", 999},
      {"cpu_q3.packets.rate.3600", 0},
      {"cpu_q3.packets.rate.60", 0},
      {"cpu_q3.packets.rate.600", 0},
      {"cpu_q3.packets.sum", 12},
  };
}

std::vector<std::pair<std::string, std::string>> rowKeys(
    const cli::ShowTrafficCounterModel& model) {
  std::vector<std::pair<std::string, std::string>> keys;
  for (const auto& entry : *model.counters()) {
    keys.emplace_back(*entry.name(), *entry.type());
  }
  return keys;
}

} // namespace

class CmdShowTrafficCounterTestFixture : public CmdHandlerTestBase {};

TEST_F(CmdShowTrafficCounterTestFixture, oneRowPerCounterAndType) {
  auto model = CmdShowTrafficCounter::createModel(
      createTestConfig(), createTestStats(), /*multipleSwitches=*/false);
  // Counters by name; types in enum order regardless of how they were typed.
  EXPECT_THAT(
      rowKeys(model),
      ElementsAre(
          Pair("acl-unused", "PACKETS"),
          Pair("cpu_q3", "PACKETS"),
          Pair("cpu_q3", "BYTES"),
          Pair("demo_counter", "PACKETS"),
          Pair("demo_counter", "BYTES")));
}

TEST_F(CmdShowTrafficCounterTestFixture, valuesComeFromTotalAndWindowRates) {
  auto model = CmdShowTrafficCounter::createModel(
      createTestConfig(), createTestStats(), /*multipleSwitches=*/false);
  const auto& packets = model.counters()[3];
  EXPECT_EQ(packets.total(), 76850722);
  EXPECT_EQ(packets.rateOneMinute(), 8066);
  EXPECT_EQ(packets.rateTenMinutes(), 7999);
  EXPECT_EQ(packets.rateOneHour(), 7848);

  const auto& bytes = model.counters()[4];
  EXPECT_EQ(bytes.total(), 19673785088);
  EXPECT_EQ(bytes.rateOneMinute(), 2064952);
  EXPECT_EQ(bytes.rateTenMinutes(), 2047873);
  EXPECT_EQ(bytes.rateOneHour(), 2009180);
}

TEST_F(CmdShowTrafficCounterTestFixture, unexportedStatLeavesValuesAbsent) {
  auto model = CmdShowTrafficCounter::createModel(
      createTestConfig(), createTestStats(), /*multipleSwitches=*/false);
  const auto& unreferenced = model.counters()[0];
  EXPECT_FALSE(unreferenced.total().has_value());
  EXPECT_FALSE(unreferenced.rateOneMinute().has_value());
  EXPECT_FALSE(unreferenced.rateTenMinutes().has_value());
  EXPECT_FALSE(unreferenced.rateOneHour().has_value());

  // Only the packet stat is exported for cpu_q3.
  EXPECT_EQ(model.counters()[1].total(), 12);
  EXPECT_EQ(model.counters()[1].rateOneMinute(), 0);
  EXPECT_FALSE(model.counters()[2].total().has_value());
}

TEST_F(CmdShowTrafficCounterTestFixture, duplicateTypeReportedOnce) {
  auto model = CmdShowTrafficCounter::createModel(
      {makeCounter(
          "demo_counter",
          {cfg::CounterType::PACKETS, cfg::CounterType::PACKETS})},
      createTestStats(),
      false);
  EXPECT_THAT(rowKeys(model), ElementsAre(Pair("demo_counter", "PACKETS")));
}

TEST_F(CmdShowTrafficCounterTestFixture, counterWithNoTypesStillListed) {
  auto model = CmdShowTrafficCounter::createModel(
      {makeCounter("legacy_ctr", {})}, createTestStats(), false);
  EXPECT_THAT(rowKeys(model), ElementsAre(Pair("legacy_ctr", "--")));
  EXPECT_FALSE(model.counters()[0].total().has_value());
}

TEST_F(CmdShowTrafficCounterTestFixture, emptyConfig) {
  EXPECT_TRUE(
      CmdShowTrafficCounter::createModel({}, {}, false).counters()->empty());
  EXPECT_TRUE(
      CmdShowTrafficCounter::createModel({}, createTestStats(), false)
          .counters()
          ->empty());
}

TEST_F(CmdShowTrafficCounterTestFixture, selectCountersAllWhenNoneQueried) {
  auto selected = CmdShowTrafficCounter::selectCounters(createTestConfig(), {});
  ASSERT_EQ(selected.size(), 3);
}

TEST_F(CmdShowTrafficCounterTestFixture, selectCountersByName) {
  auto selected = CmdShowTrafficCounter::selectCounters(
      createTestConfig(), {"acl-unused", "demo_counter", "acl-unused"});
  ASSERT_EQ(selected.size(), 2);
  EXPECT_EQ(*selected[0].name(), "acl-unused");
  EXPECT_EQ(*selected[1].name(), "demo_counter");
  EXPECT_THAT(
      *selected[1].types(),
      ElementsAre(cfg::CounterType::PACKETS, cfg::CounterType::BYTES));
}

TEST_F(CmdShowTrafficCounterTestFixture, selectCountersRejectsUnknownName) {
  EXPECT_THROW(
      CmdShowTrafficCounter::selectCounters(
          createTestConfig(), {"demo_counter", "no_such_counter"}),
      std::invalid_argument);
}

TEST_F(CmdShowTrafficCounterTestFixture, statRegexSelectsRowStatsOnly) {
  re2::RE2 regex(CmdShowTrafficCounter::statRegex(createTestConfig()));
  ASSERT_TRUE(regex.ok()) << regex.error();

  EXPECT_TRUE(re2::RE2::FullMatch("demo_counter.packets.sum", regex));
  EXPECT_TRUE(re2::RE2::FullMatch("demo_counter.bytes.rate.60", regex));
  EXPECT_TRUE(re2::RE2::FullMatch("cpu_q3.packets.rate.600", regex));
  EXPECT_TRUE(re2::RE2::FullMatch("acl-unused.packets.rate.3600", regex));

  // Series the rows do not use.
  EXPECT_FALSE(re2::RE2::PartialMatch("demo_counter.packets.sum.60", regex));
  EXPECT_FALSE(re2::RE2::PartialMatch("demo_counter.packets.rate", regex));
  // Other counters, including one whose name extends a configured one.
  EXPECT_FALSE(re2::RE2::PartialMatch("demo_counter_old.packets.sum", regex));
  EXPECT_FALSE(re2::RE2::PartialMatch("xdemo_counter.packets.sum", regex));
  EXPECT_FALSE(re2::RE2::PartialMatch("demo_counter.packets.rate.6", regex));
}

TEST_F(CmdShowTrafficCounterTestFixture, statRegexQuotesCounterName) {
  // A '.' in a name must match itself, not any character.
  re2::RE2 regex(
      CmdShowTrafficCounter::statRegex(
          {makeCounter("v6.in", {cfg::CounterType::PACKETS})}));
  ASSERT_TRUE(regex.ok()) << regex.error();
  EXPECT_TRUE(re2::RE2::FullMatch("v6.in.packets.sum", regex));
  EXPECT_FALSE(re2::RE2::PartialMatch("v6xin.packets.sum", regex));
}

// On a platform with several switch ASICs every HwAgent exports its own
// switch.<index>.-prefixed copy of the stat; the rows sum across them. A
// counter whose own name starts with switch.<n>. still gets exactly its own
// copies, which carry the real prefix on top.
TEST_F(CmdShowTrafficCounterTestFixture, multipleSwitchesSumPrefixedStats) {
  std::map<std::string, int64_t> stats = {
      {"switch.0.demo_counter.packets.sum", 100},
      {"switch.0.demo_counter.packets.rate.60", 3},
      {"switch.0.demo_counter.packets.rate.600", 2},
      {"switch.0.demo_counter.packets.rate.3600", 1},
      {"switch.1.demo_counter.packets.sum", 50},
      {"switch.1.demo_counter.packets.rate.60", 1},
      {"switch.1.demo_counter.packets.rate.600", 1},
      {"switch.1.demo_counter.packets.rate.3600", 0},
      {"switch.0.switch.5.foo.packets.sum", 7},
      {"switch.1.switch.5.foo.packets.sum", 8},
  };
  auto model = CmdShowTrafficCounter::createModel(
      {makeCounter("demo_counter", {cfg::CounterType::PACKETS}),
       makeCounter("switch.5.foo", {cfg::CounterType::PACKETS})},
      stats,
      /*multipleSwitches=*/true);
  ASSERT_EQ(model.counters()->size(), 2);
  const auto& demo = model.counters()[0];
  EXPECT_EQ(*demo.name(), "demo_counter");
  EXPECT_EQ(demo.total(), 150);
  EXPECT_EQ(demo.rateOneMinute(), 4);
  EXPECT_EQ(demo.rateTenMinutes(), 3);
  EXPECT_EQ(demo.rateOneHour(), 1);
  EXPECT_EQ(*model.counters()[1].name(), "switch.5.foo");
  EXPECT_EQ(model.counters()[1].total(), 15);
}

// On a single-ASIC platform nothing is prefixed, so a counter named like a
// prefixed stat must be looked up as is rather than folded away.
TEST_F(CmdShowTrafficCounterTestFixture, singleSwitchKeepsPrefixLikeNames) {
  std::map<std::string, int64_t> stats = {
      {"switch.5.foo.packets.sum", 7},
      {"switch.5.foo.packets.rate.60", 1},
      {"switch.x.packets.sum", 9},
  };
  auto model = CmdShowTrafficCounter::createModel(
      {makeCounter("switch.5.foo", {cfg::CounterType::PACKETS}),
       makeCounter("switch.x", {cfg::CounterType::PACKETS}),
       makeCounter("foo", {cfg::CounterType::PACKETS})},
      stats,
      /*multipleSwitches=*/false);
  ASSERT_EQ(model.counters()->size(), 3);
  EXPECT_EQ(*model.counters()[0].name(), "foo");
  EXPECT_FALSE(model.counters()[0].total().has_value());
  EXPECT_EQ(*model.counters()[1].name(), "switch.5.foo");
  EXPECT_EQ(model.counters()[1].total(), 7);
  EXPECT_EQ(model.counters()[1].rateOneMinute(), 1);
  EXPECT_EQ(model.counters()[2].total(), 9);
}

TEST_F(CmdShowTrafficCounterTestFixture, hasMultipleSwitches) {
  cfg::SwitchConfig config;
  EXPECT_FALSE(CmdShowTrafficCounter::hasMultipleSwitches(config));
  config.switchSettings()->switchIdToSwitchInfo()->emplace(
      0, cfg::SwitchInfo());
  EXPECT_FALSE(CmdShowTrafficCounter::hasMultipleSwitches(config));
  config.switchSettings()->switchIdToSwitchInfo()->emplace(
      1, cfg::SwitchInfo());
  EXPECT_TRUE(CmdShowTrafficCounter::hasMultipleSwitches(config));
}

TEST_F(CmdShowTrafficCounterTestFixture, statRegexAcceptsSwitchPrefix) {
  re2::RE2 regex(CmdShowTrafficCounter::statRegex(createTestConfig()));
  ASSERT_TRUE(regex.ok()) << regex.error();
  EXPECT_TRUE(re2::RE2::FullMatch("switch.0.demo_counter.packets.sum", regex));
  EXPECT_TRUE(
      re2::RE2::FullMatch("switch.12.demo_counter.bytes.rate.600", regex));
  // Only the agent's exact prefix form, nothing else in front of the name.
  EXPECT_FALSE(
      re2::RE2::PartialMatch("switch.demo_counter.packets.sum", regex));
  EXPECT_FALSE(
      re2::RE2::PartialMatch("switch.a.demo_counter.packets.sum", regex));
  EXPECT_FALSE(
      re2::RE2::PartialMatch("hw.switch.0.demo_counter.packets.sum", regex));
}

TEST_F(CmdShowTrafficCounterTestFixture, unsupportedCounterTypeThrows) {
  // The agent rejects any type but PACKETS and BYTES, so this cannot come
  // from a running config; it must fail loudly rather than invent a stat.
  EXPECT_THROW(
      CmdShowTrafficCounter::createModel(
          {makeCounter("demo_counter", {static_cast<cfg::CounterType>(99)})},
          {},
          false),
      std::invalid_argument);
}

TEST_F(CmdShowTrafficCounterTestFixture, printOutput) {
  auto model = CmdShowTrafficCounter::createModel(
      createTestConfig(), createTestStats(), /*multipleSwitches=*/false);
  std::stringstream ss;
  CmdShowTrafficCounter().printOutput(model, ss);
  auto output = ss.str();

  EXPECT_THAT(output, HasSubstr("Counter"));
  EXPECT_THAT(output, HasSubstr("Rate/s (1m)"));
  EXPECT_THAT(output, HasSubstr("Rate/s (10m)"));
  EXPECT_THAT(output, HasSubstr("Rate/s (1h)"));
  EXPECT_THAT(output, HasSubstr("demo_counter"));
  EXPECT_THAT(output, HasSubstr("PACKETS"));
  EXPECT_THAT(output, HasSubstr("BYTES"));
  EXPECT_THAT(output, HasSubstr("76850722"));
  EXPECT_THAT(output, HasSubstr("19673785088"));
  EXPECT_THAT(output, HasSubstr("8066"));
  // The unreferenced counter is listed with placeholders, not dropped.
  EXPECT_THAT(output, HasSubstr("acl-unused"));
  EXPECT_THAT(output, HasSubstr("--"));
}

// CLI reference wiki hooks: a human description and a non-empty sample model.
// Property checks only (no golden text).
TEST_F(CmdShowTrafficCounterTestFixture, wikiDocHooks) {
  EXPECT_FALSE(CmdShowTrafficCounterTraits::description().empty());
  EXPECT_FALSE(CmdShowTrafficCounter::sampleModel().counters()->empty());
}

} // namespace facebook::fboss
