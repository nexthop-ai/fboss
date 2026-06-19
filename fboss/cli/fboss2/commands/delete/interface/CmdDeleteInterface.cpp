/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/delete/interface/CmdDeleteInterface.h"

#include <fmt/format.h>
#include <folly/String.h>
#include <algorithm>
#include <unordered_set>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/commands/config/interface/InterfaceIpUtils.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

namespace facebook::fboss {

namespace {
const std::unordered_set<std::string> kKnownAttributes = {
    "ip-address",
    "ipv6-address",
};

bool isKnownAttribute(const std::string& s) {
  std::string lower = s;
  std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
  return kKnownAttributes.find(lower) != kKnownAttributes.end();
}
} // namespace

CmdDeleteInterfaceTraits::RetType CmdDeleteInterface::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& interfacesConfig) {
  const auto& interfaces = interfacesConfig.getInterfaces();
  const auto& attributes = interfacesConfig.getAttributes();

  if (interfaces.empty()) {
    throw std::invalid_argument("No interface name provided");
  }

  if (attributes.size() != 1) {
    throw std::invalid_argument(
        "Expected <interface-list> <attribute> <value>");
  }

  const std::string& attribute = attributes[0].first;
  const std::string& ipAddress = attributes[0].second;

  if (!isKnownAttribute(attribute)) {
    throw std::invalid_argument(
        fmt::format(
            "Unknown attribute '{}'. Valid attributes are: ip-address, ipv6-address",
            attribute));
  }

  // Validate CIDR format and IP version match — let exceptions escape
  validateInterfaceIpAttr(attribute, ipAddress);

  bool expectV6 = (attribute == "ipv6-address");
  const std::string ipKind = expectV6 ? "IPv6 address" : "IP address";

  std::vector<std::string> deleted;
  std::vector<std::string> notConfigured;

  for (const utils::Intf& intf : interfaces) {
    cfg::Interface* interface = intf.getInterface();
    if (!interface) {
      throw std::runtime_error(
          fmt::format("Interface '{}' not found", intf.name()));
    }
    auto& ipAddresses = *interface->ipAddresses();
    auto it = std::find(ipAddresses.begin(), ipAddresses.end(), ipAddress);
    if (it == ipAddresses.end()) {
      notConfigured.push_back(intf.name());
    } else {
      ipAddresses.erase(it);
      deleted.push_back(intf.name());
    }
  }

  if (!deleted.empty()) {
    ConfigSession::getInstance().saveConfig();
  }

  if (deleted.empty()) {
    return fmt::format(
        "{} {} not configured on interface(s) {}",
        ipKind,
        ipAddress,
        folly::join(", ", notConfigured));
  }
  if (notConfigured.empty()) {
    return fmt::format(
        "Successfully deleted {} {} from interface(s) {}",
        ipKind,
        ipAddress,
        folly::join(", ", deleted));
  }
  return fmt::format(
      "Successfully deleted {} {} from interface(s) {}; "
      "not configured on {}",
      ipKind,
      ipAddress,
      folly::join(", ", deleted),
      folly::join(", ", notConfigured));
}

void CmdDeleteInterface::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdDeleteInterface, CmdDeleteInterfaceTraits>::run();

} // namespace facebook::fboss
