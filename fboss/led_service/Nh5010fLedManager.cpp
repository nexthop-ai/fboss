// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/led_service/Nh5010fLedManager.h"
#include "fboss/agent/platforms/common/nh5010f/Nh5010fPlatformMapping.h"
#include "fboss/lib/bsp/nh5010f/Nh5010fBspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Nh5010fLedManager ctor()
 *
 * Nh5010fLedManager constructor will create the LedManager object for
 * Nh5010f platform
 */
Nh5010fLedManager::Nh5010fLedManager() : BspLedManager() {
  init<Nh5010fBspPlatformMapping, Nh5010fPlatformMapping>();
  XLOG(INFO) << "Created Nh5010f BSP LED Manager";
}

} // namespace facebook::fboss
