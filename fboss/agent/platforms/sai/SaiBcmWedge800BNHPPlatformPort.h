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

#include "fboss/agent/platforms/sai/SaiBcmWedge800BACTPlatformPort.h"

namespace facebook::fboss {

class SaiBcmWedge800BNHPPlatformPort : public SaiBcmWedge800BACTPlatformPort {
 public:
  SaiBcmWedge800BNHPPlatformPort(PortID id, SaiPlatform* platform)
      : SaiBcmWedge800BACTPlatformPort(id, platform) {}
};

} // namespace facebook::fboss
