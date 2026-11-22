// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <gmock/gmock.h>
#include <gtest/gtest.h>
#include <filesystem>
#include <stdexcept>
#include <string>

#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/cli/fboss2/commands/config/arp/CmdConfigArp.h"
#include "fboss/cli/fboss2/commands/config/json_patch/CmdConfigJsonPatch.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/AgentConfigDomain.h"
#include "fboss/cli/fboss2/session/ConfigSession.h"
#include "fboss/cli/fboss2/test/TestableConfigSession.h"
#include "fboss/cli/fboss2/test/config/CmdConfigTestBase.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"

using namespace ::testing;

namespace facebook::fboss {

class CmdConfigJsonPatchTestFixture : public CmdConfigTestBase {
 public:
  CmdConfigJsonPatchTestFixture()
      : CmdConfigTestBase(
            "fboss_json_patch_test_%%%%-%%%%-%%%%-%%%%",
            R"({
  "sw": {
    "arpTimeoutSeconds": 60,
    "maxNeighborProbes": 500,
    "hostname": "sw1",
    "ports": [
      {
        "logicalID": 1,
        "name": "eth1/1/1",
        "state": 2,
        "speed": 100000,
        "maxFrameSize": 9412,
        "description": "first"
      },
      {
        "logicalID": 2,
        "name": "eth1/2/1",
        "state": 2,
        "speed": 100000,
        "maxFrameSize": 9412
      }
    ]
  }
})") {}

 protected:
  const std::string cmdPrefix_ = "config json-patch";

  // Writes `content` to a patch file and returns its path.
  std::string writePatch(const std::string& content) {
    const auto path = getTestHomeDir() / "patch.json";
    createTestConfig(path, content);
    return path.string();
  }

  // Runs the command against a fresh session on `patchContent`.
  std::string runPatch(
      const std::string& patchContent,
      const std::string& level = "") {
    const auto path = writePatch(patchContent);
    std::vector<std::string> argv = {"agent", path};
    std::string cmdArgs = "agent " + path;
    if (!level.empty()) {
      argv.push_back(level);
      cmdArgs += " " + level;
    }
    setupTestableConfigSession(cmdPrefix_, cmdArgs);
    CmdConfigJsonPatch cmd;
    HostInfo hostInfo("testhost");
    return cmd.queryClient(hostInfo, JsonPatchArgs(argv));
  }

  static const cfg::SwitchConfig& sw() {
    return *ConfigSession::getInstance().config<AgentConfigDomain>().sw();
  }

  static cli::ConfigActionLevel requiredAction() {
    return TestableConfigSession::get().getRequiredAction(
        cli::ServiceType::AGENT);
  }
};

// =============================================================
// JsonPatchArgs validation
// =============================================================

TEST_F(CmdConfigJsonPatchTestFixture, argsDefaultLevelIsColdboot) {
  JsonPatchArgs args({"agent", "/tmp/p.json"});
  EXPECT_EQ(args.getPatchFile(), "/tmp/p.json");
  EXPECT_EQ(
      args.getLevel(), cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);
  EXPECT_EQ(args.getLevelName(), "coldboot");
}

TEST_F(CmdConfigJsonPatchTestFixture, argsExplicitLevels) {
  EXPECT_EQ(
      JsonPatchArgs({"agent", "p", "hitless"}).getLevel(),
      cli::ConfigActionLevel::HITLESS);
  EXPECT_EQ(
      JsonPatchArgs({"agent", "p", "warmboot"}).getLevel(),
      cli::ConfigActionLevel::SERVICE_RESTART);
  EXPECT_EQ(
      JsonPatchArgs({"agent", "p", "coldboot"}).getLevel(),
      cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);
}

TEST_F(CmdConfigJsonPatchTestFixture, argsBadArity) {
  EXPECT_THROW(JsonPatchArgs({}), std::invalid_argument);
  EXPECT_THROW(JsonPatchArgs({"agent"}), std::invalid_argument);
  EXPECT_THROW(
      JsonPatchArgs({"agent", "p", "hitless", "extra"}), std::invalid_argument);
}

TEST_F(CmdConfigJsonPatchTestFixture, argsUnsupportedService) {
  EXPECT_THROW(JsonPatchArgs({"bgp", "p"}), std::invalid_argument);
  EXPECT_THROW(JsonPatchArgs({"Agent", "p"}), std::invalid_argument);
}

TEST_F(CmdConfigJsonPatchTestFixture, argsInvalidLevel) {
  EXPECT_THROW(JsonPatchArgs({"agent", "p", "reboot"}), std::invalid_argument);
  EXPECT_THROW(JsonPatchArgs({"agent", "p", ""}), std::invalid_argument);
}

TEST_F(CmdConfigJsonPatchTestFixture, argsEmptyPatchFile) {
  EXPECT_THROW(JsonPatchArgs({"agent", ""}), std::invalid_argument);
}

// =============================================================
// queryClient(): patches that are staged
// =============================================================

TEST_F(CmdConfigJsonPatchTestFixture, scalarIsSet) {
  const auto result = runPatch(R"({"sw": {"arpTimeoutSeconds": 30}})");
  EXPECT_THAT(result, HasSubstr("Staged"));
  EXPECT_THAT(result, HasSubstr("coldboot"));

  EXPECT_EQ(*sw().arpTimeoutSeconds(), 30);
  // Fields the patch does not mention are kept.
  EXPECT_EQ(*sw().maxNeighborProbes(), 500);
  ASSERT_EQ(sw().ports()->size(), 2);
  EXPECT_EQ(*sw().ports()[0].maxFrameSize(), 9412);
}

TEST_F(CmdConfigJsonPatchTestFixture, stagedConfigIsWrittenToSession) {
  runPatch(R"({"sw": {"arpTimeoutSeconds": 30}})");
  EXPECT_THAT(
      readFile(getSessionConfigPath()), HasSubstr("\"arpTimeoutSeconds\": 30"));
  // The system config is untouched until `config session commit`.
  EXPECT_THAT(
      readFile(getSystemConfigPath()), HasSubstr("\"arpTimeoutSeconds\": 60"));
}

TEST_F(CmdConfigJsonPatchTestFixture, listIsReplacedWhole) {
  runPatch(R"({"sw": {"ports": [
    {"logicalID": 1, "name": "eth1/1/1", "state": 2, "speed": 100000,
     "maxFrameSize": 9000}
  ]}})");
  ASSERT_EQ(sw().ports()->size(), 1);
  EXPECT_EQ(*sw().ports()[0].name(), "eth1/1/1");
  EXPECT_EQ(*sw().ports()[0].maxFrameSize(), 9000);
  // The description was in the old list element and not in the patch.
  EXPECT_FALSE(sw().ports()[0].description().has_value());
}

TEST_F(CmdConfigJsonPatchTestFixture, nullDeletesOptionalField) {
  runPatch(R"({"sw": {"hostname": null}})");
  EXPECT_FALSE(sw().hostname().has_value());
  EXPECT_EQ(*sw().arpTimeoutSeconds(), 60);
}

TEST_F(CmdConfigJsonPatchTestFixture, scalarSetOrderIsIgnored) {
  // ipv6Fields is a set<>: the staged config holds it in the set's own order
  // (1, 2, 3), which is not a mismatch with the patch's order.
  const auto result = runPatch(R"({"sw": {"loadBalancers": [
    {"id": 1, "fieldSelection": {"ipv6Fields": [3, 1, 2]}, "algorithm": 1}
  ]}})");
  EXPECT_THAT(result, HasSubstr("Staged"));
  ASSERT_EQ(sw().loadBalancers()->size(), 1);
  EXPECT_EQ(sw().loadBalancers()[0].fieldSelection()->ipv6Fields()->size(), 3);
}

TEST_F(CmdConfigJsonPatchTestFixture, defaultLevelIsColdboot) {
  runPatch(R"({"sw": {"arpTimeoutSeconds": 30}})");
  EXPECT_EQ(
      requiredAction(), cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);
}

TEST_F(CmdConfigJsonPatchTestFixture, explicitLevelIsRecorded) {
  const auto result =
      runPatch(R"({"sw": {"arpTimeoutSeconds": 30}})", "hitless");
  EXPECT_THAT(result, HasSubstr("hitless"));
  EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::HITLESS);
}

TEST_F(CmdConfigJsonPatchTestFixture, lowerLevelDoesNotLowerSession) {
  runPatch(R"({"sw": {"arpTimeoutSeconds": 30}})", "warmboot");
  EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::SERVICE_RESTART);

  // A second, hitless patch in the same session keeps the higher level.
  const auto path = writePatch(R"({"sw": {"maxNeighborProbes": 100}})");
  CmdConfigJsonPatch cmd;
  HostInfo hostInfo("testhost");
  cmd.queryClient(hostInfo, JsonPatchArgs({"agent", path, "hitless"}));

  EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::SERVICE_RESTART);
  EXPECT_EQ(*sw().arpTimeoutSeconds(), 30);
  EXPECT_EQ(*sw().maxNeighborProbes(), 100);
}

TEST_F(CmdConfigJsonPatchTestFixture, combinesWithOtherConfigCommand) {
  runPatch(
      R"({"sw": {"ports": [
    {"logicalID": 1, "name": "eth1/1/1", "state": 2, "speed": 100000,
     "maxFrameSize": 9000},
    {"logicalID": 2, "name": "eth1/2/1", "state": 2, "speed": 100000,
     "maxFrameSize": 9412}
  ]}})",
      "hitless");

  // A normal config command in the same session edits the same staged config.
  CmdConfigArp arpCmd;
  HostInfo hostInfo("testhost");
  arpCmd.queryClient(hostInfo, ArpConfigArgs({"timeout", "45"}));

  EXPECT_EQ(*sw().arpTimeoutSeconds(), 45);
  EXPECT_EQ(*sw().ports()[0].maxFrameSize(), 9000);
  const auto staged = readFile(getSessionConfigPath());
  EXPECT_THAT(staged, HasSubstr("\"arpTimeoutSeconds\": 45"));
  EXPECT_THAT(staged, HasSubstr("\"maxFrameSize\": 9000"));
}

// =============================================================
// queryClient(): patches that change nothing
// =============================================================

TEST_F(CmdConfigJsonPatchTestFixture, emptyPatchStagesNothing) {
  setupTestableConfigSession();
  const auto before = sessionConfigText();
  const auto result = runPatch("{}");
  EXPECT_THAT(result, HasSubstr("Nothing was staged"));
  EXPECT_EQ(sessionConfigText(), before);
  EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::HITLESS);
}

TEST_F(CmdConfigJsonPatchTestFixture, sameValuePatchStagesNothing) {
  const auto result = runPatch(R"({"sw": {"arpTimeoutSeconds": 60}})");
  EXPECT_THAT(result, HasSubstr("Nothing was staged"));
  EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::HITLESS);
}

TEST_F(CmdConfigJsonPatchTestFixture, nullOnAbsentFieldStagesNothing) {
  const auto result = runPatch(R"({"sw": {"sdkVersion": null}})");
  EXPECT_THAT(result, HasSubstr("Nothing was staged"));
}

// =============================================================
// queryClient(): patches that are refused. Each must leave the staged
// config and the recorded action level untouched.
// =============================================================

class CmdConfigJsonPatchRefusedTest : public CmdConfigJsonPatchTestFixture {
 protected:
  void expectRefused(
      const std::string& patchContent,
      const std::string& errorSubstr) {
    setupTestableConfigSession();
    const auto before = sessionConfigText();
    try {
      runPatch(patchContent);
      FAIL() << "patch was not refused: " << patchContent;
    } catch (const std::runtime_error& ex) {
      EXPECT_THAT(ex.what(), HasSubstr(errorSubstr));
    }
    EXPECT_EQ(sessionConfigText(), before);
    EXPECT_EQ(*sw().arpTimeoutSeconds(), 60);
    EXPECT_EQ(requiredAction(), cli::ConfigActionLevel::HITLESS);
  }
};

TEST_F(CmdConfigJsonPatchRefusedTest, unknownField) {
  expectRefused(
      R"({"sw": {"arpTimeoutSeconds": 30, "notARealField": 1}})",
      "sw.notARealField");
}

TEST_F(CmdConfigJsonPatchRefusedTest, unknownFieldInListElement) {
  expectRefused(
      R"({"sw": {"ports": [
    {"logicalID": 1, "name": "eth1/1/1", "state": 2, "speed": 100000},
    {"logicalID": 2, "name": "eth1/2/1", "state": 2, "speed": 100000,
     "maxFrameSiez": 9000}
  ]}})",
      "sw.ports[1].maxFrameSiez");
}

TEST_F(CmdConfigJsonPatchRefusedTest, unknownTopLevelSection) {
  expectRefused(R"({"switch": {"arpTimeoutSeconds": 30}})", "switch");
}

TEST_F(CmdConfigJsonPatchRefusedTest, wrongValueType) {
  expectRefused(R"({"sw": {"arpTimeoutSeconds": "thirty"}})", "patch.json");
}

TEST_F(CmdConfigJsonPatchRefusedTest, structWhereScalarExpected) {
  expectRefused(R"({"sw": {"arpTimeoutSeconds": {"a": 1}}})", "patch.json");
}

TEST_F(CmdConfigJsonPatchRefusedTest, portWithoutName) {
  // The session's port map needs every port to be named.
  expectRefused(
      R"({"sw": {"ports": [{"logicalID": 1, "state": 2, "speed": 100000}]}})",
      "patch.json");
}

TEST_F(CmdConfigJsonPatchRefusedTest, deletesWholeSection) {
  expectRefused(R"({"sw": null})", "deletes 'sw'");
  expectRefused(R"({"platform": null})", "deletes 'platform'");
  // Also when the same patch makes other, valid changes.
  expectRefused(
      R"({"defaultCommandLineArgs": {"a": "b"}, "sw": null})", "deletes 'sw'");
}

TEST_F(CmdConfigJsonPatchRefusedTest, deletesNonOptionalField) {
  // Deleting a non-optional field would only reset it to its default; for the
  // port list that leaves a config with no ports.
  expectRefused(R"({"sw": {"ports": null}})", "deletes 'sw.ports'");
  expectRefused(
      R"({"sw": {"maxNeighborProbes": null}})",
      "deletes 'sw.maxNeighborProbes'");
  // Also next to a valid change in the same object.
  expectRefused(
      R"({"sw": {"arpTimeoutSeconds": 30, "ports": null}})",
      "deletes 'sw.ports'");
}

TEST_F(CmdConfigJsonPatchRefusedTest, nonObjectPatch) {
  expectRefused("[1, 2, 3]", "must contain a JSON object");
  expectRefused("null", "must contain a JSON object");
}

TEST_F(CmdConfigJsonPatchRefusedTest, malformedJson) {
  expectRefused(R"({"sw": {"arpTimeoutSeconds": )", "not valid JSON");
}

TEST_F(CmdConfigJsonPatchRefusedTest, missingFile) {
  setupTestableConfigSession();
  const auto before = sessionConfigText();
  CmdConfigJsonPatch cmd;
  HostInfo hostInfo("testhost");
  const auto missing = (getTestHomeDir() / "does-not-exist.json").string();
  EXPECT_THROW(
      cmd.queryClient(hostInfo, JsonPatchArgs({"agent", missing})),
      std::runtime_error);
  EXPECT_EQ(sessionConfigText(), before);
}

} // namespace facebook::fboss
