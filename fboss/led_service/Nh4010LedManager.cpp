// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.

#include "fboss/led_service/Nh4010LedManager.h"
#include "fboss/agent/platforms/common/nh4010/Nh4010PlatformMapping.h"
#include "fboss/lib/bsp/BspGenericSystemContainer.h"
#include "fboss/lib/bsp/nh4010/Nh4010BspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Nh4010LedManager ctor()
 *
 * Nh4010LedManager constructor will create the LedManager object for
 * Nh4010 platform
 */
Nh4010LedManager::Nh4010LedManager() : BspLedManager() {
  init<Nh4010BspPlatformMapping, Nh4010PlatformMapping>();
  XLOG(INFO) << "Created Nh4010 BSP LED Manager";
}

} // namespace facebook::fboss
