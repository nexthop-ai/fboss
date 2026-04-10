/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/interface/CmdConfigInterface.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/Conv.h>
#include <folly/String.h>
#include <cctype>
#include <cstdint>
#include <exception>
#include <iostream>
#include <ostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/commands/config/interface/SpeedValidation.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

namespace facebook::fboss {

CmdConfigInterfaceTraits::RetType CmdConfigInterface::queryClient(
    const HostInfo& hostInfo,
    const ObjectArgType& interfaceConfig) {
  const auto& interfaces = interfaceConfig.getInterfaces();
  const auto& attributes = interfaceConfig.getAttributes();

  if (interfaces.empty()) {
    throw std::invalid_argument("No interface name provided");
  }

  // If no attributes provided, this is a pass-through to subcommands
  if (!interfaceConfig.hasAttributes()) {
    throw std::runtime_error(
        "Incomplete command. Either provide attributes (description, mtu, speed) "
        "or use a subcommand (switchport)");
  }

  std::vector<std::string> results;

  // Process each attribute
  for (const auto& [attr, value] : attributes) {
    if (attr == "description") {
      // Set description for all ports
      for (const utils::Intf& intf : interfaces) {
        cfg::Port* port = intf.getPort();
        if (port) {
          port->description() = value;
        }
      }
      results.push_back(fmt::format("description=\"{}\"", value));
    } else if (attr == "mtu") {
      // Validate and set MTU for all interfaces
      int32_t mtu = 0;
      try {
        mtu = folly::to<int32_t>(value);
      } catch (const std::exception&) {
        throw std::invalid_argument(
            fmt::format("Invalid MTU value '{}': must be an integer", value));
      }

      if (mtu < utils::kMtuMin || mtu > utils::kMtuMax) {
        throw std::invalid_argument(
            fmt::format(
                "MTU value {} is out of range. Valid range is {}-{}",
                mtu,
                utils::kMtuMin,
                utils::kMtuMax));
      }

      for (const utils::Intf& intf : interfaces) {
        cfg::Interface* interface = intf.getInterface();
        if (interface) {
          interface->mtu() = mtu;
        }
      }
      results.push_back(fmt::format("mtu={}", mtu));
    } else if (attr == "speed") {
      // Parse requested speed using unified API
      cfg::PortSpeed requestedSpeed = SpeedValidator::parseSpeed(value);

      // If speed is DEFAULT (auto or "0"), skip validation and just apply
      if (requestedSpeed == cfg::PortSpeed::DEFAULT) {
        for (const utils::Intf& intf : interfaces) {
          cfg::Port* port = intf.getPort();
          if (port) {
            port->speed() = requestedSpeed;
          }
        }
        results.emplace_back("speed=auto");
        continue;
      }

      // For non-auto speeds, use SpeedValidator for comprehensive validation.
      // Construct once (queries Thrift) then reuse across all ports.
      SpeedValidator validator(hostInfo);

      // Validate and apply speed for each port
      for (const utils::Intf& intf : interfaces) {
        cfg::Port* port = intf.getPort();

        const std::string& portName = *port->name();

        // Validate speed and get matching profiles
        auto matchingProfiles = validator.validateSpeed(portName, value);

        // Select the first matching profile
        cfg::PortProfileID selectedProfile = matchingProfiles[0];

        // Set both speed and profile
        port->speed() = requestedSpeed;
        port->profileID() = selectedProfile;
      }

      results.push_back(
          fmt::format("speed={}", static_cast<int64_t>(requestedSpeed)));
    }
  }

  // Save the updated config
  ConfigSession::getInstance().saveConfig();

  std::string interfaceList = folly::join(", ", interfaces.getNames());
  std::string attrList = folly::join(", ", results);
  return fmt::format(
      "Successfully configured interface(s) {}: {}", interfaceList, attrList);
}

void CmdConfigInterface::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdConfigInterface, CmdConfigInterfaceTraits>::run();

} // namespace facebook::fboss
