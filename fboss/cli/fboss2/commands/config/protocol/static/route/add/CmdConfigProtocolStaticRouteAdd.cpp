/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/protocol/static/route/add/CmdConfigProtocolStaticRouteAdd.h"

#include <fmt/format.h>
#include <folly/String.h>
#include <algorithm>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.cpp"
#include "fboss/cli/fboss2/session/ConfigSession.h"

namespace facebook::fboss {

template <typename RouteArgType>
std::string addStaticRouteImpl(const RouteArgType& routeArg) {
  auto& config = ConfigSession::getInstance().getAgentConfig();
  auto& swConfig = *config.sw();

  const std::string& prefix = routeArg.getPrefix();
  StaticRouteType routeType = routeArg.getRouteType();

  if (routeType == StaticRouteType::NULL_ROUTE) {
    cfg::StaticRouteNoNextHops newRoute;
    newRoute.routerID() = 0;
    newRoute.prefix() = prefix;

    auto& nullRoutes = *swConfig.staticRoutesToNull();
    auto it = std::find_if(
        nullRoutes.begin(), nullRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });

    if (it != nullRoutes.end()) {
      return fmt::format("Static null0 route {} already exists", prefix);
    }

    auto& nhopRoutes = *swConfig.staticRoutesWithNhops();
    auto nhopIt = std::find_if(
        nhopRoutes.begin(), nhopRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (nhopIt != nhopRoutes.end()) {
      nhopRoutes.erase(nhopIt);
    }

    auto& cpuRoutes = *swConfig.staticRoutesToCPU();
    auto cpuIt = std::find_if(
        cpuRoutes.begin(), cpuRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (cpuIt != cpuRoutes.end()) {
      cpuRoutes.erase(cpuIt);
    }

    nullRoutes.push_back(newRoute);

    ConfigSession::getInstance().saveConfig();
    return fmt::format("Successfully added static null0 route {}", prefix);
  } else if (routeType == StaticRouteType::CPU_ROUTE) {
    cfg::StaticRouteNoNextHops newRoute;
    newRoute.routerID() = 0;
    newRoute.prefix() = prefix;

    auto& cpuRoutes = *swConfig.staticRoutesToCPU();
    auto it = std::find_if(
        cpuRoutes.begin(), cpuRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });

    if (it != cpuRoutes.end()) {
      return fmt::format("Static CPU route {} already exists", prefix);
    }

    auto& nhopRoutes = *swConfig.staticRoutesWithNhops();
    auto nhopIt = std::find_if(
        nhopRoutes.begin(), nhopRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (nhopIt != nhopRoutes.end()) {
      nhopRoutes.erase(nhopIt);
    }

    auto& nullRoutes = *swConfig.staticRoutesToNull();
    auto nullIt = std::find_if(
        nullRoutes.begin(), nullRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (nullIt != nullRoutes.end()) {
      nullRoutes.erase(nullIt);
    }

    cpuRoutes.push_back(newRoute);

    ConfigSession::getInstance().saveConfig();
    return fmt::format("Successfully added static CPU route {}", prefix);
  } else {
    cfg::StaticRouteWithNextHops newRoute;
    newRoute.routerID() = 0;
    newRoute.prefix() = prefix;
    newRoute.nexthops() = routeArg.getNexthops();

    auto& nhopRoutes = *swConfig.staticRoutesWithNhops();
    auto it = std::find_if(
        nhopRoutes.begin(), nhopRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });

    if (it != nhopRoutes.end()) {
      it->nexthops() = routeArg.getNexthops();

      ConfigSession::getInstance().saveConfig();
      std::string nexthopsList = folly::join(", ", routeArg.getNexthops());
      return fmt::format(
          "Successfully updated static route {} with nexthop{}: {}",
          prefix,
          routeArg.getNexthops().size() > 1 ? "s" : "",
          nexthopsList);
    }

    auto& nullRoutes = *swConfig.staticRoutesToNull();
    auto nullIt = std::find_if(
        nullRoutes.begin(), nullRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (nullIt != nullRoutes.end()) {
      nullRoutes.erase(nullIt);
    }

    auto& cpuRoutes = *swConfig.staticRoutesToCPU();
    auto cpuIt = std::find_if(
        cpuRoutes.begin(), cpuRoutes.end(), [&prefix](const auto& route) {
          return *route.prefix() == prefix;
        });
    if (cpuIt != cpuRoutes.end()) {
      cpuRoutes.erase(cpuIt);
    }

    nhopRoutes.push_back(newRoute);

    ConfigSession::getInstance().saveConfig();
    std::string nexthopsList = folly::join(", ", routeArg.getNexthops());
    return fmt::format(
        "Successfully added static route {} with nexthop{}: {}",
        prefix,
        routeArg.getNexthops().size() > 1 ? "s" : "",
        nexthopsList);
  }
}

CmdConfigProtocolStaticIpRouteAddTraits::RetType
CmdConfigProtocolStaticIpRouteAdd::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& routeArg) {
  return addStaticRouteImpl(routeArg);
}

void CmdConfigProtocolStaticIpRouteAdd::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

CmdConfigProtocolStaticIpv6RouteAddTraits::RetType
CmdConfigProtocolStaticIpv6RouteAdd::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& routeArg) {
  return addStaticRouteImpl(routeArg);
}

void CmdConfigProtocolStaticIpv6RouteAdd::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

template std::string addStaticRouteImpl<StaticRouteAddIpArg>(
    const StaticRouteAddIpArg& routeArg);

template std::string addStaticRouteImpl<StaticRouteAddIpv6Arg>(
    const StaticRouteAddIpv6Arg& routeArg);

template void CmdHandler<
    CmdConfigProtocolStaticIpRouteAdd,
    CmdConfigProtocolStaticIpRouteAddTraits>::run();

template void CmdHandler<
    CmdConfigProtocolStaticIpv6RouteAdd,
    CmdConfigProtocolStaticIpv6RouteAddTraits>::run();

} // namespace facebook::fboss
