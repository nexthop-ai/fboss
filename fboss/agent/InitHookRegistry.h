/*
 *  Copyright (c) 2026-present, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#pragma once

#include <functional>

namespace facebook::fboss {

class SwSwitch;

// Generic lifecycle hooks for FBOSS agent init. Independent libraries
// (e.g. platform-specific glue, alternative dataplanes) register callbacks
// at process startup via static initializers; FBOSS invokes them at the
// matching lifecycle point. Defaults are no-ops when nothing is registered.
// The callback signature selects the lifecycle point.

// Fired from HwAgentMain after fbossCommonInit() and before SAI is
// initialized -- the earliest hook point in the hw_agent process.
using PreSaiInitHook = std::function<void()>;

// Fired from SwSwitch::initialConfigApplied after the initial SwitchState has
// been fully published and observers can meaningfully see it.
//
// Contract: a single process may bring up more than one SwSwitch over its
// lifetime, so a PostConfigApplied hook must be idempotent and safe to run
// against multiple SwSwitch instances, and it must not retain the SwSwitch
// pointer beyond the lifetime of the switch it is handed.
using PostConfigAppliedHook = std::function<void(SwSwitch*)>;

class InitHookRegistry {
 public:
  static void registerHook(PreSaiInitHook hook);
  static void registerHook(PostConfigAppliedHook hook);

  static void runPreSaiInitHooks();
  static void runPostConfigAppliedHooks(SwSwitch* sw);

  // Drop all registered hooks. Lets a process that tears one switch down
  // and brings another up start from a clean registry, and lets tests reset
  // the process-global state between cases.
  static void clear();
};

} // namespace facebook::fboss
