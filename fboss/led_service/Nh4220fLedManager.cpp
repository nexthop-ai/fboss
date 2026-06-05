// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/led_service/Nh4220fLedManager.h"
#include "fboss/agent/platforms/common/nh4220f/Nh4220fPlatformMapping.h"
#include "fboss/lib/bsp/nh4220f/Nh4220fBspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Nh4220fLedManager ctor()
 *
 * Nh4220fLedManager constructor will create the LedManager object for
 * Nh4220f platform
 */
Nh4220fLedManager::Nh4220fLedManager() : BspLedManager() {
  init<Nh4220fBspPlatformMapping, Nh4220fPlatformMapping>();
  XLOG(INFO) << "Created Nh4220f BSP LED Manager";
}

} // namespace facebook::fboss
