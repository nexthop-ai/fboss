/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#pragma once

#include "fboss/led_service/BspLedManager.h"

namespace facebook::fboss {

/*
 * Nh4220fLedManager class definiton:
 *
 * The BspLedManager class managing all LED in the system. The object is spawned
 * by LED Service. This will subscribe to Fsdb to get Switch state update and
 * then update the LED in hardware
 */
class Nh4220fLedManager : public BspLedManager {
 public:
  Nh4220fLedManager();
  ~Nh4220fLedManager() override = default;

  Nh4220fLedManager(Nh4220fLedManager const&) = delete;
  Nh4220fLedManager& operator=(Nh4220fLedManager const&) = delete;
  Nh4220fLedManager(Nh4220fLedManager&&) = delete;
  Nh4220fLedManager& operator=(Nh4220fLedManager&&) = delete;
};

} // namespace facebook::fboss
