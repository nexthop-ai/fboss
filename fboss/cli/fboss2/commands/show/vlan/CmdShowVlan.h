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

#include <iostream>
#include <string_view>
#include <variant>
#include "fboss/agent/gen-cpp2/switch_config_types.h"
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/show/vlan/gen-cpp2/model_types.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

namespace facebook::fboss {

struct CmdShowVlanTraits : public ReadCommandTraits {
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_NONE;
  using ObjectArgType = std::monostate;
  using RetType = cli::ShowVlanModel;
  static constexpr bool ALLOW_FILTERING = true;
  static constexpr bool ALLOW_AGGREGATION = true;

  // Human description for auto-generated CLI reference wiki.
  static std::string_view description();
};

class CmdShowVlan : public CmdHandler<CmdShowVlan, CmdShowVlanTraits> {
 public:
  using ObjectArgType = CmdShowVlanTraits::ObjectArgType;
  using RetType = CmdShowVlanTraits::RetType;

  RetType queryClient(const HostInfo& hostInfo);

  // Builds the model from a SwitchConfig. Split out from queryClient (which
  // only fetches the running config off the agent) so the VLAN/port/interface
  // join can be unit tested without a live agent.
  RetType createModel(const cfg::SwitchConfig& swConfig);

  void printOutput(const RetType& model, std::ostream& out = std::cout);

  // Synthetic populated model for CLI reference wiki documentation.
  static RetType sampleModel();
};

} // namespace facebook::fboss
