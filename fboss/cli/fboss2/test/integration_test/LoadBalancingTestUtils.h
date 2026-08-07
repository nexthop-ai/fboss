// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

// Reverse mappings from LoadBalancer Thrift enum values (as they appear in
// the running-config JSON) to the token spellings the `config load-balancing`
// CLI accepts. Shared by ConfigLoadBalancingTest and DeleteLoadBalancingTest
// so the token vocabulary lives in one place.

#pragma once

#include <fmt/format.h>
#include <stdexcept>
#include <string>

namespace facebook::fboss {

inline std::string algorithmIntToToken(int enumValue) {
  switch (enumValue) {
    case 1:
      return "crc16-ccitt";
    case 3:
      return "crc32-lo";
    case 4:
      return "crc32-hi";
    case 5:
      return "crc32-ethernet-lo";
    case 6:
      return "crc32-ethernet-hi";
    case 7:
      return "crc32-koopman-lo";
    case 8:
      return "crc32-koopman-hi";
    case 9:
      return "crc";
    default:
      throw std::runtime_error(
          fmt::format("Unknown HashingAlgorithm enum value {}", enumValue));
  }
}

// fieldKey is the fieldSelection JSON key: "ipv4Fields", "ipv6Fields",
// "transportFields", or "mplsFields".
inline std::string fieldIntToToken(const std::string& fieldKey, int enumValue) {
  if (fieldKey == "ipv4Fields" || fieldKey == "ipv6Fields") {
    switch (enumValue) {
      case 1:
        return "src-ip";
      case 2:
        return "dst-ip";
      case 3:
        return "flow-label";
    }
  } else if (fieldKey == "transportFields") {
    switch (enumValue) {
      case 1:
        return "src-port";
      case 2:
        return "dst-port";
    }
  } else if (fieldKey == "mplsFields") {
    switch (enumValue) {
      case 1:
        return "top";
      case 2:
        return "second";
      case 3:
        return "third";
    }
  }
  throw std::runtime_error(
      fmt::format("Unknown {} enum value {}", fieldKey, enumValue));
}

} // namespace facebook::fboss
