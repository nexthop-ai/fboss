// Copyright (c) 2025-present, Nexthop Systems, Inc.

#include "fboss/led_service/Nova4000LedManager.h"
#include "fboss/agent/platforms/common/nova4000/Nova4000PlatformMapping.h"
#include "fboss/lib/bsp/nova4000/Nova4000BspPlatformMapping.h"

namespace facebook::fboss {

/*
 * Nova4000LedManager ctor()
 *
 * Nova4000LedManager constructor will create the LedManager object for
 * nova4000 platform
 */
Nova4000LedManager::Nova4000LedManager() : BspLedManager() {
  init<Nova4000BspPlatformMapping, Nova4000PlatformMapping>();
  XLOG(INFO) << "Created Nova4000 BSP LED Manager";
}

} // namespace facebook::fboss
