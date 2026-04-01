# Firmware utility hardware tests
test_context = {
    "filters": [
        "*FwUtilHwTest*",
    ],
}


def test_t0_fw_util_hw_tests(fw_util_hw_test_runner):
    assert fw_util_hw_test_runner.run_test(test_context)
