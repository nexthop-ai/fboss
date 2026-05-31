/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/ptp/CmdConfigPtp.h"

<<<<<<< HEAD
#include "fboss/cli/fboss2/CmdHandler.cpp"
||||||| cd4e0b49f5
=======
#include "fboss/cli/fboss2/CmdHandler.cpp" // NOLINT(facebook-unused-include-check)
>>>>>>> fa2cbb1024bde6617e7ebcc238ccc8f618ffc5af

namespace facebook::fboss {

// Explicit template instantiation
template void CmdHandler<CmdConfigPtp, CmdConfigPtpTraits>::run();

} // namespace facebook::fboss
