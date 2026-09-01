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
#include "fboss/agent/platforms/sai/SaiBcmDarwinPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmDarwinPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmElbertPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmElbertPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmFujiPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmFujiPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmMinipackPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmMinipackPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmWedge100Platform.h"
#include "fboss/agent/platforms/sai/SaiBcmWedge100PlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmWedge400Platform.h"
#include "fboss/agent/platforms/sai/SaiBcmWedge400PlatformPort.h"
#include "fboss/agent/platforms/sai/SaiBcmYampPlatform.h"
#include "fboss/agent/platforms/sai/SaiBcmYampPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiElbert8DDPhyPlatformPort.h"
#include "fboss/agent/platforms/sai/SaiNh5010fPlatform.h"
#include "fboss/agent/platforms/sai/SaiNh5010fPlatformPort.h"

namespace facebook::fboss {
<<<<<<< HEAD
||||||| 4c0febe655
namespace {

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
      type == PlatformType::PLATFORM_MINIPACK3BTA ||
      type == PlatformType::PLATFORM_MONTBLANC ||
      type == PlatformType::PLATFORM_TAHAN800BC ||
      type == PlatformType::PLATFORM_TAHANSB800BC;
}

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
=======
namespace {

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
      type == PlatformType::PLATFORM_MINIPACK3BTA ||
      type == PlatformType::PLATFORM_MONTBLANC ||
      type == PlatformType::PLATFORM_TAHAN800BC ||
      type == PlatformType::PLATFORM_TAHANSB800BC ||
      type == PlatformType::PLATFORM_M4061CLSC;
}

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
>>>>>>> be11fad19cf8da3f8dbcc1318a6109b7c9b96dbe

std::unique_ptr<SaiPlatform> chooseSaiPlatformImpl(
    std::unique_ptr<PlatformProductInfo>& productInfo,
    folly::MacAddress localMac,
    const std::string& platformMappingStr) {
  const auto type = productInfo->getType();
  if (type == PlatformType::PLATFORM_WEDGE100) {
    return std::make_unique<SaiBcmWedge100Platform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_WEDGE400 ||
      type == PlatformType::PLATFORM_WEDGE400_GRANDTETON) {
    return std::make_unique<SaiBcmWedge400Platform>(
        std::move(productInfo), type, localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_DARWIN ||
      type == PlatformType::PLATFORM_DARWIN48V) {
    return std::make_unique<SaiBcmDarwinPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_MINIPACK) {
    return std::make_unique<SaiBcmMinipackPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_YAMP) {
    return std::make_unique<SaiBcmYampPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_FUJI) {
    return std::make_unique<SaiBcmFujiPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_ELBERT) {
    return std::make_unique<SaiBcmElbertPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
  }
  if (type == PlatformType::PLATFORM_NH5010F) {
    return std::make_unique<SaiNh5010fPlatform>(
        std::move(productInfo), localMac, platformMappingStr);
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
  const auto platformMode = platform->getType();
  if (platformMode == PlatformType::PLATFORM_WEDGE100) {
    return std::make_unique<SaiBcmWedge100PlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_WEDGE400 ||
      platformMode == PlatformType::PLATFORM_WEDGE400_GRANDTETON) {
    return std::make_unique<SaiBcmWedge400PlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_DARWIN ||
      platformMode == PlatformType::PLATFORM_DARWIN48V) {
    return std::make_unique<SaiBcmDarwinPlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_MINIPACK) {
    return std::make_unique<SaiBcmMinipackPlatformPort>(portId, platform);
  }
  if (useGenericSaiBcmPlatform(platformMode)) {
    return std::make_unique<SaiBcmPlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_YAMP) {
    return std::make_unique<SaiBcmYampPlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_FUJI) {
    return std::make_unique<SaiBcmFujiPlatformPort>(portId, platform);
  }
  if (platformMode == PlatformType::PLATFORM_ELBERT) {
    if (platform->getAsic()->getAsicType() ==
        cfg::AsicType::ASIC_TYPE_ELBERT_8DD) {
      return std::make_unique<SaiElbert8DDPhyPlatformPort>(portId, platform);
    }
    if (platform->getAsic()->getAsicType() ==
        cfg::AsicType::ASIC_TYPE_TOMAHAWK4) {
      return std::make_unique<SaiBcmElbertPlatformPort>(portId, platform);
    }
  }
  if (platformMode == PlatformType::PLATFORM_NH5010F) {
    return std::make_unique<SaiNh5010fPlatformPort>(portId, platform);
  }
  return nullptr;
}

} // namespace facebook::fboss
