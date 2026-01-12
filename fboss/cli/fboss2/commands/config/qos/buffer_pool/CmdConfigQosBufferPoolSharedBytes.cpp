/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolSharedBytes.h"

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/BufferPoolConfigUtils.h"

namespace facebook::fboss {

CmdConfigQosBufferPoolSharedBytesTraits::RetType
CmdConfigQosBufferPoolSharedBytes::queryClient(
    const HostInfo& /* hostInfo */,
    const BufferPoolName& bufferPoolName,
    const CmdConfigQosBufferPoolSharedBytesTraits::ObjectArgType&
        sharedBytesValue) {
  const std::string& poolName = bufferPoolName.getName();
  int32_t sharedBytes = sharedBytesValue.getValue();

  return setBufferPoolConfigField(
      poolName,
      "shared-bytes",
      sharedBytes,
      [sharedBytes](cfg::BufferPoolConfig& config) {
        config.sharedBytes() = sharedBytes;
      });
}

void CmdConfigQosBufferPoolSharedBytes::printOutput(
    const CmdConfigQosBufferPoolSharedBytesTraits::RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

} // namespace facebook::fboss
