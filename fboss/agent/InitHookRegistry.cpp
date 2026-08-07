/*
 *  Copyright (c) 2026-present, Nexthop Systems Inc
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 */
#include "fboss/agent/InitHookRegistry.h"

#include <folly/logging/xlog.h>

#include <exception>
#include <mutex>
#include <vector>

namespace facebook::fboss {

namespace {

struct State {
  std::mutex mu;
  std::vector<PreSaiInitHook> preSaiInit;
  std::vector<PostConfigAppliedHook> postConfigApplied;
};

State& state() {
  static State s;
  return s;
}

} // namespace

void InitHookRegistry::registerHook(PreSaiInitHook hook) {
  auto& s = state();
  std::lock_guard<std::mutex> g(s.mu);
  s.preSaiInit.push_back(std::move(hook));
}

void InitHookRegistry::registerHook(PostConfigAppliedHook hook) {
  auto& s = state();
  std::lock_guard<std::mutex> g(s.mu);
  s.postConfigApplied.push_back(std::move(hook));
}

void InitHookRegistry::clear() {
  auto& s = state();
  std::lock_guard<std::mutex> g(s.mu);
  s.preSaiInit.clear();
  s.postConfigApplied.clear();
}

void InitHookRegistry::runPreSaiInitHooks() {
  // Snapshot under lock so hooks can register more hooks without deadlocking.
  std::vector<PreSaiInitHook> hooks;
  {
    auto& s = state();
    std::lock_guard<std::mutex> g(s.mu);
    hooks = s.preSaiInit;
  }
  XLOG(INFO) << "InitHookRegistry: running " << hooks.size()
             << " PreSaiInit hooks";
  // Contract: init hooks must not throw. A hook that throws leaves the agent
  // partially initialized (some hooks run, others not, SAI not yet up), so we
  // fail hard with the offending index rather than swallow or unwind.
  for (size_t i = 0; i < hooks.size(); ++i) {
    try {
      hooks[i]();
    } catch (const std::exception& e) {
      XLOG(FATAL) << "InitHookRegistry: PreSaiInit hook #" << i
                  << " threw: " << e.what();
    } catch (...) {
      XLOG(FATAL) << "InitHookRegistry: PreSaiInit hook #" << i
                  << " threw a non-std::exception";
    }
  }
}

void InitHookRegistry::runPostConfigAppliedHooks(SwSwitch* sw) {
  std::vector<PostConfigAppliedHook> hooks;
  {
    auto& s = state();
    std::lock_guard<std::mutex> g(s.mu);
    hooks = s.postConfigApplied;
  }
  XLOG(INFO) << "InitHookRegistry: running " << hooks.size()
             << " PostConfigApplied hooks";
  // See runPreSaiInitHooks: hooks must not throw; a throw is fatal.
  for (size_t i = 0; i < hooks.size(); ++i) {
    try {
      hooks[i](sw);
    } catch (const std::exception& e) {
      XLOG(FATAL) << "InitHookRegistry: PostConfigApplied hook #" << i
                  << " threw: " << e.what();
    } catch (...) {
      XLOG(FATAL) << "InitHookRegistry: PostConfigApplied hook #" << i
                  << " threw a non-std::exception";
    }
  }
}

} // namespace facebook::fboss
