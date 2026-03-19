/*
 *  Copyright (c) 2023-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
<<<<<<<< HEAD:fboss/cli/fboss2/commands/config/l2/CmdConfigL2.cpp

#include "fboss/cli/fboss2/commands/config/l2/CmdConfigL2.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

namespace facebook::fboss {

// Explicit template instantiation
template void CmdHandler<CmdConfigL2, CmdConfigL2Traits>::run();

} // namespace facebook::fboss
|||||||| c17655f139:fboss/agent/test/oss/Main.cpp
#include <gtest/gtest.h>
#include "folly/init/Init.h"

int main(int argc, char** argv) {
  testing::InitGoogleTest(&argc, argv);
  const folly::Init init(&argc, &argv);
  return RUN_ALL_TESTS();
}
========
#include "fboss/agent/platforms/sai/SaiYangra2PlatformPort.h"
>>>>>>>> 84406ca706433e04c579c49376acbd3a257dfc4b:fboss/agent/platforms/sai/SaiYangra2PlatformPort.cpp
