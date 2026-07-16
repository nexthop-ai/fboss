/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/switch/CmdConfigSwitch.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <iostream>

namespace facebook::fboss {

CmdConfigSwitchTraits::RetType CmdConfigSwitch::queryClient(
    const HostInfo& /* hostInfo */) {
<<<<<<< HEAD
  return "Switch configuration commands. Use subcommands: admin-distance, hostname, icmpv4-unavailable-src-addr";
||||||| ac0f8c3e61
=======
  return "Switch configuration commands. Use subcommands: admin-distance, icmpv4-unavailable-src-addr, hostname";
>>>>>>> 4accde58608fff22a8b2d33fb7c592899d266899
}

void CmdConfigSwitch::printOutput(const RetType& output) {
  std::cout << output << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdConfigSwitch, CmdConfigSwitchTraits>::run();

} // namespace facebook::fboss
