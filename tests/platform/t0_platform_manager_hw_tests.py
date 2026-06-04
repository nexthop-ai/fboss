# Platform manager hardware tests
# NOTE: run_test.py automatically stops platform_manager, sensor_service,
# fan_service, data_corral_service, qsfp_service, and led_service before
# running these tests
test_context = {
    "filters": [
        "*PlatformManagerHwTest*",
    ],
}


def test_t0_platform_manager_hw_tests(platform_manager_hw_test_runner):
    assert platform_manager_hw_test_runner.run_test(test_context)
