// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "fboss/cli/fboss2/commands/config/json_patch/CmdConfigJsonPatch.h"

#include "fboss/cli/fboss2/CmdHandler.cpp"

#include <fmt/format.h>
#include <folly/FileUtil.h>
#include <folly/json/dynamic.h>
#include <folly/json/json.h>
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include <algorithm>
#include <array>
#include <cstddef>
#include <exception>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "fboss/cli/fboss2/utils/PortMap.h"

namespace facebook::fboss {

namespace {

constexpr std::string_view kAgentService = "agent";
constexpr std::string_view kUsage =
    "Expected: agent <patch-file> [hitless|warmboot|coldboot]";

struct LevelName {
  std::string_view name;
  cli::ConfigActionLevel level;
};
constexpr auto kLevels = std::to_array<LevelName>({
    {"hitless", cli::ConfigActionLevel::HITLESS},
    {"warmboot", cli::ConfigActionLevel::SERVICE_RESTART},
    {"coldboot", cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART},
});
constexpr std::string_view kDefaultLevelName = "coldboot";

cli::ConfigActionLevel parseLevel(const std::string& name) {
  for (const auto& entry : kLevels) {
    if (entry.name == name) {
      return entry.level;
    }
  }
  throw std::invalid_argument(
      fmt::format(
          "Invalid apply level '{}'. Expected hitless, warmboot or coldboot",
          name));
}

folly::dynamic readPatch(const std::string& path) {
  std::string text;
  if (!folly::readFile(path.c_str(), text)) {
    throw std::runtime_error(
        fmt::format("Failed to read patch file '{}'", path));
  }
  folly::dynamic patch;
  try {
    patch = folly::parseJson(text);
  } catch (const std::exception& ex) {
    throw std::runtime_error(
        fmt::format("Patch file '{}' is not valid JSON: {}", path, ex.what()));
  }
  // A non-object merge patch replaces the whole document. That is never what
  // a caller wants for a service config, so refuse it.
  if (!patch.isObject()) {
    throw std::runtime_error(
        fmt::format("Patch file '{}' must contain a JSON object", path));
  }
  return patch;
}

folly::dynamic toDynamic(const cfg::AgentConfig& config) {
  return folly::parseJson(
      apache::thrift::SimpleJSONSerializer::serialize<std::string>(config));
}

// A value of the patch that the typed config does not hold as the patch says.
struct PatchMismatch {
  // Where in the patch, e.g. "sw.ports[3].maxFrameSize".
  std::string path;
  // The patch deletes (sets to null) a field the typed config always holds,
  // i.e. a non-optional one. The deletion would silently reset the field to
  // its default (e.g. "sw.ports": null leaves no ports at all).
  bool deletesRequiredField{false};
};

bool isScalar(const folly::dynamic& value) {
  return !value.isObject() && !value.isArray();
}

bool isScalarArray(const folly::dynamic& array) {
  return std::all_of(array.begin(), array.end(), isScalar);
}

// Same elements with the same multiplicity, in any order.
bool sameScalarsIgnoringOrder(
    const folly::dynamic& expected,
    const folly::dynamic& actual) {
  std::vector<bool> used(actual.size(), false);
  for (const auto& want : expected) {
    bool found = false;
    for (std::size_t i = 0; i < actual.size(); ++i) {
      if (!used[i] && (actual[i] == want)) {
        used[i] = true;
        found = true;
        break;
      }
    }
    if (!found) {
      return false;
    }
  }
  return true;
}

// Checks that everything `expected` (the patch, or a part of it) says is in
// `actual`, the patched config after a round trip through cfg::AgentConfig.
// That round trip drops members the schema does not know and adds defaults,
// so:
//   - an object of the patch must be contained in the result's object;
//   - a null member (a deletion) must be absent from the result. Thrift
//     always serializes non-optional fields, so one that is still there
//     cannot be deleted, only reset to its default;
//   - arrays must have the same length. Arrays of scalars compare ignoring
//     order (a set<> field re-serializes in its own order); other arrays
//     compare element by element with the rules above.
// Returns the first mismatch, or nullopt if the whole patch is there.
std::optional<PatchMismatch> findPatchMismatch(
    const folly::dynamic& expected,
    const folly::dynamic& actual,
    const std::string& path = "") {
  if (expected.isObject()) {
    if (!actual.isObject()) {
      return PatchMismatch{path};
    }
    for (const auto& [key, value] : expected.items()) {
      auto childPath = path.empty()
          ? key.asString()
          : fmt::format("{}.{}", path, key.asString());
      const auto* actualValue = actual.get_ptr(key);
      if (value.isNull()) {
        if (actualValue != nullptr) {
          return PatchMismatch{std::move(childPath), true};
        }
        continue;
      }
      if (actualValue == nullptr) {
        return PatchMismatch{std::move(childPath)};
      }
      if (auto mismatch = findPatchMismatch(value, *actualValue, childPath)) {
        return mismatch;
      }
    }
    return std::nullopt;
  }

  if (expected.isArray()) {
    if (!actual.isArray() || (actual.size() != expected.size())) {
      return PatchMismatch{path};
    }
    if (isScalarArray(expected)) {
      if (isScalarArray(actual) && sameScalarsIgnoringOrder(expected, actual)) {
        return std::nullopt;
      }
      return PatchMismatch{path};
    }
    for (std::size_t i = 0; i < expected.size(); ++i) {
      if (auto mismatch = findPatchMismatch(
              expected[i], actual[i], fmt::format("{}[{}]", path, i))) {
        return mismatch;
      }
    }
    return std::nullopt;
  }

  if (expected == actual) {
    return std::nullopt;
  }
  return PatchMismatch{path};
}

} // namespace

JsonPatchArgs::JsonPatchArgs(std::vector<std::string> v) {
  if ((v.size() < 2) || (v.size() > 3)) {
    throw std::invalid_argument(
        fmt::format("{}, got {} argument(s)", kUsage, v.size()));
  }
  if (v[0] != kAgentService) {
    throw std::invalid_argument(
        fmt::format(
            "Unsupported service '{}'. Only 'agent' is supported", v[0]));
  }
  if (v[1].empty()) {
    throw std::invalid_argument(fmt::format("{}: empty patch file", kUsage));
  }
  levelName_ = (v.size() == 3) ? v[2] : std::string(kDefaultLevelName);
  level_ = parseLevel(levelName_);
  patchFile_ = v[1];
  data_ = std::move(v);
}

CmdConfigJsonPatchTraits::RetType CmdConfigJsonPatch::queryClient(
    const HostInfo& /* hostInfo */,
    const ObjectArgType& args) {
  const auto& patchFile = args.getPatchFile();
  const auto patch = readPatch(patchFile);

  auto& session = ConfigSession::getInstance();
  auto& config = session.getAgentConfig();
  const auto current = toDynamic(config);
  auto merged = current;
  merged.merge_patch(patch);

  // Go through the typed config so that a value of the wrong type is refused
  // here rather than by the agent at its next start.
  cfg::AgentConfig patched;
  try {
    patched =
        apache::thrift::SimpleJSONSerializer::deserialize<cfg::AgentConfig>(
            folly::toJson(merged));
  } catch (const std::exception& ex) {
    throw std::runtime_error(
        fmt::format(
            "Patch file '{}' does not produce a valid agent config: {}",
            patchFile,
            ex.what()));
  }

  // Deserialization silently drops fields the schema does not know and puts
  // back non-optional fields the patch deleted. Refuse the patch if the config
  // that would be staged does not say what the patch says.
  const auto result = toDynamic(patched);
  if (const auto mismatch = findPatchMismatch(patch, result)) {
    if (mismatch->deletesRequiredField) {
      throw std::runtime_error(
          fmt::format(
              "Patch file '{}' deletes '{}', which is not optional in the "
              "agent config: deleting it would reset it to its default. Set "
              "the value you want instead. Nothing was staged",
              patchFile,
              mismatch->path));
    }
    throw std::runtime_error(
        fmt::format(
            "Patch file '{}' sets '{}', which the agent config does not hold "
            "after the patch (unknown field or wrong value type). Nothing was "
            "staged",
            patchFile,
            mismatch->path));
  }

  if (result == current) {
    return fmt::format(
        "Patch file '{}' does not change the agent config. Nothing was staged",
        patchFile);
  }

  // Commands derive their port map from the config, which refuses e.g. a
  // port without a name, so build one here to refuse such a config before it
  // replaces the session's.
  try {
    [[maybe_unused]] const utils::PortMap portMap(patched);
  } catch (const std::exception& ex) {
    throw std::runtime_error(
        fmt::format(
            "Patch file '{}' does not produce a usable agent config: {}",
            patchFile,
            ex.what()));
  }
  config = std::move(patched);
  session.saveConfig(cli::ServiceType::AGENT, args.getLevel());

  return fmt::format(
      "Staged patch file '{}' into the agent config (apply level: {}). "
      "Run 'config session commit' to apply",
      patchFile,
      args.getLevelName());
}

void CmdConfigJsonPatch::printOutput(const RetType& logMsg) {
  std::cout << logMsg << std::endl;
}

// Explicit template instantiation
template void CmdHandler<CmdConfigJsonPatch, CmdConfigJsonPatchTraits>::run();

} // namespace facebook::fboss
