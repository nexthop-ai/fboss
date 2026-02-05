// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include "fboss/led_service/Wedge800BNHPLedManager.h"
#include "fboss/agent/platforms/common/wedge800bnhp/Wedge800BNHPPlatformMapping.h"
#include "fboss/lib/bsp/wedge800bnhp/Wedge800BNHPBspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Wedge800BNHPLedManager ctor()
 *
 * Wedge800BNHPLedManager constructor will create the LedManager object for
 * Wedge800BNHP platform
 */
Wedge800BNHPLedManager::Wedge800BNHPLedManager() : BspLedManager() {
  init<Wedge800BNHPBspPlatformMapping, Wedge800BNHPPlatformMapping>();
  XLOG(INFO) << "Created Wedge800BNHP BSP LED Manager";
}

} // namespace facebook::fboss
