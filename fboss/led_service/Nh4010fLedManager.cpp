// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/led_service/Nh4010fLedManager.h"
#include "fboss/agent/platforms/common/nh4010f/Nh4010fPlatformMapping.h"
#include "fboss/lib/bsp/nh4010f/Nh4010fBspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Nh4010fLedManager ctor()
 *
 * Nh4010fLedManager constructor will create the LedManager object for
 * Nh4010f platform
 */
Nh4010fLedManager::Nh4010fLedManager() : BspLedManager() {
  init<Nh4010fBspPlatformMapping, Nh4010fPlatformMapping>();
  XLOG(INFO) << "Created Nh4010f BSP LED Manager";
}

} // namespace facebook::fboss
