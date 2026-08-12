/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */
#pragma once

#include "fboss/agent/platforms/sai/SaiBcmPlatform.h"

namespace facebook::fboss {

class GenericSaiBcmPlatform : public SaiBcmPlatform {
 public:
  GenericSaiBcmPlatform(
      std::unique_ptr<PlatformProductInfo> productInfo,
      std::unique_ptr<PlatformMapping> platformMapping,
      folly::MacAddress localMac);
  ~GenericSaiBcmPlatform() override;

  HwAsic* getAsic() const override;
  std::vector<FlexPortMode> getSupportedFlexPortModes() const override;
  bool supportInterfaceType() const override;
  void initLEDs() override {}

 private:
  void setupAsic(
      std::optional<int64_t> switchId,
      const cfg::SwitchInfo& switchInfo,
      std::optional<HwAsic::FabricNodeRole> fabricNodeRole) override;

  std::unique_ptr<HwAsic> asic_;
};

// Platform types served by GenericSaiBcmPlatform, i.e. boxes that need no
// platform-specific subclass and are fully described by their platform mapping.
bool useGenericSaiBcmPlatform(PlatformType type);

// Builds a GenericSaiBcmPlatform for `type`, resolving the platform mapping
// from `platformMappingStr` when non-empty and from the built-in per-platform
// mapping otherwise. Throws FbossError if `type` is not one of the types
// useGenericSaiBcmPlatform() accepts.
//
// Declared here rather than kept private to SaiPlatformInitBcm.cpp because
// chooseSaiPlatformImpl() has one definition per SAI implementation (see
// SaiPlatformInitImpl.h) and more than one of them needs these platforms:
// the bcm build serves them on real hardware, and the fake build serves them
// to fboss-sim. Sharing one definition keeps the platform-mapping selection
// from being restated per SAI implementation.
std::unique_ptr<SaiPlatform> createGenericSaiBcmPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr);

} // namespace facebook::fboss
