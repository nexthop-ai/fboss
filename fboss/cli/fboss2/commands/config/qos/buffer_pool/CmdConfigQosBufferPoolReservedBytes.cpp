/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolReservedBytes.h"

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/BufferPoolConfigUtils.h"

namespace facebook::fboss {

CmdConfigQosBufferPoolReservedBytesTraits::RetType
CmdConfigQosBufferPoolReservedBytes::queryClient(
    const HostInfo& /* hostInfo */,
    const BufferPoolName& bufferPoolName,
    const CmdConfigQosBufferPoolReservedBytesTraits::ObjectArgType&
        reservedBytesValue) {
  const std::string& poolName = bufferPoolName.getName();
  int32_t reservedBytes = reservedBytesValue.getValue();

  return setBufferPoolConfigField(
      poolName,
      "reserved-bytes",
      reservedBytes,
      [reservedBytes](cfg::BufferPoolConfig& config) {
        config.reservedBytes() = reservedBytes;
      });
}

void CmdConfigQosBufferPoolReservedBytes::printOutput(
    const CmdConfigQosBufferPoolReservedBytesTraits::RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

} // namespace facebook::fboss
