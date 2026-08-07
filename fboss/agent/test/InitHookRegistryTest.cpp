/*
 *  Copyright (c) 2026-present, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#include "fboss/agent/InitHookRegistry.h"

#include <gtest/gtest.h>

#include <vector>

using namespace facebook::fboss;

// InitHookRegistry keeps process-global state, so this test bundles its
// assertions into a single test to stay deterministic regardless of gtest run
// order. Covers: empty-registry no-op, hooks run in registration order exactly
// once per call, and isolation between the two hook points (the callback
// signature selects the point).
TEST(InitHookRegistryTest, dispatch) {
  // Empty-registry no-op: running before anything is registered must not crash
  // and must invoke nothing.
  InitHookRegistry::runPreSaiInitHooks();
  InitHookRegistry::runPostConfigAppliedHooks(nullptr);

  std::vector<int> preOrder;
  std::vector<int> postOrder;

  // The callback signature selects the hook point: a no-argument callback is a
  // PreSaiInit hook, a SwSwitch* callback is a PostConfigApplied hook.
  InitHookRegistry::registerHook([&]() { preOrder.push_back(1); });
  InitHookRegistry::registerHook([&]() { preOrder.push_back(2); });
  InitHookRegistry::registerHook([&](SwSwitch*) { postOrder.push_back(1); });

  // PreSaiInit fires only the PreSaiInit hooks, in registration order.
  InitHookRegistry::runPreSaiInitHooks();
  EXPECT_EQ(preOrder, (std::vector<int>{1, 2}));

  // Exactly once per call: a second run fires each again (appended in order).
  InitHookRegistry::runPreSaiInitHooks();
  EXPECT_EQ(preOrder, (std::vector<int>{1, 2, 1, 2}));

  // PostConfigApplied fires only its own hook; the two runners are isolated.
  InitHookRegistry::runPostConfigAppliedHooks(nullptr);
  EXPECT_EQ(postOrder, (std::vector<int>{1}));
}

// clear() drops every registered hook so a subsequent run fires nothing.
TEST(InitHookRegistryTest, clear) {
  InitHookRegistry::clear();
  int ran = 0;
  InitHookRegistry::registerHook([&]() { ++ran; });
  InitHookRegistry::registerHook([&](SwSwitch*) { ++ran; });
  InitHookRegistry::clear();
  InitHookRegistry::runPreSaiInitHooks();
  InitHookRegistry::runPostConfigAppliedHooks(nullptr);
  EXPECT_EQ(ran, 0);
}
