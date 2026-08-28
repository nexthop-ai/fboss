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
#include "fboss/cli/fboss2/commands/delete/acl/CmdDeleteAcl.h"
#include "fboss/cli/fboss2/utils/CmdUtilsCommon.h"

namespace facebook::fboss {

// Argument for `delete acl table-group <group-name>`.
class AclTableGroupDeleteArgs : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */ AclTableGroupDeleteArgs( // NOLINT(google-explicit-constructor)
      std::vector<std::string> v);

  const std::string& getGroupName() const {
    return groupName_;
  }

 private:
  std::string groupName_;
};

struct CmdDeleteAclTableGroupTraits : public WriteCommandTraits {
  using ParentCmd = CmdDeleteAcl;
  using ObjectArgType = AclTableGroupDeleteArgs;
  using RetType = std::string;
  static void addCliArg(CLI::App& cmd, std::vector<std::string>& args) {
    cmd.add_option(
           "acl_table_group_delete",
           args,
           "<group-name>: removes the AclTableGroup, every table it holds, "
           "and any traffic-policy actions attached to their entries")
        ->required()
        ->expected(1);
  }
};

class CmdDeleteAclTableGroup
    : public CmdHandler<CmdDeleteAclTableGroup, CmdDeleteAclTableGroupTraits> {
 public:
  using ObjectArgType = CmdDeleteAclTableGroupTraits::ObjectArgType;
  using RetType = CmdDeleteAclTableGroupTraits::RetType;

  RetType queryClient(const HostInfo& hostInfo, const ObjectArgType& args);
  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
