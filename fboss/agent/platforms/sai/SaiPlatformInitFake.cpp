/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/SaiPlatformInitImpl.h"

#include "fboss/agent/platforms/sai/GenericSaiBcmPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiFakePlatform.h"
#include "fboss/agent/platforms/sai/SaiFakePlatformPort.h"

namespace facebook::fboss {

// Fake SAI build. Serves two callers:
//
//  - fake platform tests, which report PLATFORM_FAKE_SAI (via a FAKE_SAI fruid
//    Product Name or --mode=fake_sai) and get SaiFakePlatform;
//
//  - fboss-sim (fboss-sim/, exercised by .github/workflows/fake-cli-sim.yml),
//    a container that runs the split sw/hw agents with no switching silicon.
//    It links the fake SAI implementation but reports a real platform in
//    fboss-sim/docker/runtime/fruid.json ("Product Name": "MONTBLANC"), so
//    that its agent config and CLI output use that platform's real port
//    layout. Such a platform needs no vendor SDK at init: the generic BCM
//    platform is driven entirely by its platform mapping, and the SAI calls
//    underneath it land in the fake implementation.
//
// Without the generic BCM branches below, chooseSaiPlatformImpl() returns
// nullptr for MONTBLANC, chooseSaiPlatform() throws "Unsupported SAI platform
// type", and fboss_hw_agent aborts before it can register with fboss_sw_agent.
std::unique_ptr<SaiPlatform> chooseSaiPlatformImpl(
    std::unique_ptr<PlatformProductInfo>& productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr) {
  const auto type = productInfo->getType();
  if (type == PlatformType::PLATFORM_FAKE_SAI) {
    return std::make_unique<SaiFakePlatform>(std::move(productInfo));
  }
  if (useGenericSaiBcmPlatform(type)) {
    return createGenericSaiBcmPlatform(
        std::move(productInfo), localMac, platformMappingStr);
  }
  return nullptr;
}

std::unique_ptr<SaiPlatformPort> createSaiPlatformPort(
    const PortID& portId,
    SaiPlatform* platform) {
  const auto type = platform->getType();
  if (type == PlatformType::PLATFORM_FAKE_SAI ||
      type == PlatformType::PLATFORM_FAKE_WEDGE) {
    return std::make_unique<SaiFakePlatformPort>(portId, platform);
  }
  // Matches the port type the bcm build uses for these platforms, so a
  // simulated box presents the same ports as the real one.
  if (useGenericSaiBcmPlatform(type)) {
    return std::make_unique<SaiBcmPlatformPort>(portId, platform);
  }
  return nullptr;
}

} // namespace facebook::fboss
