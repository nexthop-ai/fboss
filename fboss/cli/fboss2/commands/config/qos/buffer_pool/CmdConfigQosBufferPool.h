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

#include <folly/Conv.h>
#include <folly/String.h>
#include <re2/re2.h>
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/qos/CmdConfigQos.h"
#include "fboss/cli/fboss2/utils/CmdUtils.h"

namespace facebook::fboss {

// Custom type for buffer pool name argument
class BufferPoolName : public utils::BaseObjectArgType<std::string> {
 public:
  /* implicit */ BufferPoolName(std::vector<std::string> v) {
    if (v.empty()) {
      throw std::invalid_argument("Buffer pool name is required");
    }
    if (v.size() != 1) {
      throw std::invalid_argument(
          "Expected single buffer pool name, got: " + folly::join(", ", v));
    }
    const auto& name = v[0];
    // Valid pool name: starts with letter, alphanumeric + underscore/hyphen,
    // 1-64 chars
    static const re2::RE2 kValidPoolNamePattern(
        "^[a-zA-Z][a-zA-Z0-9_-]{0,63}$");
    if (!re2::RE2::FullMatch(name, kValidPoolNamePattern)) {
      throw std::invalid_argument(
          "Invalid buffer pool name: '" + name +
          "'. Name must start with a letter, contain only alphanumeric "
          "characters, underscores, or hyphens, and be 1-64 characters long.");
    }
    data_.push_back(name);
  }

  const std::string& getName() const {
    return data_[0];
  }

  const static utils::ObjectArgTypeId id =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_BUFFER_POOL_NAME;
};

struct CmdConfigQosBufferPoolTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigQos;
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_BUFFER_POOL_NAME;
  using ObjectArgType = BufferPoolName;
  using RetType = std::string;
};

class CmdConfigQosBufferPool
    : public CmdHandler<CmdConfigQosBufferPool, CmdConfigQosBufferPoolTraits> {
 public:
  using ObjectArgType = CmdConfigQosBufferPoolTraits::ObjectArgType;
  using RetType = CmdConfigQosBufferPoolTraits::RetType;

  RetType queryClient(
      const HostInfo& /* hostInfo */,
      const ObjectArgType& /* bufferPoolName */) {
    throw std::runtime_error(
        "Incomplete command, please use one of the subcommands: "
        "shared-bytes, headroom-bytes, reserved-bytes");
  }

  void printOutput(const RetType& /* model */) {}
};

} // namespace facebook::fboss
