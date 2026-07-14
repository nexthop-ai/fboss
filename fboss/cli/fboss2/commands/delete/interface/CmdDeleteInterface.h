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
#include <vector>
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/interface/InterfaceAttrArgsBase.h"

namespace facebook::fboss {

/*
 * InterfaceDeleteConfig captures interface/port names plus the attributes to
 * delete (reset to default or remove by value) for the `delete interface`
 * command.
 *
 * Usage: delete interface <port-list> [<attr> [<value>] ...]
 *
<<<<<<< HEAD
 * Tokens before the first known attribute name are interface/port names; the
 * rest are attribute names. Most attributes are valueless (delete resets to
 * default); ip-address / ipv6-address take the specific address to remove.
 *
 * Supported delete attributes (reset to default):
||||||| 7965f21dbd
 * Tokens before the first known attribute name are interface/port names; the
 * rest are attribute names (valueless — delete always resets to default).
 *
 * Supported delete attributes (reset to default):
=======
 * Valueless attributes (reset to default):
>>>>>>> ac0f8c3e61c71eb95eca42307bedf46e7fd35502
 *   loopback-mode, lldp-expected-value, lldp-expected-chassis,
 *   lldp-expected-ttl, lldp-expected-port-desc, lldp-expected-system-name,
 *   lldp-expected-system-desc
<<<<<<< HEAD
 * Supported delete attributes (with value):
 *   ip-address <cidr>, ipv6-address <cidr>
||||||| 7965f21dbd
=======
 *
 * Valued attributes (remove specific entry):
 *   ip-address <cidr>    — remove an IPv4 address (e.g. 10.0.0.1/24)
 *   ipv6-address <cidr>  — remove an IPv6 address (e.g. 2001:db8::1/64)
>>>>>>> ac0f8c3e61c71eb95eca42307bedf46e7fd35502
 */
class InterfaceDeleteConfig : public InterfaceAttrArgsBase {
 public:
  // NOLINTNEXTLINE(google-explicit-constructor)
  /* implicit */ InterfaceDeleteConfig(const std::vector<std::string>& v);
};

struct CmdDeleteInterfaceTraits : public WriteCommandTraits {
  using ParentCmd = void;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    cmd.add_option(
        "interface_delete_config",
        args,
        "<port-list> [loopback-mode|lldp-expected-*|ip-address <cidr>|ipv6-address <cidr>]");
  }
  using ObjectArgType = InterfaceDeleteConfig;
  using RetType = std::string;
};

class CmdDeleteInterface
    : public CmdHandler<CmdDeleteInterface, CmdDeleteInterfaceTraits> {
 public:
  using ObjectArgType = CmdDeleteInterfaceTraits::ObjectArgType;
  using RetType = CmdDeleteInterfaceTraits::RetType;

  RetType queryClient(
      const HostInfo& hostInfo,
      const ObjectArgType& deleteConfig);

  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
