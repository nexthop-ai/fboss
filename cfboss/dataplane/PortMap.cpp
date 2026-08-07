// (c) Nexthop Systems, Inc. and affiliates. Confidential and proprietary.
#include "cfboss/dataplane/PortMap.h"

#include <folly/FileUtil.h>
#include <folly/dynamic.h>
#include <folly/json.h>
#include <folly/logging/xlog.h>

#include <net/if.h>

#include <re2/re2.h>
#include <stdexcept>

namespace facebook::fboss::cfboss {

PortMap PortMap::loadFromFile(const std::string& path) {
  std::string raw;
  if (!folly::readFile(path.c_str(), raw)) {
    throw std::runtime_error(std::string("PortMap: cannot read file: ") + path);
  }
  folly::dynamic cfg;
  try {
    cfg = folly::parseJson(raw);
  } catch (const std::exception& e) {
    throw std::runtime_error(
        std::string("PortMap: JSON parse failed for ") + path + ": " +
        e.what());
  }
  return parse(cfg);
}

PortMap PortMap::parse(const folly::dynamic& cfg) {
  PortMap pm;
  const auto* portsArr = cfg.get_ptr("ports");
  if (!portsArr || !portsArr->isArray()) {
    throw std::runtime_error(
        R"(PortMap: top-level "ports" array missing or not an array)");
  }
  static const re2::RE2 kVethRegex(std::string(kVethPrefix) + "[1-9][0-9]*");
  // The veth bootstrap derives a peer interface named "<veth>_peer"; both the
  // veth and its peer must fit within the kernel interface-name limit
  // (IFNAMSIZ includes the NUL, so the usable name length is IFNAMSIZ - 1).
  static constexpr char kVethPeerSuffix[] = "_peer";
  static constexpr size_t kVethPeerSuffixLen = sizeof(kVethPeerSuffix) - 1;
  for (const auto& entry : *portsArr) {
    const auto* laneItem = entry.get_ptr("lane");
    const auto* vethItem = entry.get_ptr("veth");
    if (!laneItem || !vethItem || !laneItem->isInt() || !vethItem->isString()) {
      throw std::runtime_error(
          R"(PortMap: each ports[] entry must have integer "lane" and string "veth")");
    }
    if (laneItem->asInt() < 0) {
      throw std::runtime_error(
          "PortMap: negative lane " + std::to_string(laneItem->asInt()));
    }
    auto lane = static_cast<uint32_t>(laneItem->asInt());
    auto veth = vethItem->asString();
    if (!re2::RE2::FullMatch(veth, kVethRegex)) {
      throw std::runtime_error(
          "PortMap: veth name does not match required convention "
          "fboss_p<N>: " +
          veth);
    }
    if (veth.size() + kVethPeerSuffixLen >= IFNAMSIZ) {
      throw std::runtime_error(
          "PortMap: veth name too long; \"" + veth + kVethPeerSuffix +
          "\" exceeds IFNAMSIZ (" + std::to_string(IFNAMSIZ) + ")");
    }
    if (pm.laneToVeth_.count(lane)) {
      throw std::runtime_error(
          "PortMap: duplicate lane " + std::to_string(lane));
    }
    if (pm.vethToLane_.count(veth)) {
      throw std::runtime_error("PortMap: duplicate veth " + veth);
    }
    pm.laneToVeth_[lane] = veth;
    pm.vethToLane_[veth] = lane;
  }
  XLOG(INFO) << "PortMap: loaded " << pm.laneToVeth_.size() << " veth ports";
  return pm;
}

std::optional<std::string> PortMap::vethForLane(uint32_t lane) const {
  auto it = laneToVeth_.find(lane);
  if (it == laneToVeth_.end()) {
    return std::nullopt;
  }
  return it->second;
}

} // namespace facebook::fboss::cfboss
