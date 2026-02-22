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

#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/interface/CmdConfigInterface.h"
<<<<<<< HEAD
#include "fboss/cli/fboss2/utils/InterfacesConfig.h"

namespace facebook::fboss {

struct CmdConfigInterfaceSwitchportTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigInterface;
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_NONE;
  using ObjectArgType = std::monostate;
  using RetType = std::string;
};

class CmdConfigInterfaceSwitchport : public CmdHandler<
                                         CmdConfigInterfaceSwitchport,
                                         CmdConfigInterfaceSwitchportTraits> {
 public:
  RetType queryClient(
      const HostInfo& /* hostInfo */,
      const utils::InterfacesConfig& interfaceConfig) {
    // Get the interfaces from the config (ignoring any attributes)
    const auto& interfaces = interfaceConfig.getInterfaces();
    if (interfaces.empty()) {
      throw std::invalid_argument("No interface name provided");
    }
||||||| 7e29d6aa34
=======
#include "fboss/cli/fboss2/utils/CmdUtils.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

namespace facebook::fboss {

struct CmdConfigInterfaceSwitchportTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigInterface;
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_NONE;
  using ObjectArgType = std::monostate;
  using RetType = std::string;
};

class CmdConfigInterfaceSwitchport : public CmdHandler<
                                         CmdConfigInterfaceSwitchport,
                                         CmdConfigInterfaceSwitchportTraits> {
 public:
  RetType queryClient(
      const HostInfo& /* hostInfo */,
      const utils::InterfaceList& /* interfaces */) {
>>>>>>> 716bedba537020d694677496e22daa66dbcb4d42
    throw std::runtime_error(
        "Incomplete command, please use one of the subcommands");
  }

  void printOutput(const RetType& /* model */) {}
};

} // namespace facebook::fboss
