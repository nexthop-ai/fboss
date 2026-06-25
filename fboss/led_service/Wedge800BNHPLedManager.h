/*
 *  Copyright (c) 2018-present, Facebook, Inc.
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
 * Wedge800BNHPLedManager class definition:
 *
 * The BspLedManager class managing all LED in the system. The object is spawned
 * by LED Service. This will subscribe to Fsdb to get Switch state update and
 * then update the LED in hardware
 */
class Wedge800BNHPLedManager : public BspLedManager {
 public:
  Wedge800BNHPLedManager();
  ~Wedge800BNHPLedManager() override = default;

  // Forbidden copy constructor and assignment operator
  Wedge800BNHPLedManager(Wedge800BNHPLedManager const&) = delete;
  Wedge800BNHPLedManager& operator=(Wedge800BNHPLedManager const&) = delete;
  Wedge800BNHPLedManager(Wedge800BNHPLedManager&&) = delete;
  Wedge800BNHPLedManager& operator=(Wedge800BNHPLedManager&&) = delete;
};

} // namespace facebook::fboss
