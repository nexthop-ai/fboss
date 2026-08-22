// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/PortMap.h"

#include <folly/json.h>

#include <gtest/gtest.h>

#include <stdexcept>

using namespace facebook::fboss::cfboss;

namespace {
PortMap parseStr(const std::string& json) {
  return PortMap::parse(folly::parseJson(json));
}
} // namespace

TEST(PortMapTest, validParse) {
  auto pm = parseStr(
      R"({"ports":[{"lane":0,"veth":"fboss_p1"},{"lane":4,"veth":"fboss_p2"}]})");
  EXPECT_EQ(pm.laneToVeth().size(), 2);
  ASSERT_TRUE(pm.vethForLane(0).has_value());
  EXPECT_EQ(pm.vethForLane(0).value(), "fboss_p1");
  ASSERT_TRUE(pm.vethForLane(4).has_value());
  EXPECT_EQ(pm.vethForLane(4).value(), "fboss_p2");
  EXPECT_FALSE(pm.vethForLane(8).has_value());
}

TEST(PortMapTest, missingPorts) {
  EXPECT_THROW(parseStr(R"({"notports":[]})"), std::runtime_error);
}

TEST(PortMapTest, portsNotArray) {
  EXPECT_THROW(
      parseStr(R"({"ports":{"lane":0,"veth":"fboss_p1"}})"),
      std::runtime_error);
}

TEST(PortMapTest, laneNotInteger) {
  EXPECT_THROW(
      parseStr(R"({"ports":[{"lane":"zero","veth":"fboss_p1"}]})"),
      std::runtime_error);
}

TEST(PortMapTest, vethNotString) {
  EXPECT_THROW(
      parseStr(R"({"ports":[{"lane":0,"veth":5}]})"), std::runtime_error);
}

TEST(PortMapTest, vethBadPattern) {
  EXPECT_THROW(
      parseStr(R"({"ports":[{"lane":0,"veth":"eth0"}]})"), std::runtime_error);
  // fboss_p0 fails the required [1-9] first digit.
  EXPECT_THROW(
      parseStr(R"({"ports":[{"lane":0,"veth":"fboss_p0"}]})"),
      std::runtime_error);
}

TEST(PortMapTest, vethNameTooLongForPeer) {
  // 11 chars + "_peer" (5) = 16 >= IFNAMSIZ, so it is rejected.
  EXPECT_THROW(
      parseStr(R"({"ports":[{"lane":0,"veth":"fboss_p1000"}]})"),
      std::runtime_error);
}

TEST(PortMapTest, duplicateLane) {
  EXPECT_THROW(
      parseStr(
          R"({"ports":[{"lane":0,"veth":"fboss_p1"},{"lane":0,"veth":"fboss_p2"}]})"),
      std::runtime_error);
}

TEST(PortMapTest, duplicateVeth) {
  EXPECT_THROW(
      parseStr(
          R"({"ports":[{"lane":0,"veth":"fboss_p1"},{"lane":4,"veth":"fboss_p1"}]})"),
      std::runtime_error);
}

#ifdef CFBOSS_PORT_MAP_JSON
TEST(PortMapTest, parseShippedPortMap) {
  auto pm = PortMap::loadFromFile(CFBOSS_PORT_MAP_JSON);
  EXPECT_GT(pm.laneToVeth().size(), 0u);
}
#endif
