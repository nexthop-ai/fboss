// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include <optional>

#include "fboss/platform/fan_service/if/gen-cpp2/fan_service_config_types.h"

namespace facebook::fboss::platform::fan_service {

// Explaination for PidLogic and IncrementalPidLogic
// https://www.yahboom.net/public/upload/upload-html/1653307952/1.%20PID%20algorithm%20theory.html
class PidLogicBase {
 public:
  explicit PidLogicBase(const PidSetting& pidSetting)
      : pidSetting_(pidSetting) {}
  virtual ~PidLogicBase() = default;
  virtual int16_t calculatePwm(float measurement) = 0;
  float getSetPoint() const {
    return *pidSetting_.setPoint();
  }

  void updateLastPwm(int16_t lastPwm) {
    lastPwm_ = lastPwm;
  }

  int16_t getLastPwm() const {
    return lastPwm_;
  }
  // Gains/band change; loop state (history, integral, lastPwm) carries on.
  virtual void updateSetting(const PidSetting& pidSetting) {
    pidSetting_ = pidSetting;
  }
  const PidSetting& getSetting() const {
    return pidSetting_;
  }
  virtual std::optional<float> integral() const {
    return std::nullopt;
  }
  virtual std::optional<float> derivative() const {
    return std::nullopt;
  }

 protected:
  PidSetting pidSetting_;
  int16_t lastPwm_{0};
};

class PidLogic : public PidLogicBase {
 public:
  explicit PidLogic(const PidSetting& pidSetting, unsigned int dT)
      : PidLogicBase(pidSetting), dT_(dT) {
    if (dT_ == 0) {
      throw std::invalid_argument("dT cannot be less than or equal to 0");
    }
  }
  int16_t calculatePwm(float measurement) override;
  // Keeps ki * integral continuous; a ki of 0 never ran anti-windup, so its
  // integral is meaningless and starts over.
  void updateSetting(const PidSetting& pidSetting) override;
  float getLastError() const {
    return lastError_;
  }
  std::optional<float> integral() const override {
    return integral_;
  }
  std::optional<float> derivative() const override {
    return lastDerivative_;
  }

 private:
  float integral_{0};
  float lastError_{0};
  float lastDerivative_{0};
  const unsigned int dT_;
};

class IncrementalPidLogic : public PidLogicBase {
 public:
  explicit IncrementalPidLogic(const PidSetting& pidSetting)
      : PidLogicBase(pidSetting) {}
  int16_t calculatePwm(float measurement) override;

 private:
  float previousRead1_{0};
  float previousRead2_{0};
};

} // namespace facebook::fboss::platform::fan_service
