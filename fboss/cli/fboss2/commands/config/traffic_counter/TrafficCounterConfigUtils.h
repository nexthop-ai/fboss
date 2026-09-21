/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#pragma once

#include <string>

#include "fboss/agent/gen-cpp2/switch_config_types.h"

namespace facebook::fboss::utils {

// Ensures that an action's traffic counter name is declared in the switch
// config. A newly declared counter keeps the Thrift default type (PACKETS).
void ensureTrafficCounterDeclared(
    cfg::SwitchConfig& switchConfig,
    const std::string& name);

} // namespace facebook::fboss::utils
