# LED service hardware tests
test_context = {
    "filters": [
        "*LedServiceTest*",
    ],
}


def test_t0_led_service_hw_tests(led_service_hw_test_runner):
    assert led_service_hw_test_runner.run_test(test_context)
