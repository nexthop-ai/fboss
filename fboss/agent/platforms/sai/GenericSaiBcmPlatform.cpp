/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/sai/GenericSaiBcmPlatform.h"

#include "fboss/agent/FbossError.h"
#include "fboss/agent/hw/switch_asics/HwAsic.h"
#include "fboss/agent/platforms/common/PlatformMapping.h"
#include "fboss/agent/platforms/common/blackwolf800banw/Blackwolf800banwPlatformMapping.h"
#include "fboss/agent/platforms/common/icecube800banw/Icecube800banwPlatformMapping.h"
#include "fboss/agent/platforms/common/icecube800bc/Icecube800bcPlatformMapping.h"
#include "fboss/agent/platforms/common/icetea800bc/Icetea800bcPlatformMapping.h"
#include "fboss/agent/platforms/common/j4sim/J4SimPlatformMapping.h"
#include "fboss/agent/platforms/common/janga800bic/Janga800bicPlatformMapping.h"
#include "fboss/agent/platforms/common/ladakh800bcls/Ladakh800bclsPlatformMapping.h"
#include "fboss/agent/platforms/common/leh800bcls/Leh800bclsPlatformMapping.h"
#include "fboss/agent/platforms/common/m4062nhp/M4062nhpPlatformMapping.h"
#include "fboss/agent/platforms/common/meru800bfa/Meru800bfaP1PlatformMapping.h"
#include "fboss/agent/platforms/common/meru800bfa/Meru800bfaPlatformMapping.h"
#include "fboss/agent/platforms/common/meru800bia/Meru800biaPlatformMapping.h"
#include "fboss/agent/platforms/common/minipack3bta/Minipack3BTAPlatformMapping.h"
#include "fboss/agent/platforms/common/montblanc/MontblancPlatformMapping.h"
#include "fboss/agent/platforms/common/saintpaul/SaintpaulPlatformMapping.h"
#include "fboss/agent/platforms/common/tahan800bc/Tahan800bcPlatformMapping.h"
#include "fboss/agent/platforms/common/tahansb800bc/Tahansb800bcPlatformMapping.h"
#include "fboss/lib/platforms/PlatformDescriptor.h"

#include "thrift/lib/cpp/util/EnumUtils.h"

namespace facebook::fboss {
namespace {

std::unique_ptr<PlatformMapping> createGenericSaiBcmPlatformMapping(
    PlatformType type,
    const std::string& platformMappingStr) {
  if (!platformMappingStr.empty()) {
    return std::make_unique<PlatformMapping>(platformMappingStr);
  }
  if (!FLAGS_platform_descriptor_config_path.empty()) {
    throw FbossError(
        "Generic SAI platform descriptor is missing platform mapping");
  }

  switch (type) {
    case PlatformType::PLATFORM_BLACKWOLF800BANW:
      return std::make_unique<Blackwolf800banwPlatformMapping>();
    case PlatformType::PLATFORM_ICECUBE800BC:
      return std::make_unique<Icecube800bcPlatformMapping>();
    case PlatformType::PLATFORM_ICECUBE800BANW:
      return std::make_unique<Icecube800banwPlatformMapping>();
    case PlatformType::PLATFORM_ICETEA800BC:
      return std::make_unique<Icetea800bcPlatformMapping>();
    case PlatformType::PLATFORM_J4SIM:
      return std::make_unique<J4SimPlatformMapping>();
    case PlatformType::PLATFORM_JANGA800BIC:
      return std::make_unique<Janga800bicPlatformMapping>();
    case PlatformType::PLATFORM_LADAKH800BCLS:
      return std::make_unique<Ladakh800bclsPlatformMapping>();
    case PlatformType::PLATFORM_LEH800BCLS:
      return std::make_unique<Leh800bclsPlatformMapping>();
    case PlatformType::PLATFORM_M4062NHP:
      return std::make_unique<M4062nhpPlatformMapping>();
    case PlatformType::PLATFORM_MERU800BIA:
    case PlatformType::PLATFORM_MERU800BIAB:
    case PlatformType::PLATFORM_MERU800BIAC:
      return std::make_unique<Meru800biaPlatformMapping>();
    case PlatformType::PLATFORM_MERU800BFA:
      return std::make_unique<Meru800bfaPlatformMapping>();
    case PlatformType::PLATFORM_MERU800BFA_P1:
      return std::make_unique<Meru800bfaP1PlatformMapping>();
    case PlatformType::PLATFORM_MINIPACK3BTA:
      return std::make_unique<Minipack3BTAPlatformMapping>();
    case PlatformType::PLATFORM_MONTBLANC:
      return std::make_unique<MontblancPlatformMapping>();
    case PlatformType::PLATFORM_SAINTPAUL:
      return std::make_unique<SaintpaulPlatformMapping>();
    case PlatformType::PLATFORM_TAHAN800BC:
      return std::make_unique<Tahan800bcPlatformMapping>();
    case PlatformType::PLATFORM_TAHANSB800BC:
      return std::make_unique<Tahansb800bcPlatformMapping>();
    default:
      throw FbossError(
          "Generic BCM SAI platform is missing platform mapping for platform type ",
          apache::thrift::util::enumNameSafe(type));
  }
}

} // namespace

bool useGenericSaiBcmPlatform(PlatformType type) {
  return type == PlatformType::PLATFORM_BLACKWOLF800BANW ||
      type == PlatformType::PLATFORM_J4SIM ||
      type == PlatformType::PLATFORM_JANGA800BIC ||
      type == PlatformType::PLATFORM_MERU800BIA ||
      type == PlatformType::PLATFORM_MERU800BIAB ||
      type == PlatformType::PLATFORM_MERU800BIAC ||
      type == PlatformType::PLATFORM_MERU800BFA ||
      type == PlatformType::PLATFORM_MERU800BFA_P1 ||
      type == PlatformType::PLATFORM_SAINTPAUL ||
      type == PlatformType::PLATFORM_WEDGE800BACT ||
      type == PlatformType::PLATFORM_WEDGE800BNHP ||
      type == PlatformType::PLATFORM_ICECUBE800BC ||
      type == PlatformType::PLATFORM_ICECUBE800BANW ||
      type == PlatformType::PLATFORM_ICETEA800BC ||
      type == PlatformType::PLATFORM_LADAKH800BCLS ||
      type == PlatformType::PLATFORM_LEH800BCLS ||
      type == PlatformType::PLATFORM_M4062NHP ||
      type == PlatformType::PLATFORM_MINIPACK3BTA ||
      type == PlatformType::PLATFORM_MONTBLANC ||
      type == PlatformType::PLATFORM_NH4010F ||
      type == PlatformType::PLATFORM_TAHAN800BC ||
      type == PlatformType::PLATFORM_TAHANSB800BC;
}

std::unique_ptr<SaiPlatform> createGenericSaiBcmPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr) {
  const auto platformType = productInfo->getType();
  return std::make_unique<GenericSaiBcmPlatform>(
      std::move(productInfo),
      createGenericSaiBcmPlatformMapping(platformType, platformMappingStr),
      localMac);
}

GenericSaiBcmPlatform::GenericSaiBcmPlatform(
    std::unique_ptr<PlatformProductInfo> productInfo,
    std::unique_ptr<PlatformMapping> platformMapping,
    folly::MacAddress localMac)
    : SaiBcmPlatform(
          std::move(productInfo),
          std::move(platformMapping),
          localMac) {}

GenericSaiBcmPlatform::~GenericSaiBcmPlatform() = default;

void GenericSaiBcmPlatform::setupAsic(
    std::optional<int64_t> switchId,
    const cfg::SwitchInfo& switchInfo,
    std::optional<HwAsic::FabricNodeRole> fabricNodeRole) {
  asic_ = HwAsic::makeAsic(
      switchId.value_or(0), switchInfo, std::nullopt, fabricNodeRole);
}

HwAsic* GenericSaiBcmPlatform::getAsic() const {
  return asic_.get();
}

std::vector<FlexPortMode> GenericSaiBcmPlatform::getSupportedFlexPortModes()
    const {
  return {};
}

bool GenericSaiBcmPlatform::supportInterfaceType() const {
  return true;
}

} // namespace facebook::fboss
