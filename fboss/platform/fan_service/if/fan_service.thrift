include "thrift/annotation/thrift.thrift"
include "fboss/agent/if/fboss.thrift"
include "thrift/annotation/hack.thrift"

@hack.NamePrefix{prefix = "NetengFbossPlatformFanService_"}
@hack.LegacyAlwaysIncludeNamePrefixInProcessor
@hack.LegacyOmitPrefixInNameString
@thrift.AllowLegacyMissingUris
package;

namespace cpp2 facebook.fboss.platform.fan_service
namespace py3 neteng.fboss.platform.fan_service

// Holds latest status of Fans
// `fanFailed`: Whether fan is in failure state. Either it's missing, unaccessible, unable to be programmed.
// `pwmToProgram`: Last pwm value computed to program based on the latest sensors/optics data.
// `rpm`: Last rpm value observed.
// `lastSuccessfulAccessTime`: Last time the fan was successfully accessed.
struct FanStatus {
  1: bool fanFailed;
  2: float pwmToProgram;
  3: i64 lastSuccessfulAccessTime;
  4: optional i32 rpm;
}

struct FanStatusesResponse {
  1: map<string /*fanName*/, FanStatus> fanStatuses;
}

struct PwmHoldRequest {
  1: optional i32 pwm; // Removes hold if unset
}

struct PwmHoldStatus {
  1: optional i32 pwm; // No hold if unset
}

// PID loop state for one sensor; integral/derivative exist only for the
// positional controller (SENSOR_PWM_CALC_TYPE_PID).
struct PidState {
  1: float setPoint;
  2: float error; // reading - setPoint
  3: optional float integral;
  4: optional float derivative;
  5: float kp;
  6: float ki;
  7: float kd;
  8: float posHysteresis;
  9: float negHysteresis;
}

struct SensorControl {
  1: string name; // sensor name, or "<opticName>:<opticType>" for optics
  2: float reading;
  3: i64 readTime;
  4: bool failed;
  5: i16 calculatedPwm; // this component's own PWM request
  6: string pwmCalcType;
  7: optional PidState pid;
}

struct ZoneControl {
  1: string name;
  2: string aggregationType;
  3: i16 aggregatePwm; // before slope limiting and the pwm thresholds
  4: optional string drivingComponent; // MAX/MIN zones: component that set aggregatePwm
  5: i16 programmedPwm; // written to the zone's fans this tick
}

// Snapshot of the last control tick.
struct ControlState {
  1: i64 tickTime;
  2: list<SensorControl> sensors;
  3: list<ZoneControl> zones;
  4: bool boostMode;
  5: optional i32 pwmHold;
  6: i16 pwmLowerThreshold;
  7: i16 pwmUpperThreshold;
  8: i32 pwmUpdateIntervalSec;
}

// Fields left unset keep the sensor's current value.
struct PidSettingRequest {
  1: string sensorName; // a sensors[] entry whose pwmCalcType is a PID type
  2: optional float kp;
  3: optional float ki;
  4: optional float kd;
  5: optional float setPoint;
  6: optional float posHysteresis;
  7: optional float negHysteresis;
}

service FanService {
  FanStatusesResponse getFanStatuses();
  void setPwmHold(1: PwmHoldRequest pwmHoldRequest);
  PwmHoldStatus getPwmHold();
  ControlState getControlState();
  // Replaces one sensor's PID loop settings for the running process, applied at
  // the next control tick. Not persisted: a restart returns to the config file.
  void setPidSetting(1: PidSettingRequest request) throws (1: fboss.FbossBaseError error);
}
