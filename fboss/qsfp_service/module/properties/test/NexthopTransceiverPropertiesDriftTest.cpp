// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
//
// Drift check for the Nexthop transceiver properties override.
//
// fboss/oss/scripts/run_configs/transceiver_properties/nexthop.json5 is loaded
// via --transceiver_properties_config and *replaces* the compiled-in default
// table in TransceiverPropertiesDefault.h. It must therefore carry every
// upstream entry verbatim, plus the Nexthop-only ones. This test fails when
// the two tables drift apart so that a change to the default header is not
// silently dropped from the Nexthop platforms.

#include <folly/FileUtil.h>
#include <folly/json/json.h>
#include <gtest/gtest.h>
#include <thrift/lib/cpp2/folly_dynamic/folly_dynamic.h>

#include <set>

#include "fboss/qsfp_service/if/gen-cpp2/transceiver_properties_types.h"
#include "fboss/qsfp_service/module/properties/TransceiverPropertiesDefault.h"
#include "fboss/qsfp_service/module/properties/TransceiverPropertiesManager.h"

#ifndef FBOSS_SOURCE_DIR
#error "FBOSS_SOURCE_DIR must be defined by the build"
#endif

namespace facebook::fboss {

namespace {

constexpr auto kOverridePath = FBOSS_SOURCE_DIR
    "/fboss/oss/scripts/run_configs/transceiver_properties/nexthop.json5";

// Entries that exist only in nexthop.json5 and not in the compiled-in default.
// Keep in sync with the "Nexthop-only entries" list in the README next to
// nexthop.json5. Anything else that appears in the override but not in the
// default is a drift error.
const std::set<int32_t> kNexthopOnlyCodes = {
    static_cast<int32_t>(MediaInterfaceCode::DR4_800G), // 22
};

TransceiverPropertiesConfig parseConfig(const std::string& json) {
  // Same parsing path as TransceiverPropertiesManager::initFromJson.
  folly::json::serialization_opts opts;
  opts.allow_json5_experimental = true;
  auto dynamic = folly::parseJson(json, opts);
  TransceiverPropertiesConfig config;
  facebook::thrift::from_dynamic(
      config,
      dynamic,
      facebook::thrift::dynamic_format::PORTABLE,
      facebook::thrift::format_adherence::LENIENT);
  return config;
}

// JSON_1 renders enums as integers, so raw enum values that are not in the
// enum (e.g. a mediaLaneCode the SMFMediaInterfaceCode enum does not define
// yet) print fine; PORTABLE would throw on them.
std::string toPrettyJson(const SmfTransceiverProperties& props) {
  return folly::toPrettyJson(
      facebook::thrift::to_dynamic(
          props, facebook::thrift::dynamic_format::JSON_1));
}

std::string readOverride() {
  std::string json;
  if (!folly::readFile(kOverridePath, json)) {
    ADD_FAILURE() << "Failed to read " << kOverridePath;
  }
  return json;
}

} // namespace

TEST(NexthopTransceiverPropertiesDriftTest, OverrideLoadsThroughManager) {
  // The override must be accepted by the real loader, including its
  // validation of firstApplicationAdvertisement fields.
  TransceiverPropertiesManager::reset();
  ASSERT_NO_THROW(TransceiverPropertiesManager::init(kOverridePath));
  EXPECT_TRUE(TransceiverPropertiesManager::isInitialized());
  for (auto code : kNexthopOnlyCodes) {
    EXPECT_TRUE(TransceiverPropertiesManager::isKnown(code))
        << "Nexthop-only code " << code << " missing from nexthop.json5";
  }
  TransceiverPropertiesManager::reset();
}

TEST(NexthopTransceiverPropertiesDriftTest, OverrideMatchesDefault) {
  const auto defaultCfg = parseConfig(kDefaultTransceiverPropertiesJson);
  const auto overrideCfg = parseConfig(readOverride());
  const auto& defaults = *defaultCfg.smfTransceivers();
  const auto& overrides = *overrideCfg.smfTransceivers();

  // Every upstream entry must be present and identical.
  for (const auto& [code, defaultProps] : defaults) {
    auto it = overrides.find(code);
    if (it == overrides.end()) {
      ADD_FAILURE() << "Entry " << code << " (" << *defaultProps.displayName()
                    << ") is in TransceiverPropertiesDefault.h but missing "
                       "from nexthop.json5; re-sync the override";
      continue;
    }
    // EXPECT_TRUE rather than EXPECT_EQ: the struct has no printer, and the
    // raw byte dump gtest would emit is useless next to the JSON below.
    EXPECT_TRUE(it->second == defaultProps)
        << "Entry " << code << " (" << *defaultProps.displayName()
        << ") differs between TransceiverPropertiesDefault.h and nexthop.json5"
        << "\n--- default ---\n"
        << toPrettyJson(defaultProps) << "\n--- nexthop.json5 ---\n"
        << toPrettyJson(it->second);
  }

  // Anything extra must be a documented Nexthop-only entry.
  for (const auto& [code, props] : overrides) {
    if (defaults.contains(code)) {
      continue;
    }
    EXPECT_TRUE(kNexthopOnlyCodes.contains(code))
        << "Entry " << code << " (" << *props.displayName()
        << ") is in nexthop.json5 but neither in "
           "TransceiverPropertiesDefault.h nor listed in kNexthopOnlyCodes";
  }

  // And every documented Nexthop-only entry must still be Nexthop-only. If it
  // has been upstreamed into the default, drop it from the list (and README).
  for (auto code : kNexthopOnlyCodes) {
    EXPECT_TRUE(overrides.contains(code))
        << "kNexthopOnlyCodes lists " << code
        << " but nexthop.json5 has no such entry";
    EXPECT_FALSE(defaults.contains(code))
        << "kNexthopOnlyCodes lists " << code
        << " but it is now in TransceiverPropertiesDefault.h";
  }
}

} // namespace facebook::fboss
