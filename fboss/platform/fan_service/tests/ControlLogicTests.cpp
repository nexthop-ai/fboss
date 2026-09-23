// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include <algorithm>
#include <map>

#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include <thrift/lib/cpp2/protocol/Serializer.h>

#include "fboss/agent/FbossError.h"
#include "fboss/platform/config_lib/ConfigLib.h"
#include "fboss/platform/fan_service/Bsp.h"
#include "fboss/platform/fan_service/ControlLogic.h"
#include "fboss/platform/fan_service/SensorData.h"
#include "fboss/platform/fan_service/if/gen-cpp2/fan_service_config_constants.h"

using namespace ::testing;
using namespace facebook::fboss::platform::fan_service;

namespace {

float kDefaultRpm = 31;

// An optic type the sample platform config has no thermal profile for.
const std::string kUnprofiledOpticType = "OPTIC_TYPE_800_ZR";
const std::string kProfiledOpticType = "OPTIC_TYPE_400_GENERIC";

std::array<int, 5> kExpectedPwms = std::array<int, 5>{49, 49, 48, 48, 47};
std::array<int, 5> kExpectedBoostModePwms =
    std::array<int, 5>{51, 51, 52, 52, 53};

}; // namespace

namespace facebook::fboss::platform {
class MockBsp : public Bsp {
 public:
  explicit MockBsp(const FanServiceConfig& config) : Bsp(config) {}
  MOCK_METHOD(bool, setFanPwmSysfs, (const std::string&, int));
  MOCK_METHOD(bool, turnOnLedSysfs, (const std::string&));
  MOCK_METHOD(bool, checkIfInitialSensorDataRead, (), (const));
  MOCK_METHOD(float, readSysfs, (const std::string&), (const));
  std::optional<int> getLedMaxBrightness(const std::string&) const override {
    return 255;
  }
};

class ControlLogicTests : public testing::Test {
 public:
  void SetUp() override {
    // fb303 counters are process-global. Without this, a counter set by an
    // earlier test satisfies assertions in a later one.
    fb303::fbData->resetAllData();

    auto fanServiceConfJson = ConfigLib().getFanServiceConfig("sample");

    apache::thrift::SimpleJSONSerializer::deserialize<FanServiceConfig>(
        fanServiceConfJson, fanServiceConfig_);
    mockBsp_ = std::make_shared<MockBsp>(fanServiceConfig_);
    controlLogic_ = std::make_shared<ControlLogic>(fanServiceConfig_, mockBsp_);
    sensorData_ = std::make_shared<SensorData>();

    float value = 30.0;
    for (const auto& sensor : *fanServiceConfig_.sensors()) {
      sensorData_->updateSensorEntry(
          *sensor.sensorName(), value, mockBsp_->getCurrentTime());
      value += 10.5;
    }

    for (const auto& optic : *fanServiceConfig_.optics()) {
      value = 30.0;
      std::map<std::string, std::vector<OpticData>> opticData;
      int32_t txvrId = 1;
      for (const auto& [opticType, tempToPwm] : *optic.tempToPwmMaps()) {
        opticData[opticType].push_back(OpticData{txvrId++, value});
        value += 12.0;
      }
      sensorData_->updateOpticEntry(
          *optic.opticName(), opticData, mockBsp_->getCurrentTime());
    }

    ASSERT_TRUE(kExpectedPwms.size() == fanServiceConfig_.fans()->size());
  }

  // Sets up the fan sysfs expectations shared by the updateControl() tests.
  void expectFanAccess() {
    EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead())
        .WillRepeatedly(Return(true));
    for (const auto& fan : *fanServiceConfig_.fans()) {
      EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
          .WillRepeatedly(Return(true));
      EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
          .WillRepeatedly(Return(true));
      EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
          .WillRepeatedly(Return(kDefaultRpm));
      EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
          .WillRepeatedly(Return(1 /* fan exists */));
    }
  }

  // Removes an optic type from every optic group's cached data, as if the
  // transceiver had been unplugged.
  void removeOpticTypeFromSensorData(const std::string& opticType) {
    for (const auto& optic : *fanServiceConfig_.optics()) {
      auto opticEntry = sensorData_->getOpticEntry(*optic.opticName());
      auto opticData = opticEntry->data;
      opticData.erase(opticType);
      sensorData_->updateOpticEntry(
          *optic.opticName(), opticData, mockBsp_->getCurrentTime());
    }
  }

  // Empties every optic group's cached data, as if qsfp_service had stopped
  // publishing.
  void clearOpticDataForAllGroups() {
    for (const auto& optic : *fanServiceConfig_.optics()) {
      sensorData_->updateOpticEntry(
          *optic.opticName(), {}, mockBsp_->getCurrentTime());
    }
  }

  // Adds an extra optic type to every optic group's cached data.
  void addOpticTypeToSensorData(const std::string& opticType, float temp) {
    for (const auto& optic : *fanServiceConfig_.optics()) {
      auto opticEntry = sensorData_->getOpticEntry(*optic.opticName());
      auto opticData = opticEntry->data;
      opticData[opticType].push_back(OpticData{99, temp});
      sensorData_->updateOpticEntry(
          *optic.opticName(), opticData, mockBsp_->getCurrentTime());
    }
  }

  FanServiceConfig fanServiceConfig_;
  std::shared_ptr<SensorData> sensorData_;
  std::shared_ptr<MockBsp> mockBsp_;
  std::shared_ptr<ControlLogic> controlLogic_;
};

TEST_F(ControlLogicTests, SetTransitionValueSuccess) {
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .WillOnce(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath())).Times(0);
  }

  controlLogic_->setTransitionValue();

  for (const auto& [fanName, fanStatus] : controlLogic_->getFanStatuses()) {
    EXPECT_EQ(*fanStatus.fanFailed(), false);
    EXPECT_EQ(
        *fanStatus.pwmToProgram(), *fanServiceConfig_.pwmTransitionValue());
  }
}

TEST_F(ControlLogicTests, SetTransitionValueFailure) {
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .WillOnce(Return(false));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.failLedSysfsPath()))
        .Times(1)
        .WillOnce(Return(true));
  }

  controlLogic_->setTransitionValue();

  for (const auto& [fanName, fanStatus] : controlLogic_->getFanStatuses()) {
    EXPECT_EQ(*fanStatus.fanFailed(), true);
    EXPECT_EQ(
        *fanStatus.pwmToProgram(), *fanServiceConfig_.pwmTransitionValue());
  }
}

TEST_F(ControlLogicTests, UpdateControlSuccess) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .WillOnce(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Return(kDefaultRpm));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(1 /* fan exists */));
  }

  auto startTime = mockBsp_->getCurrentTime();

  controlLogic_->setTransitionValue();

  controlLogic_->updateControl(sensorData_);
  const auto fanStatuses = controlLogic_->getFanStatuses();
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  int i = 0;
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.fanFailed(), false);
    EXPECT_EQ(*fanStatus.rpm(), kDefaultRpm);
    EXPECT_GE(*fanStatus.lastSuccessfulAccessTime(), startTime);
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedPwms[i++]);
    EXPECT_EQ(fb303::fbData->getCounter(fmt::format("{}.absent", fanName)), 0);
    EXPECT_EQ(
        fb303::fbData->getCounter(fmt::format("{}.rpm_read.failure", fanName)),
        0);
  }
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_rpm_read_failure"), 0);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_pwm_write_failure"), 0);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_absent"), 0);
  const auto& sensorCaches = controlLogic_->getSensorCaches();
  for (const auto& [sensorName, sensorCache] : sensorCaches) {
    EXPECT_EQ(sensorCache.sensorFailed, false);
    EXPECT_EQ(
        fb303::fbData->getCounter(
            fmt::format("{}.sensor_read.failure", sensorName)),
        0);
  }
}

TEST_F(ControlLogicTests, UpdateControlFailureDueToMissingFans) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.failLedSysfsPath()))
        .WillOnce(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath())).Times(0);
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(0 /* fan missing */));
  }

  controlLogic_->setTransitionValue();

  controlLogic_->updateControl(sensorData_);
  const auto fanStatuses = controlLogic_->getFanStatuses();
  int i = 0;
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.fanFailed(), true);
    EXPECT_EQ(fanStatus.rpm().has_value(), false);
    EXPECT_EQ(*fanStatus.lastSuccessfulAccessTime(), 0);
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedBoostModePwms[i++]);
    EXPECT_EQ(fb303::fbData->getCounter(fmt::format("{}.absent", fanName)), 1);
    EXPECT_EQ(
        fb303::fbData->getCounter(fmt::format("{}.rpm_read.failure", fanName)),
        1);
  }
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_rpm_read_failure"), 1);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_pwm_write_failure"), 0);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_absent"), 1);
}

TEST_F(ControlLogicTests, UpdateControlFailureDueToFanInaccessible) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.failLedSysfsPath()))
        .Times(1)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Throw(std::exception()));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(1 /* fan exists */));
  }

  controlLogic_->setTransitionValue();

  controlLogic_->updateControl(sensorData_);
  const auto fanStatuses = controlLogic_->getFanStatuses();
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  int i = 0;
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.fanFailed(), true);
    EXPECT_EQ(fanStatus.rpm().has_value(), false);
    EXPECT_EQ(*fanStatus.lastSuccessfulAccessTime(), 0);
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedBoostModePwms[i++]);
    EXPECT_EQ(fb303::fbData->getCounter(fmt::format("{}.absent", fanName)), 0);
    EXPECT_EQ(
        fb303::fbData->getCounter(fmt::format("{}.rpm_read.failure", fanName)),
        1);
  }
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_rpm_read_failure"), 1);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_pwm_write_failure"), 0);
  EXPECT_EQ(fb303::fbData->getCounter("has.fan_absent"), 0);
}

TEST_F(
    ControlLogicTests,
    UpdateControlFailureDueToFanInaccessibleAfterSuccessLTThreshold) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead())
      .Times(2)
      .WillRepeatedly(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(3)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Return(kDefaultRpm))
        .WillOnce(Throw(std::exception()));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .Times(2)
        .WillRepeatedly(Return(1 /* fan exists */));
  }

  auto startTime = mockBsp_->getCurrentTime();

  controlLogic_->setTransitionValue();

  // Simulate two cycles of programing fan.
  controlLogic_->updateControl(sensorData_);
  controlLogic_->updateControl(sensorData_);
  const auto fanStatuses = controlLogic_->getFanStatuses();
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.fanFailed(), false);
    EXPECT_EQ(fanStatus.rpm().has_value(), false);
    EXPECT_GE(*fanStatus.lastSuccessfulAccessTime(), startTime);
    EXPECT_EQ(fb303::fbData->getCounter(fmt::format("{}.absent", fanName)), 0);
    EXPECT_EQ(
        fb303::fbData->getCounter(fmt::format("{}.rpm_read.failure", fanName)),
        1);
  }
}
TEST_F(ControlLogicTests, UpdateControlSensorReadFailure) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .WillOnce(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Return(kDefaultRpm));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(1 /* fan exists */));
  }

  auto startTime = mockBsp_->getCurrentTime();

  controlLogic_->setTransitionValue();

  for (const auto& sensor : *fanServiceConfig_.sensors()) {
    sensorData_->delSensorEntry(*sensor.sensorName());
  }
  controlLogic_->updateControl(sensorData_);
  const auto fanStatuses = controlLogic_->getFanStatuses();
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  int i = 0;
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.fanFailed(), false);
    EXPECT_EQ(*fanStatus.rpm(), kDefaultRpm);
    EXPECT_GE(*fanStatus.lastSuccessfulAccessTime(), startTime);
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedPwms[i++]);
    EXPECT_EQ(fb303::fbData->getCounter(fmt::format("{}.absent", fanName)), 0);
    EXPECT_EQ(
        fb303::fbData->getCounter(fmt::format("{}.rpm_read.failure", fanName)),
        0);
  }
  const auto& sensorCaches = controlLogic_->getSensorCaches();
  for (const auto& [sensorName, sensorCache] : sensorCaches) {
    EXPECT_EQ(sensorCache.sensorFailed, true);
    EXPECT_EQ(
        fb303::fbData->getCounter(
            fmt::format("{}.sensor_read.failure", sensorName)),
        1);
  }
}

TEST_F(ControlLogicTests, OpticsFb303CountersAreSet) {
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *fanServiceConfig_.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .WillOnce(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Return(kDefaultRpm));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(1 /* fan exists */));
  }

  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  // Verify optics counters are set per optic type.
  // SetUp creates optic data with temps 30.0, 42.0, 54.0 for each optic type
  // (in std::map alphabetical order: 100_GENERIC, 200_GENERIC, 400_GENERIC).
  // Expected PWM values based on tempToPwmMaps:
  //   - OPTIC_TYPE_100_GENERIC: temp=30, PWM=24 (30 >= 5)
  //   - OPTIC_TYPE_200_GENERIC: temp=42, PWM=26 (42 >= 5, < 43)
  //   - OPTIC_TYPE_400_GENERIC: temp=54, PWM=36 (54 >= 5, < 59)
  std::map<std::string, std::pair<int64_t, int64_t>> expectedOpticValues = {
      {"OPTIC_TYPE_100_GENERIC", {30, 24}},
      {"OPTIC_TYPE_200_GENERIC", {42, 26}},
      {"OPTIC_TYPE_400_GENERIC", {54, 36}},
  };

  for (const auto& [opticType, expected] : expectedOpticValues) {
    const auto& [expectedTemp, expectedPwm] = expected;
    EXPECT_EQ(
        fb303::fbData->getCounter(
            fmt::format("{}.optics_read.max.value", opticType)),
        expectedTemp);
    EXPECT_EQ(
        fb303::fbData->getCounter(
            fmt::format("{}.optics_pwm.value", opticType)),
        expectedPwm);
  }

  // Verify aggregate optics PWM counter is max(24, 26, 36) = 36.
  EXPECT_EQ(fb303::fbData->getCounter("agg.optics_pwm.value"), 36);

  // Every configured optic type has a profile.
  for (const auto& [opticType, _] : expectedOpticValues) {
    EXPECT_EQ(
        fb303::fbData->getCounter(
            fmt::format("{}.optics_no_profile", opticType)),
        0);
  }
}

TEST_F(ControlLogicTests, UnprofiledOpticTypeIsReportedExcludedAndBoosts) {
  expectFanAccess();
  addOpticTypeToSensorData(kUnprofiledOpticType, 70.0);

  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  // The temperature is still published so the optic stays visible, and the
  // no-profile counter flags it.
  EXPECT_EQ(
      fb303::fbData->getCounter(
          fmt::format("{}.optics_read.max.value", kUnprofiledOpticType)),
      70);
  EXPECT_EQ(
      fb303::fbData->getCounter(
          fmt::format("{}.optics_no_profile", kUnprofiledOpticType)),
      1);

  // It contributes nothing to the optics aggregate, which stays at the
  // max over the profiled types (24, 26, 36).
  EXPECT_EQ(fb303::fbData->getCounter("agg.optics_pwm.value"), 36);

  // An optic we cannot control must fail toward more cooling, not less.
  const auto fanStatuses = controlLogic_->getFanStatuses();
  int i = 0;
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedBoostModePwms[i++]);
  }
}

TEST_F(
    ControlLogicTests,
    UnprofiledOpticTypeUnderPidAggregationIsReportedAndBoosts) {
  // Same contract as the MAX case above, under PID aggregation: an optic type
  // with no profile is reported and boosts, and must never abort the control
  // loop. PID is the branch where getting it wrong throws rather than
  // degrading, because a profile miss must not reach pidLogics_.
  PidSetting pidSetting;
  pidSetting.kp() = -4;
  pidSetting.ki() = -0.06;
  pidSetting.kd() = 0;
  pidSetting.setPoint() = 67.0;
  pidSetting.posHysteresis() = 0.0;
  pidSetting.negHysteresis() = 3.0;
  for (auto& optic : *fanServiceConfig_.optics()) {
    for (const auto& [opticType, _] : *optic.tempToPwmMaps()) {
      optic.pidSettings()->emplace(opticType, pidSetting);
    }
    optic.tempToPwmMaps()->clear();
    optic.aggregationType() = "OPTIC_AGGREGATION_TYPE_PID";
  }

  // Before constructing ControlLogic: its constructor programs the fans.
  expectFanAccess();
  auto pidControlLogic =
      std::make_shared<ControlLogic>(fanServiceConfig_, mockBsp_);
  addOpticTypeToSensorData(kUnprofiledOpticType, 70.0);

  EXPECT_NO_THROW(pidControlLogic->updateControl(sensorData_));

  EXPECT_EQ(
      fb303::fbData->getCounter(
          fmt::format("{}.optics_no_profile", kUnprofiledOpticType)),
      1);
  // No PWM was computed for it, so no pwm counter should exist.
  EXPECT_FALSE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_pwm.value", kUnprofiledOpticType)));

  // An optic we cannot control must fail toward more cooling, not less.
  const auto fanStatuses = pidControlLogic->getFanStatuses();
  int i = 0;
  EXPECT_EQ(fanStatuses.size(), fanServiceConfig_.fans()->size());
  for (const auto& [fanName, fanStatus] : fanStatuses) {
    EXPECT_EQ(*fanStatus.pwmToProgram(), kExpectedBoostModePwms[i++]);
  }
}

TEST_F(ControlLogicTests, OpticCountersAreClearedWhenOpticTypeDisappears) {
  expectFanAccess();
  addOpticTypeToSensorData(kUnprofiledOpticType, 70.0);

  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_read.max.value", kUnprofiledOpticType)));
  EXPECT_EQ(
      fb303::fbData->getCounter(
          fmt::format("{}.optics_no_profile", kUnprofiledOpticType)),
      1);
  // A profiled type is the only one that ever gets a pwm counter, so it has
  // to be part of this test for the pwm counter's clearing to be covered.
  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_pwm.value", kProfiledOpticType)));

  // Unplug both. The counters must stop reporting rather than latch their last
  // value, otherwise an alert on optics_no_profile fires forever.
  removeOpticTypeFromSensorData(kUnprofiledOpticType);
  removeOpticTypeFromSensorData(kProfiledOpticType);
  controlLogic_->updateControl(sensorData_);

  for (const auto& opticType : {kUnprofiledOpticType, kProfiledOpticType}) {
    EXPECT_FALSE(
        fb303::fbData->hasCounter(
            fmt::format("{}.optics_read.max.value", opticType)));
    EXPECT_FALSE(
        fb303::fbData->hasCounter(
            fmt::format("{}.optics_pwm.value", opticType)));
    EXPECT_FALSE(
        fb303::fbData->hasCounter(
            fmt::format("{}.optics_no_profile", opticType)));
  }
}

TEST_F(ControlLogicTests, OpticCountersSurviveEmptyOpticData) {
  expectFanAccess();

  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_read.max.value", kProfiledOpticType)));
  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_pwm.value", kProfiledOpticType)));

  // An empty optic group means qsfp_service is unreachable or its data has
  // gone stale, not that the optics were unplugged. Fan control keeps running
  // off the cached pwm, so the counters must keep reporting instead of
  // disappearing from monitoring at exactly that moment.
  clearOpticDataForAllGroups();
  controlLogic_->updateControl(sensorData_);

  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_read.max.value", kProfiledOpticType)));
  EXPECT_TRUE(
      fb303::fbData->hasCounter(
          fmt::format("{}.optics_pwm.value", kProfiledOpticType)));
}

namespace {
namespace constants =
    facebook::fboss::platform::fan_service::fan_service_config_constants;
void expectHealthyTick(MockBsp& mockBsp, const FanServiceConfig& config) {
  EXPECT_CALL(mockBsp, checkIfInitialSensorDataRead()).WillOnce(Return(true));
  for (const auto& fan : *config.fans()) {
    EXPECT_CALL(mockBsp, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .Times(2)
        .WillRepeatedly(Return(true));
    EXPECT_CALL(mockBsp, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .WillOnce(Return(true));
    EXPECT_CALL(mockBsp, readSysfs(*fan.rpmSysfsPath()))
        .WillOnce(Return(kDefaultRpm));
    EXPECT_CALL(mockBsp, readSysfs(*fan.presenceSysfsPath()))
        .WillOnce(Return(1 /* fan exists */));
  }
}

std::map<std::string, SensorControl> sensorsByName(const ControlState& state) {
  std::map<std::string, SensorControl> byName;
  for (const auto& sensor : *state.sensors()) {
    byName[*sensor.name()] = sensor;
  }
  return byName;
}
} // namespace

TEST_F(ControlLogicTests, OpticRowsCarryTheQsfpReadTimeNotTheTickTime) {
  // qsfp_service last published an hour ago. The rows must say that, or a
  // reader cannot tell a live optic from one that stopped reporting.
  const uint64_t staleQsfpTime = mockBsp_->getCurrentTime() - 3600;
  for (const auto& optic : *fanServiceConfig_.optics()) {
    auto opticEntry = sensorData_->getOpticEntry(*optic.opticName());
    sensorData_->updateOpticEntry(
        *optic.opticName(), opticEntry->data, staleQsfpTime);
  }

  expectHealthyTick(*mockBsp_, fanServiceConfig_);
  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  const auto state = controlLogic_->getControlState();
  const auto byName = sensorsByName(state);
  int opticRows = 0;
  for (const auto& optic : *fanServiceConfig_.optics()) {
    for (const auto& [opticType, tempToPwm] : *optic.tempToPwmMaps()) {
      const auto name = *optic.opticName() + ":" + opticType;
      ASSERT_TRUE(byName.contains(name)) << name;
      EXPECT_EQ(*byName.at(name).readTime(), staleQsfpTime);
      opticRows++;
    }
  }
  EXPECT_GT(opticRows, 0);
  EXPECT_GT(*state.tickTime(), staleQsfpTime);
}

TEST_F(ControlLogicTests, AnOpticTypeThatDisappearsStopsBeingPublished) {
  expectFanAccess();
  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  const auto& optic = fanServiceConfig_.optics()->front();
  const auto goneType = optic.tempToPwmMaps()->begin()->first;
  const auto goneName = *optic.opticName() + ":" + goneType;
  ASSERT_TRUE(
      sensorsByName(controlLogic_->getControlState()).contains(goneName));

  removeOpticTypeFromSensorData(goneType);
  controlLogic_->updateControl(sensorData_);

  EXPECT_FALSE(
      sensorsByName(controlLogic_->getControlState()).contains(goneName));
}

TEST_F(ControlLogicTests, OpticPidLoopsArePublishedWithTheirSetting) {
  PidSetting pidSetting;
  pidSetting.kp() = -4;
  pidSetting.ki() = -0.06;
  pidSetting.kd() = 0;
  pidSetting.setPoint() = 67.0;
  pidSetting.posHysteresis() = 0.0;
  pidSetting.negHysteresis() = 3.0;
  std::vector<std::string> pidOptics;
  for (auto& optic : *fanServiceConfig_.optics()) {
    for (const auto& [opticType, _] : *optic.tempToPwmMaps()) {
      optic.pidSettings()->emplace(opticType, pidSetting);
      pidOptics.push_back(*optic.opticName() + ":" + opticType);
    }
    optic.tempToPwmMaps()->clear();
    optic.aggregationType() = "OPTIC_AGGREGATION_TYPE_PID";
  }
  ASSERT_FALSE(pidOptics.empty());

  expectFanAccess();
  auto pidControlLogic =
      std::make_shared<ControlLogic>(fanServiceConfig_, mockBsp_);
  pidControlLogic->setTransitionValue();
  pidControlLogic->updateControl(sensorData_);

  const auto byName = sensorsByName(pidControlLogic->getControlState());
  for (const auto& name : pidOptics) {
    ASSERT_TRUE(byName.contains(name)) << name;
    const auto& pid = byName.at(name).pid();
    ASSERT_TRUE(pid.has_value()) << name;
    EXPECT_FLOAT_EQ(*pid->setPoint(), *pidSetting.setPoint());
    EXPECT_FLOAT_EQ(*pid->kp(), *pidSetting.kp());
    EXPECT_FLOAT_EQ(*pid->ki(), *pidSetting.ki());
  }
}

TEST_F(ControlLogicTests, GetControlStateReflectsTheTick) {
  expectHealthyTick(*mockBsp_, fanServiceConfig_);
  EXPECT_TRUE(controlLogic_->getControlState().sensors()->empty());

  controlLogic_->setTransitionValue();
  controlLogic_->updateControl(sensorData_);

  const auto state = controlLogic_->getControlState();
  EXPECT_FALSE(*state.boostMode());
  EXPECT_FALSE(state.pwmHold().has_value());
  EXPECT_EQ(*state.pwmLowerThreshold(), *fanServiceConfig_.pwmLowerThreshold());
  EXPECT_EQ(*state.pwmUpperThreshold(), *fanServiceConfig_.pwmUpperThreshold());
  EXPECT_EQ(
      *state.pwmUpdateIntervalSec(), controlLogic_->getControlFrequency());

  const auto byName = sensorsByName(state);
  const auto& caches = controlLogic_->getSensorCaches();
  for (const auto& sensor : *fanServiceConfig_.sensors()) {
    const auto& name = *sensor.sensorName();
    ASSERT_TRUE(byName.contains(name)) << name;
    EXPECT_EQ(*byName.at(name).calculatedPwm(), caches.at(name).targetPwmCache);
    EXPECT_FLOAT_EQ(*byName.at(name).reading(), caches.at(name).lastReadValue);
    EXPECT_EQ(*byName.at(name).pwmCalcType(), *sensor.pwmCalcType());
    EXPECT_FALSE(
        byName.at(name).pid().has_value()); // table sensors run no loop
  }
  for (const auto& optic : *fanServiceConfig_.optics()) {
    for (const auto& [opticType, tempToPwm] : *optic.tempToPwmMaps()) {
      const auto name = *optic.opticName() + ":" + opticType;
      ASSERT_TRUE(byName.contains(name)) << name;
      EXPECT_FALSE(byName.at(name).pid().has_value());
    }
  }

  const auto fanStatuses = controlLogic_->getFanStatuses();
  ASSERT_EQ(state.zones()->size(), fanServiceConfig_.zones()->size());
  for (const auto& zoneState : *state.zones()) {
    const auto& zone = *std::find_if(
        fanServiceConfig_.zones()->begin(),
        fanServiceConfig_.zones()->end(),
        [&](const Zone& z) { return *z.zoneName() == *zoneState.name(); });
    EXPECT_EQ(*zoneState.aggregationType(), *zone.zoneType());
    const auto& firstFan = *std::find_if(
        fanServiceConfig_.fans()->begin(),
        fanServiceConfig_.fans()->end(),
        [&](const Fan& f) {
          return std::find(
                     zone.fanNames()->begin(),
                     zone.fanNames()->end(),
                     *f.fanName()) != zone.fanNames()->end();
        });
    EXPECT_EQ(
        *zoneState.programmedPwm(),
        *fanStatuses.at(*firstFan.fanName()).pwmToProgram());
    if (*zone.zoneType() == constants::ZONE_TYPE_MAX()) {
      ASSERT_TRUE(zoneState.drivingComponent().has_value());
      EXPECT_EQ(*zoneState.drivingComponent(), zone.sensorNames()->front());
    } else if (*zone.zoneType() == constants::ZONE_TYPE_AVG()) {
      EXPECT_FALSE(zoneState.drivingComponent().has_value());
    }
  }
}

TEST_F(ControlLogicTests, GetControlStateReportsPidState) {
  auto config = fanServiceConfig_;
  config.controlInterval().ensure();
  config.controlInterval()->sensorReadInterval() = 5;
  config.controlInterval()->pwmUpdateInterval() = 5;
  // INLET_SENSOR reads 30.0 in the fixture: positional loop, above its band.
  auto& positional = config.sensors()->at(0);
  positional.pwmCalcType() = constants::SENSOR_PWM_CALC_TYPE_PID();
  positional.pidSetting()->kp() = -4;
  positional.pidSetting()->ki() = -0.06;
  positional.pidSetting()->kd() = 0;
  positional.pidSetting()->setPoint() = 20;
  positional.pidSetting()->posHysteresis() = 2;
  positional.pidSetting()->negHysteresis() = 2;
  // OUTLET_SENSOR reads 40.5: incremental loop, below its band.
  auto& incremental = config.sensors()->at(1);
  incremental.pwmCalcType() = constants::SENSOR_PWM_CALC_TYPE_INCREMENTAL_PID();
  incremental.pidSetting()->kp() = 2;
  incremental.pidSetting()->ki() = 0.6;
  incremental.pidSetting()->kd() = 0;
  incremental.pidSetting()->setPoint() = 60;
  incremental.pidSetting()->posHysteresis() = 2;
  incremental.pidSetting()->negHysteresis() = 2;
  auto controlLogic = std::make_shared<ControlLogic>(config, mockBsp_);
  expectHealthyTick(*mockBsp_, config);

  controlLogic->setTransitionValue();
  controlLogic->updateControl(sensorData_);

  const auto byName = sensorsByName(controlLogic->getControlState());
  const auto& pos = byName.at(*positional.sensorName());
  ASSERT_TRUE(pos.pid().has_value());
  EXPECT_FLOAT_EQ(*pos.pid()->setPoint(), 20);
  EXPECT_FLOAT_EQ(*pos.pid()->error(), 10); // 30 - 20
  EXPECT_FLOAT_EQ(*pos.pid()->kp(), -4);
  EXPECT_TRUE(pos.pid()->integral().has_value());
  EXPECT_TRUE(pos.pid()->derivative().has_value());

  const auto& inc = byName.at(*incremental.sensorName());
  ASSERT_TRUE(inc.pid().has_value());
  EXPECT_FLOAT_EQ(*inc.pid()->error(), -19.5); // 40.5 - 60
  EXPECT_FALSE(inc.pid()->integral().has_value());
  EXPECT_FALSE(inc.pid()->derivative().has_value());

  EXPECT_FALSE(
      byName.at(*config.sensors()->at(2).sensorName()).pid().has_value());
}

TEST_F(ControlLogicTests, SetPidSettingTakesEffectNextTickAndKeepsLoopState) {
  auto config = fanServiceConfig_;
  config.controlInterval().ensure();
  config.controlInterval()->sensorReadInterval() = 5;
  config.controlInterval()->pwmUpdateInterval() = 5;
  auto& sensor = config.sensors()->at(0); // reads 30.0 in the fixture
  sensor.pwmCalcType() = constants::SENSOR_PWM_CALC_TYPE_INCREMENTAL_PID();
  sensor.pidSetting()->kp() = 2;
  sensor.pidSetting()->ki() = 0.6;
  sensor.pidSetting()->kd() = 0;
  sensor.pidSetting()->setPoint() =
      60; // far below the band: the loop keeps pulling down
  sensor.pidSetting()->posHysteresis() = 2;
  sensor.pidSetting()->negHysteresis() = 2;
  auto controlLogic = std::make_shared<ControlLogic>(config, mockBsp_);
  EXPECT_CALL(*mockBsp_, checkIfInitialSensorDataRead())
      .WillRepeatedly(Return(true));
  for (const auto& fan : *config.fans()) {
    EXPECT_CALL(*mockBsp_, setFanPwmSysfs(*fan.pwmSysfsPath(), _))
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, turnOnLedSysfs(*fan.goodLedSysfsPath()))
        .WillRepeatedly(Return(true));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.rpmSysfsPath()))
        .WillRepeatedly(Return(kDefaultRpm));
    EXPECT_CALL(*mockBsp_, readSysfs(*fan.presenceSysfsPath()))
        .WillRepeatedly(Return(1));
  }
  controlLogic->setTransitionValue();
  controlLogic->updateControl(sensorData_);
  const auto beforeState = controlLogic->getControlState();
  const auto before = sensorsByName(beforeState).at(*sensor.sensorName());
  ASSERT_TRUE(before.pid().has_value());
  EXPECT_FLOAT_EQ(*before.pid()->setPoint(), 60);

  PidSettingRequest changed;
  changed.sensorName() = *sensor.sensorName();
  changed.kp() = 4;
  changed.setPoint() =
      25; // 30.0 is now above the band: the loop pushes up instead
  controlLogic->setPidSetting(changed);
  // Nothing changes until the next tick.
  EXPECT_FLOAT_EQ(
      *sensorsByName(controlLogic->getControlState())
           .at(*sensor.sensorName())
           .pid()
           ->setPoint(),
      60);

  controlLogic->updateControl(sensorData_);
  const auto after =
      sensorsByName(controlLogic->getControlState()).at(*sensor.sensorName());
  EXPECT_FLOAT_EQ(*after.pid()->setPoint(), 25);
  EXPECT_FLOAT_EQ(*after.pid()->kp(), 4);
  EXPECT_FLOAT_EQ(*after.pid()->ki(), 0.6); // unset fields keep their value
  EXPECT_FLOAT_EQ(*after.pid()->posHysteresis(), 2);
  EXPECT_FLOAT_EQ(*after.pid()->error(), 5); // 30 - 25
  // Same loop, reading history intact: the delta is ki * (30 - 25) = 3 on top
  // of the fan PWM fed back into the loop, with no kp * (30 - 0) kick from a
  // fresh loop.
  int16_t fedBackPwm = -1;
  for (const auto& zone : *beforeState.zones()) {
    for (const auto& z : *config.zones()) {
      if (*z.zoneName() == *zone.name() &&
          std::find(
              z.sensorNames()->begin(),
              z.sensorNames()->end(),
              *sensor.sensorName()) != z.sensorNames()->end()) {
        fedBackPwm = *zone.programmedPwm();
      }
    }
  }
  ASSERT_NE(fedBackPwm, -1);
  EXPECT_EQ(*after.calculatedPwm(), fedBackPwm + 3);
}

TEST_F(ControlLogicTests, SetPidSettingRejectsUnknownAndTableSensors) {
  PidSettingRequest request;
  request.sensorName() = "NO_SUCH_SENSOR";
  EXPECT_THROW(
      controlLogic_->setPidSetting(request), facebook::fboss::FbossError);
  // Every sample-config sensor is table driven.
  request.sensorName() = *fanServiceConfig_.sensors()->at(0).sensorName();
  EXPECT_THROW(
      controlLogic_->setPidSetting(request), facebook::fboss::FbossError);
}

} // namespace facebook::fboss::platform
