/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#include "fboss/agent/platforms/sai/SaiNh5010fPlatformPort.h"

namespace facebook::fboss {

void SaiNh5010fPlatformPort::linkStatusChanged(bool /*up*/, bool /*adminUp*/) {
  // TODO: set led color
}

void SaiNh5010fPlatformPort::externalState(PortLedExternalState /*lfs*/) {
  // TODO: set led color
}

} // namespace facebook::fboss
