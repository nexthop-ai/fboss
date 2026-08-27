// Copyright 2004-present Facebook. All Rights Reserved.

#include "fboss/qsfp_service/module/cmis/CmisModule.h"

namespace facebook {
namespace fboss {

/*
 * Keep modules in low power until AppSel programming completes, so the data
 * path initializes once, on the configured application.
 */
bool CmisModule::programAppSelInLowPowerMode() const {
  return true;
}

/*
 * Always return the input SNR value for OSS (no correction applied).
 */
double CmisModule::applyRxSnrCorrection(
    uint16_t /* rawValue */,
    double snrValue) const {
  return snrValue;
}

/*
 * Always return false for OSS (no vendor-specific retry).
 */
bool CmisModule::shouldRetryCdbFwInfo() const {
  return false;
}

} // namespace fboss
} // namespace facebook
