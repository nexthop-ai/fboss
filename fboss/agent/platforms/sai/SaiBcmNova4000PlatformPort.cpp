/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#include "fboss/agent/platforms/sai/SaiBcmNova4000PlatformPort.h"

namespace facebook::fboss {

void SaiBcmNova4000PlatformPort::linkStatusChanged(
    bool /*up*/,
    bool /*adminUp*/) {
  // TODO: set led color
}

void SaiBcmNova4000PlatformPort::externalState(PortLedExternalState /*lfs*/) {
  // TODO: set led color
}

} // namespace facebook::fboss
