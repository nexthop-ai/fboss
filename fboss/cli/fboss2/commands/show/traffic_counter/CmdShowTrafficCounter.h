// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <cstdint>
#include <iostream>
#include <map>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/show/traffic_counter/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"

namespace facebook::fboss {

// Optional positional: the names of the counters to show. Empty means every
// counter in the running config.
class TrafficCounterNameList : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */ TrafficCounterNameList() : BaseObjectArgType() {}
  /* implicit */ TrafficCounterNameList( // NOLINT(google-explicit-constructor)
      std::vector<std::string> v)
      : BaseObjectArgType(std::move(v)) {}
};

struct CmdShowTrafficCounterTraits : public ReadCommandTraits {
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    cmd.add_option(
        "counters",
        args,
        "Traffic counter name(s), as given to 'config traffic-counter'. "
        "Every configured counter when omitted.");
  }
  using ObjectArgType = TrafficCounterNameList;
  using RetType = cli::ShowTrafficCounterModel;
  static constexpr bool ALLOW_FILTERING = true;
  static constexpr bool ALLOW_AGGREGATION = true;

  // Human-authored guide prose for the CLI reference wiki. Superset of the
  // one-line help string registered in the command tree.
  static std::string_view description();
};

class CmdShowTrafficCounter
    : public CmdHandler<CmdShowTrafficCounter, CmdShowTrafficCounterTraits> {
 public:
  using ObjectArgType = CmdShowTrafficCounterTraits::ObjectArgType;
  using RetType = CmdShowTrafficCounterTraits::RetType;

  RetType queryClient(
      const HostInfo& hostInfo,
      const ObjectArgType& queriedCounters);
  void printOutput(const RetType& model, std::ostream& out = std::cout);

  // Canned, synthetic model (no real switch data) used to render a
  // deterministic example for the CLI reference wiki. No live switch.
  static RetType sampleModel();

  // The configured counters to report: all of them when `queried` is empty,
  // otherwise the queried ones, each once. Throws std::invalid_argument for a
  // queried name that is not configured.
  static std::vector<cfg::TrafficCounter> selectCounters(
      const std::vector<cfg::TrafficCounter>& configured,
      const std::vector<std::string>& queried);

  // The getRegexCounters pattern selecting exactly the fb303 stats these
  // counters' rows are built from.
  static std::string statRegex(
      const std::vector<cfg::TrafficCounter>& counters);

  // Whether the config spans more than one switch ASIC, in which case each
  // HwAgent exports its stats under a switch.<index>. prefix.
  static bool hasMultipleSwitches(const cfg::SwitchConfig& config);

  // One row per counter and type, counters sorted by name, from the fb303
  // stats keyed by name as the agent exports them. With multipleSwitches the
  // switch.<index>. prefixes are stripped and the copies summed.
  static RetType createModel(
      const std::vector<cfg::TrafficCounter>& counters,
      const std::map<std::string, int64_t>& stats,
      bool multipleSwitches);
};

} // namespace facebook::fboss
