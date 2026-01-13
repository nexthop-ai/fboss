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

#include <fmt/format.h>
#include <functional>
#include <map>
#include <string>

#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"

namespace facebook::fboss {

/**
 * Helper function to set a buffer pool configuration field.
 *
 * This function handles the common logic for all buffer pool configuration
 * commands (shared-bytes, headroom-bytes, reserved-bytes):
 * - Gets or creates the buffer pool config map
 * - Gets or creates the specific buffer pool entry
 * - Calls the setter to update the specific field
 * - Saves the config
 * - Updates the required action level to AGENT_RESTART
 *
 * @param poolName The name of the buffer pool to configure
 * @param fieldName The name of the field being set (for the success message)
 * @param value The value to set
 * @param setter A lambda that sets the specific field on the BufferPoolConfig.
 *               For new configs, it receives a reference to the new config.
 *               For existing configs, it receives a reference to the existing
 * config.
 * @return A success message string
 */
template <typename SetterFn>
std::string setBufferPoolConfigField(
    const std::string& poolName,
    const std::string& fieldName,
    int32_t value,
    SetterFn setter) {
  auto& session = ConfigSession::getInstance();
  auto& agentConfig = session.getAgentConfig();
  auto& switchConfig = *agentConfig.sw();

  // Get or create the bufferPoolConfigs map
  if (!switchConfig.bufferPoolConfigs()) {
    switchConfig.bufferPoolConfigs() =
        std::map<std::string, cfg::BufferPoolConfig>{};
  }

  auto& bufferPoolConfigs = *switchConfig.bufferPoolConfigs();

  // Check if the buffer pool exists
  auto it = bufferPoolConfigs.find(poolName);
  if (it == bufferPoolConfigs.end()) {
    // Create a new buffer pool config
    // Note: sharedBytes is required, so we default it to 0
    cfg::BufferPoolConfig newConfig;
    newConfig.sharedBytes() = 0;
    setter(newConfig);
    bufferPoolConfigs[poolName] = std::move(newConfig);
  } else {
    // Update the existing buffer pool config
    setter(it->second);
  }

  // Save the updated config and update the required action level
  // Buffer pool changes always require agent restart
  session.saveConfig(cli::ConfigActionLevel::AGENT_RESTART);

  return fmt::format(
      "Successfully set {} for buffer-pool '{}' to {}",
      fieldName,
      poolName,
      value);
}

} // namespace facebook::fboss
