/*
 *  Copyright (c) 2026 Nexthop Systems Inc.
 *  SPDX-License-Identifier: BSD-3-Clause
 */
#pragma once

#include "fboss/led_service/BspLedManager.h"

namespace facebook::fboss {

/*
 * Nova4000LedManager class definition:
 *
 * The BspLedManager class managing all LED in the system. The object is spawned
 * by LED Service. This will subscribe to Fsdb to get Switch state update and
 * then update the LED in hardware
 */
class Nova4000LedManager : public BspLedManager {
 public:
  Nova4000LedManager();
  ~Nova4000LedManager() override = default;

  // Forbidden copy and move constructors and assignment operators
  Nova4000LedManager(Nova4000LedManager const&) = delete;
  Nova4000LedManager& operator=(Nova4000LedManager const&) = delete;
  Nova4000LedManager(Nova4000LedManager&&) = delete;
  Nova4000LedManager& operator=(Nova4000LedManager&&) = delete;
};

} // namespace facebook::fboss
