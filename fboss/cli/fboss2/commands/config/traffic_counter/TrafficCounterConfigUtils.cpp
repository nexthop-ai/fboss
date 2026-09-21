/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/traffic_counter/TrafficCounterConfigUtils.h"

#include <algorithm>
#include <utility>

namespace facebook::fboss::utils {

void ensureTrafficCounterDeclared(
    cfg::SwitchConfig& switchConfig,
    const std::string& name) {
  auto& counters = *switchConfig.trafficCounters();
  if (std::none_of(counters.begin(), counters.end(), [&](const auto& counter) {
        return *counter.name() == name;
      })) {
    cfg::TrafficCounter counter;
    counter.name() = name;
    counters.push_back(std::move(counter));
  }
}

} // namespace facebook::fboss::utils
