/*
 *  Copyright (c) 2025-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#pragma once

#include "fboss/led_service/BspLedManager.h"
#include "fboss/lib/bsp/BspSystemContainer.h"

namespace facebook::fboss {

/*
 * Nh4010LedManager class definiton:
 *
 * The BspLedManager class managing all LED in the system. The object is spawned
 * by LED Service. This will subscribe to Fsdb to get Switch state update and
 * then update the LED in hardware
 */
class Nh4010LedManager : public BspLedManager {
 public:
  Nh4010LedManager();
  virtual ~Nh4010LedManager() override {}

  // Forbidden copy constructor and assignment operator
  Nh4010LedManager(Nh4010LedManager const&) = delete;
  Nh4010LedManager& operator=(Nh4010LedManager const&) = delete;
};

} // namespace facebook::fboss
