/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiTajoPlatform.h"

#include <cstdlib>

namespace facebook::fboss {

const std::unordered_map<std::string, std::string>
SaiTajoPlatform::getSaiProfileVendorExtensionValues() const {
  std::unordered_map<std::string, std::string> vendorExtensions;

  // Nexthop internal change: The SDK reads its per-component log levels from
  // this file. BASE_OUTPUT_DIR is exported by sai-runtime's
  // /etc/profile.d/sai-env.sh.
  // NOLINTNEXTLINE(concurrency-mt-unsafe): read once during platform init
  if (const char* basePath = getenv("BASE_OUTPUT_DIR")) {
    vendorExtensions["SAI_SDK_LOG_CONFIG_FILE"] =
        std::string(basePath) + "/res/config/sai_sdk_log_config.json";
  }
  return vendorExtensions;
}

} // namespace facebook::fboss
