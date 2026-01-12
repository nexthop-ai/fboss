/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/CmdConfigQosBufferPoolHeadroomBytes.h"

#include "fboss/cli/fboss2/commands/config/qos/buffer_pool/BufferPoolConfigUtils.h"

namespace facebook::fboss {

CmdConfigQosBufferPoolHeadroomBytesTraits::RetType
CmdConfigQosBufferPoolHeadroomBytes::queryClient(
    const HostInfo& /* hostInfo */,
    const BufferPoolName& bufferPoolName,
    const CmdConfigQosBufferPoolHeadroomBytesTraits::ObjectArgType&
        headroomBytesValue) {
  const std::string& poolName = bufferPoolName.getName();
  int32_t headroomBytes = headroomBytesValue.getValue();

  return setBufferPoolConfigField(
      poolName,
      "headroom-bytes",
      headroomBytes,
      [headroomBytes](cfg::BufferPoolConfig& config) {
        config.headroomBytes() = headroomBytes;
      });
}

void CmdConfigQosBufferPoolHeadroomBytes::printOutput(
    const CmdConfigQosBufferPoolHeadroomBytesTraits::RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

} // namespace facebook::fboss
