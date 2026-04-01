# Fan service hardware tests
test_context = {
    "filters": [
        "*FanServiceHwTest*",
    ],
}


def test_t0_fan_service_hw_tests(fan_service_hw_test_runner):
    assert fan_service_hw_test_runner.run_test(test_context)
