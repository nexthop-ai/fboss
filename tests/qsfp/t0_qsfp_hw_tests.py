# Wildcard filters based on fboss/oss/hw_sanity_tests/t0_qsfp_hw_tests.conf
# Using wildcards because test class names vary by platform
# (e.g., HwTransceiverResetTest vs HwTransceiverResetBmcLiteTest)
test_context = {
    "filters": [
        "*EmptyHwTest*CheckInit*",
        "*i2cStressRead*",
        "*i2cStressWrite*",
        "*verifyResetControl*",
        "*resetTranscieverAndDetectPresence*",
        "*CheckPortsProgrammed*",
        "*cmisPageChange*",
    ],
}


def test_t0_qsfp_hw_tests(qsfp_test_runner):
    assert qsfp_test_runner.run_test(test_context)
