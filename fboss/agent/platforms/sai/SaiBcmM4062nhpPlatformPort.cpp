/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#include "fboss/agent/platforms/sai/SaiBcmM4062nhpPlatformPort.h"

namespace facebook::fboss {

void SaiBcmM4062nhpPlatformPort::linkStatusChanged(
    bool /*up*/,
    bool /*adminUp*/) {
  // TODO: set led color
}

void SaiBcmM4062nhpPlatformPort::externalState(PortLedExternalState /*lfs*/) {
  // TODO: set led color
}

} // namespace facebook::fboss
