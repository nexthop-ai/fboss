// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#pragma once

#include <map>
#include <optional>
#include <string>

namespace folly {
struct dynamic;
}

namespace facebook::fboss::cfboss {

/**
 * Maps SAI port "first lane" -> kernel veth name (fboss_p<N>).
 * Loaded from /etc/fboss/cfboss/port_map.json by default. Naming convention
 * is enforced: veth names must match "fboss_p<positive-int>".
 */
class PortMap {
 public:
  static constexpr const char* kDefaultPath = "/etc/fboss/cfboss/port_map.json";
  static constexpr const char* kVethPrefix = "fboss_p";

  // Throws std::runtime_error on read/parse/validation failure.
  static PortMap loadFromFile(const std::string& path = kDefaultPath);

  // Parse from an already-loaded dynamic. Throws on validation failure.
  static PortMap parse(const folly::dynamic& cfg);

  // Lookup by first-lane.
  std::optional<std::string> vethForLane(uint32_t lane) const;

  const std::map<uint32_t, std::string>& laneToVeth() const {
    return laneToVeth_;
  }

 private:
  std::map<uint32_t, std::string> laneToVeth_;
  std::map<std::string, uint32_t> vethToLane_;
};

} // namespace facebook::fboss::cfboss
