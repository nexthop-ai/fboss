// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "fboss/cli/fboss2/commands/show/traffic_counter/CmdShowTrafficCounter.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/String.h>
#include <re2/re2.h>
#include <thrift/lib/cpp/util/EnumUtils.h>
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include <algorithm>
#include <cstdint>
#include <map>
#include <optional>
#include <ostream>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrl.h"
#include "fboss/agent/if/gen-cpp2/FbossCtrlAsyncClient.h"
#include "fboss/cli/fboss2/commands/show/traffic_counter/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/utils/CmdClientUtilsCommon.h"
#include "fboss/cli/fboss2/utils/CmdUtils.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/cli/fboss2/utils/Table.h"

namespace facebook::fboss {

namespace {

constexpr std::string_view kAbsent = "--";

// The HwAgent exports one stat per counter and type, named
// <counter>.<packets|bytes> (SaiAclTableManager::addAclCounter). fb303
// derives the cumulative total and the per-second rate over each trailing
// window from it (ExportType SUM and RATE).
constexpr std::string_view kPacketsSuffix = "packets";
constexpr std::string_view kBytesSuffix = "bytes";
constexpr std::string_view kTotalSuffix = "sum";
constexpr std::string_view kRateSuffix = "rate";
constexpr int kOneMinute = 60;
constexpr int kTenMinutes = 600;
constexpr int kOneHour = 3600;

// On a platform with several switch ASICs each HwAgent prefixes its stats
// with switch.<index>. (Platform::getMultiSwitchStatsPrefix); on the others
// the stat is exported under its bare name.
constexpr std::string_view kSwitchPrefix = "switch.";

std::string statSuffix(cfg::CounterType type) {
  switch (type) {
    case cfg::CounterType::PACKETS:
      return std::string(kPacketsSuffix);
    case cfg::CounterType::BYTES:
      return std::string(kBytesSuffix);
  }
  // SaiAclTableManager::addAclCounter rejects any other type, so a running
  // agent cannot have one in its config.
  throw std::invalid_argument(
      fmt::format(
          "unsupported traffic counter type {}",
          apache::thrift::util::enumNameSafe(type)));
}

// The stat name without its leading switch.<index>. prefix. Only called on
// stats from a multi-ASIC platform, where every stat carries one, so a
// counter whose own name starts that way keeps its name.
std::string_view stripSwitchPrefix(std::string_view key) {
  if (!key.starts_with(kSwitchPrefix)) {
    return key;
  }
  auto rest = key.substr(kSwitchPrefix.size());
  auto digits = rest.find_first_not_of("0123456789");
  if (digits == 0 || digits == std::string_view::npos || rest[digits] != '.') {
    return key;
  }
  return rest.substr(digits + 1);
}

// The stats keyed by bare name, summed across switch indices: a counter is
// programmed on every ASIC it applies to, and each HwAgent exports its own
// copy.
std::map<std::string, int64_t> foldSwitchPrefixes(
    const std::map<std::string, int64_t>& stats) {
  std::map<std::string, int64_t> folded;
  for (const auto& [key, value] : stats) {
    folded[std::string(stripSwitchPrefix(key))] += value;
  }
  return folded;
}

std::optional<int64_t> statValue(
    const std::map<std::string, int64_t>& stats,
    const std::string& key) {
  auto it = stats.find(key);
  if (it == stats.end()) {
    return std::nullopt;
  }
  return it->second;
}

std::string rateKey(const std::string& statName, int window) {
  return fmt::format("{}.{}.{}", statName, kRateSuffix, window);
}

template <typename OptionalRef>
std::string cell(const OptionalRef& ref) {
  return ref.has_value() ? std::to_string(*ref) : std::string(kAbsent);
}

} // namespace

CmdShowTrafficCounter::RetType CmdShowTrafficCounter::queryClient(
    const HostInfo& hostInfo,
    const ObjectArgType& queriedCounters) {
  auto client =
      utils::createClient<apache::thrift::Client<FbossCtrl>>(hostInfo);

  // The counter names and types come from the running config: ctrl.thrift
  // has no call that lists traffic counters, and the agent's AclStats (the
  // cumulative values) reach SwAgent only through the HwSwitch stats sync
  // and are published to FSDB (AgentStats.aclStatsMap); no FbossCtrl method
  // returns them, and they carry no rates. The values come from the fb303
  // stats the agent exports for each counter instead.
  std::string configStr;
  client->sync_getRunningConfig(configStr);

  cfg::AgentConfig agentConfig;
  apache::thrift::SimpleJSONSerializer::deserialize<cfg::AgentConfig>(
      configStr, agentConfig);
  // Handle the legacy case where the agent returns a bare SwitchConfig.
  if (*agentConfig.sw() == cfg::SwitchConfig()) {
    apache::thrift::SimpleJSONSerializer::deserialize<cfg::SwitchConfig>(
        configStr, *agentConfig.sw());
  }

  auto counters = selectCounters(
      *agentConfig.sw()->trafficCounters(), queriedCounters.data());

  std::map<std::string, int64_t> stats;
  if (!counters.empty()) {
    // In multi-switch mode the ACL counters live in the HwAgent processes,
    // which this helper fans out to; in mono mode SwAgent serves them.
    stats = utils::getAgentFb303RegexCounters(hostInfo, statRegex(counters));
  }
  return createModel(counters, stats, hasMultipleSwitches(*agentConfig.sw()));
}

bool CmdShowTrafficCounter::hasMultipleSwitches(
    const cfg::SwitchConfig& config) {
  // The agent's own test (SwitchIdScopeResolver::hasMultipleSwitches).
  return config.switchSettings()->switchIdToSwitchInfo()->size() > 1;
}

std::vector<cfg::TrafficCounter> CmdShowTrafficCounter::selectCounters(
    const std::vector<cfg::TrafficCounter>& configured,
    const std::vector<std::string>& queried) {
  if (queried.empty()) {
    return configured;
  }
  std::vector<cfg::TrafficCounter> selected;
  for (const auto& name : queried) {
    auto it = std::find_if(
        configured.begin(), configured.end(), [&name](const auto& counter) {
          return *counter.name() == name;
        });
    if (it == configured.end()) {
      throw std::invalid_argument(
          fmt::format(
              "traffic counter '{}' is not configured; run without a name to list "
              "the configured counters",
              name));
    }
    auto already = std::any_of(
        selected.begin(), selected.end(), [&name](const auto& counter) {
          return *counter.name() == name;
        });
    if (!already) {
      selected.push_back(*it);
    }
  }
  return selected;
}

std::string CmdShowTrafficCounter::statRegex(
    const std::vector<cfg::TrafficCounter>& counters) {
  std::vector<std::string> names;
  names.reserve(counters.size());
  for (const auto& counter : counters) {
    names.push_back(re2::RE2::QuoteMeta(*counter.name()));
  }
  // Anchored, so it selects the same stats whether the service searches or
  // full-matches, and leaves out the .sum.<window> and all-time .rate series
  // the rows do not use.
  return fmt::format(
      R"(^({}[0-9]+\.)?({})\.({}|{})\.({}|{}\.({}|{}|{}))$)",
      re2::RE2::QuoteMeta(kSwitchPrefix),
      folly::join("|", names),
      kPacketsSuffix,
      kBytesSuffix,
      kTotalSuffix,
      kRateSuffix,
      kOneMinute,
      kTenMinutes,
      kOneHour);
}

CmdShowTrafficCounter::RetType CmdShowTrafficCounter::createModel(
    const std::vector<cfg::TrafficCounter>& counters,
    const std::map<std::string, int64_t>& stats,
    bool multipleSwitches) {
  RetType model;
  // On a single-ASIC platform the stats carry no prefix, and a name that
  // merely looks prefixed (a counter called switch.5.foo) must stay intact.
  const auto& byName = multipleSwitches ? foldSwitchPrefixes(stats) : stats;

  // Config order is the order counters were created in; report by name.
  auto sorted = counters;
  std::sort(sorted.begin(), sorted.end(), [](const auto& a, const auto& b) {
    return *a.name() < *b.name();
  });

  for (const auto& counter : sorted) {
    // Types are listed as typed; report them in enum order (PACKETS, BYTES),
    // each once.
    std::set<cfg::CounterType> types(
        counter.types()->begin(), counter.types()->end());
    if (types.empty()) {
      // The config CLI always sets a type and thrift defaults to PACKETS,
      // but a hand-edited config can list none. Keep the counter visible
      // rather than drop it from the listing.
      cli::TrafficCounterEntry entry;
      entry.name() = *counter.name();
      entry.type() = kAbsent;
      model.counters()->push_back(std::move(entry));
      continue;
    }
    for (const auto& type : types) {
      cli::TrafficCounterEntry entry;
      entry.name() = *counter.name();
      entry.type() = apache::thrift::util::enumNameSafe(type);

      auto statName = fmt::format("{}.{}", *counter.name(), statSuffix(type));
      entry.total().from_optional(
          statValue(byName, fmt::format("{}.{}", statName, kTotalSuffix)));
      entry.rateOneMinute().from_optional(
          statValue(byName, rateKey(statName, kOneMinute)));
      entry.rateTenMinutes().from_optional(
          statValue(byName, rateKey(statName, kTenMinutes)));
      entry.rateOneHour().from_optional(
          statValue(byName, rateKey(statName, kOneHour)));
      model.counters()->push_back(std::move(entry));
    }
  }
  return model;
}

void CmdShowTrafficCounter::printOutput(
    const RetType& model,
    std::ostream& out) {
  utils::Table table;
  table.setHeader(
      {"Counter",
       "Type",
       "Total",
       "Rate/s (1m)",
       "Rate/s (10m)",
       "Rate/s (1h)"});
  for (const auto& entry : *model.counters()) {
    table.addRow(
        {*entry.name(),
         *entry.type(),
         cell(entry.total()),
         cell(entry.rateOneMinute()),
         cell(entry.rateTenMinutes()),
         cell(entry.rateOneHour())});
  }
  out << table << std::endl;
}

std::string_view CmdShowTrafficCounterTraits::description() {
  return "Shows the packet and byte totals and rates of named traffic counters, which 'config traffic-counter' creates and the ACL rules whose data-plane traffic-policy action names them increment. One row per counter and counter type; a counter that several rules name is one ASIC counter, so its row is their combined count. Total is cumulative since the agent created the counter; each rate is the per-second average over the trailing minute, ten minutes and hour. The names and types come from the agent's running config and the values from the stats the agent exports for each counter (the <counter>.packets and <counter>.bytes series that `show fb303-counters` dumps raw), so no knowledge of that naming is needed. On a platform with several switch ASICs the counter exists on each and the rows sum across them. A '--' means the agent exports no stat for that counter and type: nothing references the counter yet, so no ASIC counter exists for it. With no argument every configured counter is shown; naming a counter that is not configured is an error.";
}

CmdShowTrafficCounter::RetType CmdShowTrafficCounter::sampleModel() {
  RetType model;

  cli::TrafficCounterEntry packets;
  packets.name() = "demo_counter";
  packets.type() = "PACKETS";
  packets.total() = 76850722;
  packets.rateOneMinute() = 8066;
  packets.rateTenMinutes() = 7999;
  packets.rateOneHour() = 7848;
  model.counters()->push_back(packets);

  cli::TrafficCounterEntry bytes;
  bytes.name() = "demo_counter";
  bytes.type() = "BYTES";
  bytes.total() = 19673785088;
  bytes.rateOneMinute() = 2064952;
  bytes.rateTenMinutes() = 2047873;
  bytes.rateOneHour() = 2009180;
  model.counters()->push_back(bytes);

  // Configured but not yet named by any traffic-policy action.
  cli::TrafficCounterEntry unreferenced;
  unreferenced.name() = "spare_counter";
  unreferenced.type() = "PACKETS";
  model.counters()->push_back(unreferenced);

  return model;
}

// Explicit template instantiation
template void
CmdHandler<CmdShowTrafficCounter, CmdShowTrafficCounterTraits>::run();
template const ValidFilterMapType CmdHandler<
    CmdShowTrafficCounter,
    CmdShowTrafficCounterTraits>::getValidFilters();

} // namespace facebook::fboss
