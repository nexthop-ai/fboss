/*
 *  Copyright (c) 2004-present, Meta Platforms, Inc. and affiliates.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/platform/platform_checks/checks/KernelVersionCheck.h"

#include <sys/utsname.h>

#include <folly/logging/xlog.h>

#ifndef IS_OSS
#include "common/config/ConfigeratorConfig.h"
#include "configerator/structs/fboss/fboss_platform/gen-cpp2/kernel_versions_types.h"
#endif

namespace facebook::fboss::platform::platform_checks {

CheckResult KernelVersionCheck::run() {
  auto supportedKernelVersions = getSupportedKernelVersions();
  if (!supportedKernelVersions) {
    return makeError("Failed to get supported kernel versions");
  }

  struct utsname unameData{};
  if (uname(&unameData) != 0) {
    return makeError("Failed to get kernel version information");
  }
  std::string kernelRelease(unameData.release);

  if (std::find(
          supportedKernelVersions->begin(),
          supportedKernelVersions->end(),
          kernelRelease) != supportedKernelVersions->end()) {
    return makeOK();
  }

  std::string errorMsg =
      "Kernel version " + kernelRelease + " is not supported";
  std::string remediationMsg = "Reprovision to install correct kernel";
  return makeProblem(
      errorMsg, RemediationType::REPROVISION_REQUIRED, remediationMsg);
}

std::optional<std::vector<std::string>>
KernelVersionCheck::getSupportedKernelVersions() {
#ifndef IS_OSS
  config::ConfigeratorConfig<::fboss::platform::KernelVersionsConfig> cfg(
      "fboss/fboss_platform/kernel_versions");
  auto cfgPtr = cfg.get();
  if (!cfgPtr) {
    return std::nullopt;
  }
  return *cfgPtr->kernel_versions();
#else
  // Distro supports 6.4.3 and 6.11.1
  return std::optional<std::vector<std::string>>(
      {"6.4.3-1.fboss.el9.x86_64", "6.11.1-1.fboss.el9.x86_64"});
#endif
}

} // namespace facebook::fboss::platform::platform_checks
