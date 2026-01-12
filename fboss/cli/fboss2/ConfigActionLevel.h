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

namespace facebook::fboss {

// Action level required for config changes to take effect.
// Used to track the highest impact action needed when committing config
// changes.
enum class ConfigActionLevel {
  HITLESS = 0, // Can be applied with reloadConfig() - default
  AGENT_RESTART = 1 // Requires agent restart
};

} // namespace facebook::fboss
