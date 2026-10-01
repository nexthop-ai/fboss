/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/cli/fboss2/commands/config/interface/InterfaceAttrArgsBase.h"

#include <fmt/format.h>
#include <folly/String.h>

namespace facebook::fboss {

void InterfaceAttrArgsBase::resolveInterfaces(
    const std::vector<std::string>& names,
    bool allowMissing) {
  try {
    interfaces_ = utils::InterfaceList(names, allowMissing);
  } catch (const std::invalid_argument&) {
    std::vector<std::string> failed;
    for (const utils::Intf& intf :
         utils::InterfaceList(names, /*allowMissing=*/true)) {
      if (!intf.isValid()) {
        failed.push_back(intf.name());
      }
    }
    throw std::invalid_argument(
        fmt::format(
            "Neither a configured interface nor a valid {}: {}. "
            "Valid attributes are: {}",
            spec_.attrKind,
            folly::join(", ", failed),
            spec_.validAttrs));
  }
}

} // namespace facebook::fboss
