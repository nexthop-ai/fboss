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
#include "fboss/cli/fboss2/CmdHandler.h"
#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPool.h"
#include "fboss/cli/fboss2/utils/CmdUtils.h"

namespace facebook::fboss {

// Custom type for buffer bytes argument with validation
class BufferBytesValue : public utils::BaseObjectArgType<int32_t> {
 public:
  /* implicit */ BufferBytesValue(std::vector<std::string> v) {
    if (v.empty()) {
      throw std::invalid_argument("Buffer bytes value is required");
    }
    if (v.size() != 1) {
      throw std::invalid_argument(
          "Expected single buffer bytes value, got: " + folly::join(", ", v));
    }

    try {
      int32_t bytes = folly::to<int32_t>(v[0]);
      if (bytes < 0) {
        throw std::invalid_argument(
            "Buffer bytes must be non-negative, got: " + std::to_string(bytes));
      }
      data_.push_back(bytes);
    } catch (const folly::ConversionError& e) {
      throw std::invalid_argument("Invalid buffer bytes value: " + v[0]);
    }
  }

  int32_t getValue() const {
    return data_[0];
  }

  const static utils::ObjectArgTypeId id =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_BUFFER_BYTES;
};

struct CmdConfigQosBufferPoolSharedBytesTraits : public WriteCommandTraits {
  using ParentCmd = CmdConfigQosBufferPool;
  static constexpr utils::ObjectArgTypeId ObjectArgTypeId =
      utils::ObjectArgTypeId::OBJECT_ARG_TYPE_ID_BUFFER_BYTES;
  using ObjectArgType = BufferBytesValue;
  using RetType = std::string;
};

class CmdConfigQosBufferPoolSharedBytes
    : public CmdHandler<
          CmdConfigQosBufferPoolSharedBytes,
          CmdConfigQosBufferPoolSharedBytesTraits> {
 public:
  using ObjectArgType = CmdConfigQosBufferPoolSharedBytesTraits::ObjectArgType;
  using RetType = CmdConfigQosBufferPoolSharedBytesTraits::RetType;

  RetType queryClient(
      const HostInfo& hostInfo,
      const BufferPoolName& bufferPoolName,
      const ObjectArgType& sharedBytesValue);

  void printOutput(const RetType& logMsg);
};

} // namespace facebook::fboss
