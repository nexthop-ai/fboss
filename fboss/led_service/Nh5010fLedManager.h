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
 * Nh5010fLedManager class definiton:
 *
 * The BspLedManager class managing all LED in the system. The object is spawned
 * by LED Service. This will subscribe to Fsdb to get Switch state update and
 * then update the LED in hardware
 */
class Nh5010fLedManager : public BspLedManager {
 public:
  Nh5010fLedManager();
  virtual ~Nh5010fLedManager() override {}

  // Forbidden copy constructor and assignment operator
  Nh5010fLedManager(Nh5010fLedManager const&) = delete;
  Nh5010fLedManager& operator=(Nh5010fLedManager const&) = delete;
};

} // namespace facebook::fboss
