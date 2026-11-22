/*
 *  Copyright (c) 2004-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <folly/FileUtil.h>
#include <thrift/lib/cpp2/protocol/Serializer.h>
#include <filesystem>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "fboss/agent/gen-cpp2/agent_config_types.h"
#include "fboss/cli/fboss2/gen-cpp2/cli_metadata_types.h"
#include "fboss/cli/fboss2/session/AgentServiceController.h"
#include "fboss/cli/fboss2/session/BgpServiceController.h"
#include "fboss/cli/fboss2/test/TestableConfigSession.h"
#include "fboss/cli/fboss2/test/config/MockServiceControllers.h"
#include "fboss/cli/fboss2/test/config/MockSystemdInterface.h"
#include "fboss/cli/fboss2/utils/HostInfo.h"
#include "folly/IPAddress.h"

using ::testing::_; // NOLINT(bugprone-reserved-identifier)
using ::testing::InSequence;
using ::testing::NiceMock;
using ::testing::Return;
using ::testing::StrictMock;
using ::testing::Throw;

namespace facebook::fboss {

<<<<<<< HEAD
=======
namespace {
// An AgentDirectoryUtil rooted under a unique scratch directory, so tests
// never read or write the real /dev/shm coldboot markers and warm boot flags.
// Callers keep the returned path if they need to seed files under it.
// The pid keeps concurrent runs of this binary (CI shards, a shared build
// host) from wiping each other's seeded flag files mid-test.
std::string makeScratchStateDir(const std::string& name) {
  auto dir = std::filesystem::temp_directory_path() /
      ("fboss_service_util_" + name + "_" + std::to_string(::getpid()));
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir / "warm_boot");
  return dir.string();
}

AgentDirectoryUtil scratchDirUtil(const std::string& stateDir) {
  return {stateDir, stateDir};
}

// Exposes protected AgentServiceController members to the tests.
class TestableAgentServiceController : public AgentServiceController {
 public:
  using AgentServiceController::AgentServiceController;
  using AgentServiceController::findServicesMissingWarmBootState;
  using AgentServiceController::isSplitMode;
};
} // namespace

>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
// Test: isSplitMode() returns true when multi_switch flag is set
TEST(AgentServiceControllerTest, IsSplitMode_ReturnsTrueWhenMultiSwitchSet) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

<<<<<<< HEAD
  FbossServiceUtil util(
=======
  TestableAgentServiceController util(
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
      std::vector<int>{0}, /*multiSwitch=*/true, std::move(mockSystemd));
  EXPECT_TRUE(util.isSplitMode());
}

// Test: isSplitMode() returns false when multi_switch flag is not set
TEST(
    AgentServiceControllerTest,
    IsSplitMode_ReturnsFalseWhenMultiSwitchNotSet) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

<<<<<<< HEAD
  FbossServiceUtil util(
=======
  TestableAgentServiceController util(
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
      std::vector<int>{}, /*multiSwitch=*/false, std::move(mockSystemd));
  EXPECT_FALSE(util.isSplitMode());
}

// Test: Monolithic mode warmboot restart
TEST(AgentServiceControllerTest, RestartService_MonolithicMode_Warmboot) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, restartService("wedge_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _)).Times(1);

  AgentServiceController util(
      std::vector<int>{}, /*multiSwitch=*/false, std::move(mockSystemd));

  auto services = util.restart(cli::ConfigActionLevel::SERVICE_RESTART);

  EXPECT_EQ(services.size(), 1);
  EXPECT_EQ(services[0], "wedge_agent");
}

// Test: Monolithic mode coldboot restart
TEST(AgentServiceControllerTest, RestartService_MonolithicMode_Coldboot) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  // Expect marker creation, then restart -> wait for coldboot
  InSequence seq;
  EXPECT_CALL(*mockSystemd, restartService("wedge_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _)).Times(1);

  AgentServiceController util(
      std::vector<int>{}, /*multiSwitch=*/false, std::move(mockSystemd));

  auto services =
      util.restart(cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);

  EXPECT_EQ(services.size(), 1);
  EXPECT_EQ(services[0], "wedge_agent");
}

// Test: Split mode warmboot restart (single hw_agent)
<<<<<<< HEAD
// hw_agent must be restarted before sw_agent
TEST(FbossServiceUtilTest, RestartService_SplitMode_Warmboot_SingleHwAgent) {
=======
// Everything stops (sw_agent first) before anything starts (hw_agent first).
TEST(
    AgentServiceControllerTest,
    RestartService_SplitMode_Warmboot_SingleHwAgent) {
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
  auto mockSystemd = std::make_unique<StrictMock<MockSystemdInterface>>();

  InSequence seq;
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_hw_agent@0.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_sw_agent.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_sw_agent.service"}));
  EXPECT_CALL(*mockSystemd, restartService("fboss_hw_agent@0")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, restartService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);

<<<<<<< HEAD
  FbossServiceUtil util(
      std::vector<int>{0}, /*multiSwitch=*/true, std::move(mockSystemd));
=======
  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("wb_single")));
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))

  auto services = util.restart(cli::ConfigActionLevel::SERVICE_RESTART);

  EXPECT_EQ(services.size(), 2);
  EXPECT_EQ(services[0], "fboss_hw_agent@0");
  EXPECT_EQ(services[1], "fboss_sw_agent");
}

// Test: Split mode coldboot restart (single hw_agent)
<<<<<<< HEAD
// hw_agent must be fully coldbooted before sw_agent
TEST(FbossServiceUtilTest, RestartService_SplitMode_Coldboot_SingleHwAgent) {
=======
// Coldboot uses the same stop-all-then-start-all sequence as warmboot; the
// marker files are written in between.
TEST(
    AgentServiceControllerTest,
    RestartService_SplitMode_Coldboot_SingleHwAgent) {
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_hw_agent@0.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_sw_agent.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_sw_agent.service"}));

  // Expect sequential coldboot: create marker -> restart -> wait for each
  // service
  InSequence seq;
  EXPECT_CALL(*mockSystemd, restartService("fboss_hw_agent@0")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, restartService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);

<<<<<<< HEAD
  FbossServiceUtil util(
      std::vector<int>{0}, /*multiSwitch=*/true, std::move(mockSystemd));
=======
  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("cb_single")));
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))

  auto services =
      util.restart(cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);

  EXPECT_EQ(services.size(), 2);
  EXPECT_EQ(services[0], "fboss_hw_agent@0");
  EXPECT_EQ(services[1], "fboss_sw_agent");
}

// Test: Split mode warmboot restart (multiple hw_agents)
<<<<<<< HEAD
// All hw_agents must be restarted before sw_agent
TEST(FbossServiceUtilTest, RestartService_SplitMode_Warmboot_MultipleHwAgents) {
=======
// All hw_agents stop after the sw_agent, and all start before it.
TEST(
    AgentServiceControllerTest,
    RestartService_SplitMode_Warmboot_MultipleHwAgents) {
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_hw_agent@0.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_hw_agent@1.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@1.service"}));
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_sw_agent.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_sw_agent.service"}));

  // Each service: restart -> wait, in hw-before-sw order
  InSequence seq;
  EXPECT_CALL(*mockSystemd, restartService("fboss_hw_agent@0")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, restartService("fboss_hw_agent@1")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@1", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, restartService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);

<<<<<<< HEAD
  FbossServiceUtil util(
      std::vector<int>{0, 1}, /*multiSwitch=*/true, std::move(mockSystemd));
=======
  AgentServiceController util(
      std::vector<int>{0, 1},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("wb_multi")));
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))

  auto services = util.restart(cli::ConfigActionLevel::SERVICE_RESTART);

  EXPECT_EQ(services.size(), 3);
  EXPECT_EQ(services[0], "fboss_hw_agent@0");
  EXPECT_EQ(services[1], "fboss_hw_agent@1");
  EXPECT_EQ(services[2], "fboss_sw_agent");
}

TEST(AgentServiceControllerTest, RestartService_SplitMode_UsesNetosServices) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, getMatchingServices(_))
      .WillRepeatedly(Return(std::vector<std::string>{}));
  EXPECT_CALL(
      *mockSystemd,
      getMatchingServices("netos.service.fboss_wedge_agent_*_0.service"))
      .WillOnce(Return(
          std::vector<std::string>{
              "netos.service.fboss_wedge_agent_brcm_0.service"}));
  EXPECT_CALL(
      *mockSystemd, getMatchingServices("netos.service.fboss_sw_agent.service"))
      .WillOnce(Return(
          std::vector<std::string>{"netos.service.fboss_sw_agent.service"}));

  InSequence seq;
  EXPECT_CALL(
      *mockSystemd, restartService("netos.service.fboss_wedge_agent_brcm_0"));
  EXPECT_CALL(
      *mockSystemd,
      waitForServiceActive("netos.service.fboss_wedge_agent_brcm_0", _, _));
  EXPECT_CALL(*mockSystemd, restartService("netos.service.fboss_sw_agent"));
  EXPECT_CALL(
      *mockSystemd, waitForServiceActive("netos.service.fboss_sw_agent", _, _));

<<<<<<< HEAD
  FbossServiceUtil util(
      std::vector<int>{0}, /*multiSwitch=*/true, std::move(mockSystemd));
=======
  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("netos")));
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))

  const std::vector<std::string> expectedServices = {
      "netos.service.fboss_wedge_agent_brcm_0", "netos.service.fboss_sw_agent"};
  EXPECT_EQ(
      util.restart(cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART),
      expectedServices);
}

TEST(BgpServiceControllerTest, Restart_UsesNetosService) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, getMatchingServices("bgpd.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(
      *mockSystemd, getMatchingServices("netos.service.fboss_bgp.service"))
      .WillOnce(
          Return(std::vector<std::string>{"netos.service.fboss_bgp.service"}));
  EXPECT_CALL(*mockSystemd, restartService("netos.service.fboss_bgp"));
  EXPECT_CALL(
      *mockSystemd, waitForServiceActive("netos.service.fboss_bgp", _, _));

  BgpServiceController util(std::move(mockSystemd));

  EXPECT_EQ(
      util.restart(), std::vector<std::string>{"netos.service.fboss_bgp"});
}

TEST(BgpServiceControllerTest, Restart_ThrowsWhenServiceIsMissing) {
  auto mockSystemd = std::make_unique<StrictMock<MockSystemdInterface>>();

  InSequence seq;
  EXPECT_CALL(*mockSystemd, getMatchingServices("bgpd.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(
      *mockSystemd, getMatchingServices("netos.service.fboss_bgp.service"))
      .WillOnce(Return(std::vector<std::string>{}));

  BgpServiceController util(std::move(mockSystemd));

  try {
    util.restart();
    FAIL() << "Expected restart() to reject missing systemd services";
  } catch (const std::runtime_error& ex) {
    EXPECT_EQ(
        std::string(ex.what()),
        "No systemd service found for bgpd and netos.service.fboss_bgp");
  }
}

<<<<<<< HEAD
=======
// Test: the sw_agent is stopped before any hw_agent.
// This single ordering constraint is the whole bug: taking a hw_agent down
// while the sw_agent is still up makes HwSwitchConnectionStatusTable treat it
// as a crash and force both sides to cold boot.
TEST(
    AgentServiceControllerTest,
    RestartService_SplitMode_Warmboot_StopsSwAgentBeforeHwAgent) {
  // NiceMock: this test asserts one invariant, so the start calls it does not
  // name are expected to go unmatched rather than warned about.
  auto mockSystemd = std::make_unique<NiceMock<MockSystemdInterface>>();
  ON_CALL(*mockSystemd, getMatchingServices(_))
      .WillByDefault([](const std::string& pattern) {
        return std::vector<std::string>{pattern};
      });

  InSequence seq;
  EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@1")).Times(1);
  EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0")).Times(1);

  AgentServiceController util(
      std::vector<int>{0, 1},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("stop_order")));

  util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
}

// Test: a failure mid-sequence still brings the agents back up.
// systemd will not restart units we stopped explicitly, so bailing out
// without this would leave the box with no agents at all.
TEST(
    AgentServiceControllerTest,
    RestartService_SplitMode_FailureStartsServicesBack) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, getMatchingServices(_))
      .WillRepeatedly([](const std::string& pattern) {
        return std::vector<std::string>{pattern};
      });
  EXPECT_CALL(*mockSystemd, stopService(_)).Times(2);
  EXPECT_CALL(*mockSystemd, waitForServiceInactive(_, _, _)).Times(2);
  // The hw_agent start fails; recovery then retries every service.
  EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"))
      .Times(2)
      .WillOnce(Throw(std::runtime_error("Failed to start fboss_hw_agent@0")))
      .WillOnce(Return());
  EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent")).Times(1);
  // Recovery waits for each service it restarts, so the operator learns
  // whether the box actually came back.
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _))
      .Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _))
      .Times(1);

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("recovery")));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

// Test: findServicesMissingWarmBootState() names exactly the services that
// stopped without leaving warm boot state behind.
TEST(AgentServiceControllerTest, FindServicesMissingWarmBootState) {
  auto stateDir = makeScratchStateDir("missing_flags");
  auto dirUtil = scratchDirUtil(stateDir);

  // sw_agent and hw_agent@0 saved state; hw_agent@1 did not.
  folly::writeFile(
      std::string("1"), dirUtil.getSwSwitchCanWarmBootFile().c_str());
  folly::writeFile(
      std::string("1"), dirUtil.getHwSwitchCanWarmBootFile(0).c_str());

  TestableAgentServiceController util(
      std::vector<int>{0, 1},
      /*multiSwitch=*/true,
      std::make_unique<NiceMock<MockSystemdInterface>>(),
      dirUtil);

  // bgpd does not warm boot and must never be reported.
  auto missing = util.findServicesMissingWarmBootState(
      {"fboss_hw_agent@0", "fboss_hw_agent@1", "fboss_sw_agent", "bgpd"});

  ASSERT_EQ(missing.size(), 1);
  EXPECT_EQ(missing[0], "fboss_hw_agent@1");
}

// Test: with every flag present, nothing is reported.
TEST(AgentServiceControllerTest, FindServicesMissingWarmBootState_AllPresent) {
  auto stateDir = makeScratchStateDir("all_flags");
  auto dirUtil = scratchDirUtil(stateDir);

  folly::writeFile(
      std::string("1"), dirUtil.getSwSwitchCanWarmBootFile().c_str());
  folly::writeFile(
      std::string("1"), dirUtil.getHwSwitchCanWarmBootFile(0).c_str());

  TestableAgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::make_unique<NiceMock<MockSystemdInterface>>(),
      dirUtil);

  EXPECT_TRUE(util.findServicesMissingWarmBootState(
                      {"fboss_hw_agent@0", "fboss_sw_agent"})
                  .empty());
}

// Test: NetOS unit names map onto the same warm boot flag files.
TEST(
    AgentServiceControllerTest,
    FindServicesMissingWarmBootState_NetosServices) {
  auto stateDir = makeScratchStateDir("netos_flags");
  auto dirUtil = scratchDirUtil(stateDir);

  folly::writeFile(
      std::string("1"), dirUtil.getSwSwitchCanWarmBootFile().c_str());

  TestableAgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::make_unique<NiceMock<MockSystemdInterface>>(),
      dirUtil);

  auto missing = util.findServicesMissingWarmBootState(
      {"netos.service.fboss_wedge_agent_brcm_0",
       "netos.service.fboss_sw_agent",
       "netos.service.fboss_bgp"});

  ASSERT_EQ(missing.size(), 1);
  EXPECT_EQ(missing[0], "netos.service.fboss_wedge_agent_brcm_0");
}

>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
// Test: Service restart failure is propagated
TEST(AgentServiceControllerTest, RestartService_PropagatesFailure) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, restartService("wedge_agent"))
      .WillOnce(Throw(std::runtime_error("Failed to restart wedge_agent")));

  AgentServiceController util(
      std::vector<int>{}, /*multiSwitch=*/false, std::move(mockSystemd));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

// Test: Service fails to become active within timeout
TEST(AgentServiceControllerTest, RestartService_ServiceFailsToStart) {
  auto mockSystemd = std::make_unique<MockSystemdInterface>();

  EXPECT_CALL(*mockSystemd, restartService("wedge_agent")).Times(1);
  EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _))
      .WillOnce(Throw(
          std::runtime_error(
              "wedge_agent did not become active within 60 seconds")));

  AgentServiceController util(
      std::vector<int>{}, /*multiSwitch=*/false, std::move(mockSystemd));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

// ============================================================
<<<<<<< HEAD
=======
// NOS-22719: a warmboot stops each active BGP unit before the agents and
// starts it after them, so that the BGP sessions do not time out while the
// agent is down.
// ============================================================
namespace {
// A mock where only the units in activeUnits report active.
std::unique_ptr<NiceMock<MockSystemdInterface>> makeMockWithActiveUnits(
    const std::vector<std::string>& activeUnits) {
  auto mock = std::make_unique<NiceMock<MockSystemdInterface>>();
  ON_CALL(*mock, isServiceActive(_)).WillByDefault(Return(false));
  for (const auto& unit : activeUnits) {
    ON_CALL(*mock, isServiceActive(unit)).WillByDefault(Return(true));
  }
  ON_CALL(*mock, getMatchingServices(_))
      .WillByDefault([](const std::string& pattern) {
        return std::vector<std::string>{pattern};
      });
  // Any other unit may be stopped, started or waited for. A test expectation
  // set later takes precedence over these.
  EXPECT_CALL(*mock, stopService(_)).Times(::testing::AnyNumber());
  EXPECT_CALL(*mock, startService(_)).Times(::testing::AnyNumber());
  EXPECT_CALL(*mock, waitForServiceInactive(_, _, _))
      .Times(::testing::AnyNumber());
  EXPECT_CALL(*mock, waitForServiceActive(_, _, _))
      .Times(::testing::AnyNumber());
  return mock;
}

void expectNoCalls(MockSystemdInterface& mock, const std::string& unit) {
  EXPECT_CALL(mock, stopService(unit)).Times(0);
  EXPECT_CALL(mock, startService(unit)).Times(0);
}
} // namespace

TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_BgpdStopsFirstStartsLast) {
  // StrictMock: any call outside this sequence fails the test.
  auto mockSystemd = std::make_unique<StrictMock<MockSystemdInterface>>();

  InSequence seq;
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_hw_agent@0.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
  EXPECT_CALL(*mockSystemd, getMatchingServices("fboss_sw_agent.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_sw_agent.service"}));
  EXPECT_CALL(*mockSystemd, isServiceActive("openr")).WillOnce(Return(false));
  EXPECT_CALL(*mockSystemd, isServiceActive("bgpd")).WillOnce(Return(true));
  EXPECT_CALL(*mockSystemd, isServiceActive("bgpd-bb")).WillOnce(Return(false));
  EXPECT_CALL(*mockSystemd, isServiceActive("netos.service.fboss_bgp"))
      .WillOnce(Return(false));
  EXPECT_CALL(*mockSystemd, stopService("bgpd"));
  EXPECT_CALL(*mockSystemd, waitForServiceInactive("bgpd", _, _));
  EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent"));
  EXPECT_CALL(*mockSystemd, waitForServiceInactive("fboss_sw_agent", _, _));
  EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0"));
  EXPECT_CALL(*mockSystemd, waitForServiceInactive("fboss_hw_agent@0", _, _));
  EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"));
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_hw_agent@0", _, _));
  EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent"));
  EXPECT_CALL(*mockSystemd, waitForServiceActive("fboss_sw_agent", _, _));
  EXPECT_CALL(*mockSystemd, startService("bgpd"));
  EXPECT_CALL(*mockSystemd, waitForServiceActive("bgpd", _, _));

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_active")));

  // The result lists the agent units only.
  EXPECT_EQ(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      (std::vector<std::string>{"fboss_hw_agent@0", "fboss_sw_agent"}));
}

TEST(AgentServiceControllerTest, RestartService_Warmboot_BgpdBbStopsAndStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd-bb"});

  expectNoCalls(*mockSystemd, "bgpd");
  {
    InSequence seq;
    EXPECT_CALL(*mockSystemd, stopService("bgpd-bb"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, startService("bgpd-bb"));
  }

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_bb")));

  util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
}

// openr stops after BGP and before the agents. It starts after the agents and
// before BGP.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_OpenrBetweenAgentsAndBgp) {
  auto mockSystemd = makeMockWithActiveUnits({"openr", "bgpd-bb"});

  {
    InSequence seq;
    EXPECT_CALL(*mockSystemd, stopService("bgpd-bb"));
    EXPECT_CALL(*mockSystemd, stopService("openr"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, startService("openr"));
    EXPECT_CALL(*mockSystemd, startService("bgpd-bb"));
  }

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("openr_active")));

  util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
}

// An openr unit without a BGP unit is still stopped and started.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_OpenrOnlyStopsAndStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"openr"});

  expectNoCalls(*mockSystemd, "bgpd");
  expectNoCalls(*mockSystemd, "bgpd-bb");
  expectNoCalls(*mockSystemd, "netos.service.fboss_bgp");
  {
    InSequence seq;
    EXPECT_CALL(*mockSystemd, stopService("openr"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, startService("openr"));
  }

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("openr_only")));

  util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
}

TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_NetosBgpStopsAndStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"netos.service.fboss_bgp"});

  expectNoCalls(*mockSystemd, "bgpd");
  expectNoCalls(*mockSystemd, "bgpd-bb");
  {
    InSequence seq;
    EXPECT_CALL(*mockSystemd, stopService("netos.service.fboss_bgp"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, stopService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"));
    EXPECT_CALL(*mockSystemd, startService("fboss_sw_agent"));
    EXPECT_CALL(*mockSystemd, startService("netos.service.fboss_bgp"));
  }

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgp_netos")));

  util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
}

// A failed bgpd stop must not leave bgpd down: the recovery path starts it.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_BgpdStopFailsBgpdStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd"});

  EXPECT_CALL(*mockSystemd, stopService("bgpd"))
      .WillOnce(Throw(std::runtime_error("Failed to stop bgpd")));
  EXPECT_CALL(*mockSystemd, startService("bgpd")).Times(1);

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_stop_fail")));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

TEST(AgentServiceControllerTest, RestartService_Warmboot_AgentFailsBgpdStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd"});

  EXPECT_CALL(*mockSystemd, stopService("bgpd")).Times(1);
  // The hw_agent start fails once; the recovery start works.
  EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"))
      .WillOnce(Throw(std::runtime_error("Failed to start fboss_hw_agent@0")))
      .WillOnce(Return());
  EXPECT_CALL(*mockSystemd, startService("bgpd")).Times(1);

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_agent_fail")));

  try {
    util.restart(cli::ConfigActionLevel::SERVICE_RESTART);
    FAIL() << "Expected the agent start failure to propagate";
  } catch (const std::runtime_error& ex) {
    EXPECT_THAT(ex.what(), ::testing::HasSubstr("fboss_hw_agent@0"));
  }
}

// A failed agent start must not leave openr down: the recovery path starts it.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_AgentFailsOpenrStarts) {
  auto mockSystemd = makeMockWithActiveUnits({"openr"});

  EXPECT_CALL(*mockSystemd, stopService("openr")).Times(1);
  // The hw_agent start fails once; the recovery start works.
  EXPECT_CALL(*mockSystemd, startService("fboss_hw_agent@0"))
      .WillOnce(Throw(std::runtime_error("Failed to start fboss_hw_agent@0")))
      .WillOnce(Return());
  EXPECT_CALL(*mockSystemd, startService("openr")).Times(1);

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("openr_agent_fail")));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

// Known effect: a bgpd that does not become active makes restartService throw,
// although both agents are active again.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_BgpdNeverActiveThrows) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd"});

  EXPECT_CALL(*mockSystemd, waitForServiceActive("bgpd", _, _))
      .WillRepeatedly(Throw(
          std::runtime_error("bgpd did not become active within 60 seconds")));

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_never_active")));

  EXPECT_THROW(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      std::runtime_error);
}

// Monolithic mode: with bgpd active, the single agent unit is stopped and
// started instead of restarted.
TEST(
    AgentServiceControllerTest,
    RestartService_Warmboot_MonolithicStopsAndStartsBgpd) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd"});

  EXPECT_CALL(*mockSystemd, restartService(_)).Times(0);
  {
    InSequence seq;
    EXPECT_CALL(*mockSystemd, stopService("bgpd"));
    EXPECT_CALL(*mockSystemd, stopService("wedge_agent"));
    EXPECT_CALL(*mockSystemd, startService("wedge_agent"));
    EXPECT_CALL(*mockSystemd, waitForServiceActive("wedge_agent", _, _));
    EXPECT_CALL(*mockSystemd, startService("bgpd"));
    EXPECT_CALL(*mockSystemd, waitForServiceActive("bgpd", _, _));
  }

  AgentServiceController util(
      std::vector<int>{},
      /*multiSwitch=*/false,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgpd_monolithic")));

  EXPECT_EQ(
      util.restart(cli::ConfigActionLevel::SERVICE_RESTART),
      (std::vector<std::string>{"wedge_agent"}));
}

// Coldboot is not changed: no BGP unit is checked, stopped or started.
TEST(AgentServiceControllerTest, RestartService_Coldboot_NoBgpCall) {
  auto mockSystemd = makeMockWithActiveUnits({"bgpd"});

  EXPECT_CALL(*mockSystemd, isServiceActive(_)).Times(0);
  expectNoCalls(*mockSystemd, "bgpd");
  expectNoCalls(*mockSystemd, "bgpd-bb");
  expectNoCalls(*mockSystemd, "netos.service.fboss_bgp");

  AgentServiceController util(
      std::vector<int>{0},
      /*multiSwitch=*/true,
      std::move(mockSystemd),
      scratchDirUtil(makeScratchStateDir("bgp_coldboot")));

  util.restart(cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART);
}

// ============================================================
>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
// Test: waitForAgentConfigured() polls the given host until the agent is
// configured.
TEST(AgentServiceControllerTest, WaitForAgentConfigured_PollsUntilConfigured) {
  MockAgentServiceController util;
  HostInfo hostInfo("dut1", "dut1-oob", folly::IPAddress("10.0.0.1"));

  EXPECT_CALL(
      util, isAgentConfigured(::testing::Property(&HostInfo::getName, "dut1")))
      .WillOnce(Return(false))
      .WillOnce(Return(false))
      .WillOnce(Return(true));

  util.waitForAgentConfigured(
      hostInfo, /*maxWaitSeconds=*/5, /*pollIntervalMs=*/10);
}

// Test: waitForAgentConfigured() throws if the agent never becomes configured.
TEST(AgentServiceControllerTest, WaitForAgentConfigured_ThrowsOnTimeout) {
  MockAgentServiceController util;
  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  EXPECT_CALL(util, isAgentConfigured(_)).WillRepeatedly(Return(false));

  EXPECT_THROW(
      util.waitForAgentConfigured(
          hostInfo, /*maxWaitSeconds=*/1, /*pollIntervalMs=*/10),
      std::runtime_error);
}

// ConfigSession integration tests using MockAgentServiceController
// These verify that ConfigSession::applyServiceActions() correctly
// delegates to the agent controller without touching real systemd or thrift.
// ============================================================

// Test: applyServiceActions() delegates SERVICE_RESTART to
// AgentServiceController::restart()
TEST(
    ConfigSessionServiceTest,
    ApplyServiceActions_Warmboot_DelegatesToRestartService) {
  auto mock = std::make_unique<MockAgentServiceController>();
  auto* mockPtr = mock.get();

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  EXPECT_CALL(*mockPtr, restart(cli::ConfigActionLevel::SERVICE_RESTART))
      .WillOnce(::testing::Return(std::vector<std::string>{"wedge_agent"}));
  EXPECT_CALL(*mockPtr, isAgentConfigured(_)).WillOnce(Return(true));

  TestableConfigSession session(
      "/tmp/test_session", "/tmp/test_system", std::move(mock));

  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT, cli::ConfigActionLevel::SERVICE_RESTART}};
  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 1);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "wedge_agent");
}

// Test: applyServiceActions() delegates DISRUPTIVE_SERVICE_RESTART to
// AgentServiceController::restart()
TEST(
    ConfigSessionServiceTest,
    ApplyServiceActions_Coldboot_DelegatesToRestartService) {
  auto mock = std::make_unique<MockAgentServiceController>();
  auto* mockPtr = mock.get();

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  EXPECT_CALL(
      *mockPtr, restart(cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART))
      .WillOnce(
          ::testing::Return(
              std::vector<std::string>{"fboss_hw_agent@0", "fboss_sw_agent"}));
  EXPECT_CALL(*mockPtr, isAgentConfigured(_)).WillOnce(Return(true));

  TestableConfigSession session(
      "/tmp/test_session", "/tmp/test_system", std::move(mock));

  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT,
       cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART}};
  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 2);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "fboss_hw_agent@0");
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][1], "fboss_sw_agent");
}

// Test: ConfigSession::applyServiceActions() delegates HITLESS to
// AgentServiceController::reloadConfig() (monolithic mode)
TEST(
    ConfigSessionServiceTest,
    ApplyServiceActions_Hitless_DelegatesToReloadConfig_Monolithic) {
  auto mock = std::make_unique<MockAgentServiceController>();
  auto* mockPtr = mock.get();

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  EXPECT_CALL(*mockPtr, reloadConfig(::testing::_))
      .WillOnce(::testing::Return(std::vector<std::string>{"wedge_agent"}));
  EXPECT_CALL(*mockPtr, isAgentConfigured(_)).Times(0);

  TestableConfigSession session(
      "/tmp/test_session", "/tmp/test_system", std::move(mock));

  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS}};

  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  ASSERT_EQ(serviceNames.size(), 1);
  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 1);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "wedge_agent");
}

// Test: ConfigSession::applyServiceActions() delegates HITLESS to
// AgentServiceController::reloadConfig() (split mode)
TEST(
    ConfigSessionServiceTest,
    ApplyServiceActions_Hitless_DelegatesToReloadConfig_SplitMode) {
  auto mock = std::make_unique<MockAgentServiceController>();
  auto* mockPtr = mock.get();

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  EXPECT_CALL(*mockPtr, reloadConfig(::testing::_))
      .WillOnce(::testing::Return(std::vector<std::string>{"fboss_sw_agent"}));

  TestableConfigSession session(
      "/tmp/test_session", "/tmp/test_system", std::move(mock));

  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS}};

  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  ASSERT_EQ(serviceNames.size(), 1);
  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 1);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "fboss_sw_agent");
}

// ============================================================
// Tests for the agent domain Thrift-based detection
// Verify that multi-switch mode is detected via Thrift RPC (runtime state),
// not from the config file's defaultCommandLineArgs.
// ============================================================

// Test: Config file has no multi_switch flag, but agent is running in
// multi-switch mode. the agent domain should detect multi-switch
// via Thrift and restart fboss_sw_agent + fboss_hw_agent@N.
TEST(ConfigSessionServiceTest, AgentController_DetectsMultiSwitchViaThrift) {
  // Write a minimal config so initializeSession() succeeds.
  // the agent domain no longer reads the config — it gets everything
  // from the Thrift RPC (simulated via overrides here).
  cfg::AgentConfig agentConfig;
  auto configJson =
      apache::thrift::SimpleJSONSerializer::serialize<std::string>(agentConfig);

  std::filesystem::create_directories("/tmp/test_system_thrift");
  std::filesystem::create_directories("/tmp/test_session_thrift");
  folly::writeFile(configJson, "/tmp/test_system_thrift/agent.conf");

  TestableConfigSession session(
      "/tmp/test_session_thrift", "/tmp/test_system_thrift");

  // Simulate Thrift RPC reporting multi-switch with 1 hw_agent at index 0
  session.setMultiSwitchOverride(true, {0});
  session.setMockSystemdFactory([] {
    auto mock = std::make_unique<NiceMock<MockSystemdInterface>>();
    ON_CALL(*mock, getMatchingServices(_))
        .WillByDefault([](const std::string& pattern) {
          return std::vector<std::string>{pattern};
        });
    return mock;
  });

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));

  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT,
       cli::ConfigActionLevel::DISRUPTIVE_SERVICE_RESTART}};

  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  // Should restart multi-switch services, not wedge_agent
  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 2);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "fboss_hw_agent@0");
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][1], "fboss_sw_agent");

  std::filesystem::remove_all("/tmp/test_session_thrift");
  std::filesystem::remove_all("/tmp/test_system_thrift");
}

<<<<<<< HEAD
=======
// ============================================================
// Config rollback/commit must work when the agent is down.
// AgentServiceController::fromSystemd() detects the mode from systemd, and
// reloadConfig() on an unreachable agent falls back to a restart.
// ============================================================

namespace {

// Let each service resolve to its own (Classic) systemd unit name.
void expectClassicUnits(
    MockSystemdInterface& systemd,
    const std::vector<std::string>& services) {
  for (const auto& service : services) {
    auto unit = fmt::format("{}.service", service);
    EXPECT_CALL(systemd, getMatchingServices(unit))
        .WillRepeatedly(Return(std::vector<std::string>{unit}));
  }
}

// Expect the stop-all-then-start-all warm boot sequence for a split-mode box
// with a single hw_agent: sw_agent stops first, hw_agent starts first.
void expectSplitWarmbootSequence(MockSystemdInterface& systemd) {
  expectClassicUnits(systemd, {"fboss_hw_agent@0", "fboss_sw_agent"});
  InSequence seq;
  EXPECT_CALL(systemd, stopService("fboss_sw_agent"));
  EXPECT_CALL(systemd, waitForServiceInactive("fboss_sw_agent", _, _));
  EXPECT_CALL(systemd, stopService("fboss_hw_agent@0"));
  EXPECT_CALL(systemd, waitForServiceInactive("fboss_hw_agent@0", _, _));
  EXPECT_CALL(systemd, startService("fboss_hw_agent@0"));
  EXPECT_CALL(systemd, waitForServiceActive("fboss_hw_agent@0", _, _));
  EXPECT_CALL(systemd, startService("fboss_sw_agent"));
  EXPECT_CALL(systemd, waitForServiceActive("fboss_sw_agent", _, _));
}

} // namespace

// fromSystemd(): hw_agent template instances known to systemd => split mode,
// with indexes parsed from the unit names and sorted.
TEST(
    AgentServiceControllerOfflineTest,
    FromSystemd_DetectsSplitModeFromHwAgentUnits) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(
          std::vector<std::string>{
              "fboss_hw_agent@1.service", "fboss_hw_agent@0.service"}));
  // Split mode is established from the instances alone; is-enabled is not
  // consulted.
  EXPECT_CALL(*systemd, isServiceEnabled(_)).Times(0);
  auto* systemdPtr = systemd.get();

  auto util = AgentServiceController::fromSystemd(std::move(systemd));

  // Split mode: the restart covers every hw_agent, in sorted index order.
  expectClassicUnits(
      *systemdPtr, {"fboss_hw_agent@0", "fboss_hw_agent@1", "fboss_sw_agent"});
  {
    InSequence seq;
    EXPECT_CALL(*systemdPtr, stopService("fboss_sw_agent"));
    EXPECT_CALL(*systemdPtr, waitForServiceInactive("fboss_sw_agent", _, _));
    EXPECT_CALL(*systemdPtr, stopService("fboss_hw_agent@1"));
    EXPECT_CALL(*systemdPtr, waitForServiceInactive("fboss_hw_agent@1", _, _));
    EXPECT_CALL(*systemdPtr, stopService("fboss_hw_agent@0"));
    EXPECT_CALL(*systemdPtr, waitForServiceInactive("fboss_hw_agent@0", _, _));
    EXPECT_CALL(*systemdPtr, startService("fboss_hw_agent@0"));
    EXPECT_CALL(*systemdPtr, waitForServiceActive("fboss_hw_agent@0", _, _));
    EXPECT_CALL(*systemdPtr, startService("fboss_hw_agent@1"));
    EXPECT_CALL(*systemdPtr, waitForServiceActive("fboss_hw_agent@1", _, _));
    EXPECT_CALL(*systemdPtr, startService("fboss_sw_agent"));
    EXPECT_CALL(*systemdPtr, waitForServiceActive("fboss_sw_agent", _, _));
  }
  auto restarted = util->restart(cli::ConfigActionLevel::SERVICE_RESTART);
  ASSERT_EQ(restarted.size(), 3);
  EXPECT_EQ(restarted[0], "fboss_hw_agent@0");
  EXPECT_EQ(restarted[1], "fboss_hw_agent@1");
  EXPECT_EQ(restarted[2], "fboss_sw_agent");
}

// fromSystemd(): no hw_agent instances and wedge_agent enabled => monolithic.
TEST(AgentServiceControllerOfflineTest, FromSystemd_DetectsMonolithicMode) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(*systemd, isServiceEnabled("fboss_sw_agent"))
      .WillOnce(Return(false));
  EXPECT_CALL(*systemd, isServiceEnabled("wedge_agent")).WillOnce(Return(true));
  auto* systemdPtr = systemd.get();

  auto util = AgentServiceController::fromSystemd(std::move(systemd));

  // Monolithic mode: the restart covers wedge_agent only.
  {
    InSequence seq;
    EXPECT_CALL(*systemdPtr, restartService("wedge_agent"));
    EXPECT_CALL(*systemdPtr, waitForServiceActive("wedge_agent", _, _));
  }
  auto restarted = util->restart(cli::ConfigActionLevel::SERVICE_RESTART);
  ASSERT_EQ(restarted.size(), 1);
  EXPECT_EQ(restarted[0], "wedge_agent");
}

// fromSystemd(): sw_agent enabled but no hw_agent instance to manage is an
// error rather than a guess.
TEST(AgentServiceControllerOfflineTest, FromSystemd_SplitWithoutHwAgentThrows) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(*systemd, isServiceEnabled("fboss_sw_agent"))
      .WillOnce(Return(true));

  EXPECT_THROW(
      AgentServiceController::fromSystemd(std::move(systemd)),
      std::runtime_error);
}

// fromSystemd(): nothing known to systemd is an error too.
TEST(AgentServiceControllerOfflineTest, FromSystemd_NoAgentUnitsThrows) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(*systemd, isServiceEnabled("fboss_sw_agent"))
      .WillOnce(Return(false));
  EXPECT_CALL(*systemd, isServiceEnabled("wedge_agent"))
      .WillOnce(Return(false));

  EXPECT_THROW(
      AgentServiceController::fromSystemd(std::move(systemd)),
      std::runtime_error);
}

// reloadConfig() on an unreachable agent: no thrift, a warm boot restart
// instead (split mode).
TEST(
    AgentServiceControllerOfflineTest,
    ReloadConfig_AgentDown_RestartsSplitMode) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
  auto* systemdPtr = systemd.get();
  auto util = AgentServiceController::fromSystemd<NoAgentServiceController>(
      std::move(systemd));

  expectSplitWarmbootSequence(*systemdPtr);

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));
  auto services = util->reloadConfig(hostInfo);
  ASSERT_EQ(services.size(), 2);
  EXPECT_EQ(services[0], "fboss_hw_agent@0");
  EXPECT_EQ(services[1], "fboss_sw_agent");
}

// reloadConfig() on an unreachable agent, monolithic mode: a plain restart of
// wedge_agent.
TEST(
    AgentServiceControllerOfflineTest,
    ReloadConfig_AgentDown_RestartsMonolithic) {
  auto systemd = std::make_unique<MockSystemdInterface>();
  EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
      .WillOnce(Return(std::vector<std::string>{}));
  EXPECT_CALL(*systemd, isServiceEnabled("fboss_sw_agent"))
      .WillOnce(Return(false));
  EXPECT_CALL(*systemd, isServiceEnabled("wedge_agent")).WillOnce(Return(true));
  auto* systemdPtr = systemd.get();
  auto util = AgentServiceController::fromSystemd<NoAgentServiceController>(
      std::move(systemd));

  {
    InSequence seq;
    EXPECT_CALL(*systemdPtr, restartService("wedge_agent"));
    EXPECT_CALL(*systemdPtr, waitForServiceActive("wedge_agent", _, _));
  }

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));
  auto services = util->reloadConfig(hostInfo);
  ASSERT_EQ(services.size(), 1);
  EXPECT_EQ(services[0], "wedge_agent");
}

namespace {
// Reports the agent configured on the second poll and counts the polls.
class SlowAgentServiceController : public AgentServiceController {
 public:
  using AgentServiceController::AgentServiceController;
  bool isAgentConfigured(const HostInfo& /*hostInfo*/) override {
    return ++polls >= 2;
  }
  int polls{0};
};
} // namespace

// The restart that stands in for a reload when the agent is down also waits
// for the agent to be configured before it returns.
TEST(
    AgentServiceControllerOfflineTest,
    ReloadConfig_AgentDown_WaitsForAgentConfigured) {
  auto systemd = std::make_unique<NiceMock<MockSystemdInterface>>();
  ON_CALL(*systemd, isServiceEnabled("wedge_agent"))
      .WillByDefault(Return(true));
  auto util = AgentServiceController::fromSystemd<SlowAgentServiceController>(
      std::move(systemd));

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));
  EXPECT_EQ(
      util->reloadConfig(hostInfo), std::vector<std::string>{"wedge_agent"});
  EXPECT_EQ(util->polls, 2);
}

// ConfigSession: local host, thrift probe fails => systemd fallback, and a
// HITLESS action becomes a restart of the services systemd reported.
TEST(ConfigSessionServiceTest, AgentController_AgentDown_LocalFallsBack) {
  cfg::AgentConfig agentConfig;
  auto configJson =
      apache::thrift::SimpleJSONSerializer::serialize<std::string>(agentConfig);
  std::filesystem::create_directories("/tmp/test_system_agent_down");
  std::filesystem::create_directories("/tmp/test_session_agent_down");
  folly::writeFile(configJson, "/tmp/test_system_agent_down/agent.conf");

  TestableConfigSession session(
      "/tmp/test_session_agent_down", "/tmp/test_system_agent_down");
  session.setAgentUnreachable(true);
  session.setMockSystemdFactory([] {
    auto systemd = std::make_unique<MockSystemdInterface>();
    EXPECT_CALL(*systemd, getMatchingServices("fboss_hw_agent@*.service"))
        .WillOnce(Return(std::vector<std::string>{"fboss_hw_agent@0.service"}));
    expectSplitWarmbootSequence(*systemd);
    return systemd;
  });

  HostInfo hostInfo(
      "localhost", "localhost-oob", folly::IPAddress("127.0.0.1"));
  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS}};

  auto serviceNames = session.applyServiceActions(actions, hostInfo);

  ASSERT_EQ(serviceNames[cli::ServiceType::AGENT].size(), 2);
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][0], "fboss_hw_agent@0");
  EXPECT_EQ(serviceNames[cli::ServiceType::AGENT][1], "fboss_sw_agent");

  std::filesystem::remove_all("/tmp/test_session_agent_down");
  std::filesystem::remove_all("/tmp/test_system_agent_down");
}

// ConfigSession: remote host, thrift probe fails => no systemd fallback (we
// cannot drive a remote systemd); the original "Is the agent running?" error.
TEST(ConfigSessionServiceTest, AgentController_AgentDown_RemoteThrows) {
  cfg::AgentConfig agentConfig;
  auto configJson =
      apache::thrift::SimpleJSONSerializer::serialize<std::string>(agentConfig);
  std::filesystem::create_directories("/tmp/test_system_agent_down_remote");
  std::filesystem::create_directories("/tmp/test_session_agent_down_remote");
  folly::writeFile(configJson, "/tmp/test_system_agent_down_remote/agent.conf");

  TestableConfigSession session(
      "/tmp/test_session_agent_down_remote",
      "/tmp/test_system_agent_down_remote");
  session.setAgentUnreachable(true);
  bool systemdRequested = false;
  session.setMockSystemdFactory([&systemdRequested] {
    systemdRequested = true;
    return std::make_unique<MockSystemdInterface>();
  });

  HostInfo hostInfo("rsw001", "rsw001-oob", folly::IPAddress("10.1.2.3"));
  std::map<cli::ServiceType, cli::ConfigActionLevel> actions = {
      {cli::ServiceType::AGENT, cli::ConfigActionLevel::HITLESS}};

  try {
    session.applyServiceActions(actions, hostInfo);
    FAIL() << "expected applyServiceActions to throw";
  } catch (const std::runtime_error& ex) {
    EXPECT_THAT(
        std::string(ex.what()),
        ::testing::HasSubstr("Failed to query agent run state from rsw001"));
    EXPECT_THAT(
        std::string(ex.what()), ::testing::HasSubstr("Is the agent running?"));
  }
  EXPECT_FALSE(systemdRequested);

  std::filesystem::remove_all("/tmp/test_session_agent_down_remote");
  std::filesystem::remove_all("/tmp/test_system_agent_down_remote");
}

>>>>>>> 029458680e (NOS-23962: [fboss2] Give each config domain its own service controller (3/6) (#3081))
} // namespace facebook::fboss
