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
#include <variant>
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/delete/interface/CmdDeleteInterface.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/cli/fboss2/utils/InterfaceList.h"

namespace facebook::fboss {

// `delete interface <port-list> queuing-policy` clears
// sw.ports[*].portQueueConfigName. The command takes no value: a port either
// names a queuing policy or it does not. Ports left without a name fall back
// to sw.defaultPortQueues (ApplyThriftConfig::updatePortQueues).
struct CmdDeleteInterfaceQueuingPolicyTraits : public WriteCommandTraits {
  using ParentCmd = CmdDeleteInterface;
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_NONE;
  using ObjectArgType = std::monostate;
  using RetType = std::string;
};

class CmdDeleteInterfaceQueuingPolicy
    : public CmdHandler<
          CmdDeleteInterfaceQueuingPolicy,
          CmdDeleteInterfaceQueuingPolicyTraits> {
 public:
  using RetType = CmdDeleteInterfaceQueuingPolicyTraits::RetType;

  RetType queryClient(
      const HostInfo& hostInfo,
      const utils::InterfaceList& interfaces);

  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
