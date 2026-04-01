# Sensor service hardware tests
test_context = {
    "filters": [
        "*SensorServiceHwTest*",
    ],
}


def test_t0_sensor_service_hw_tests(sensor_service_hw_test_runner):
    assert sensor_service_hw_test_runner.run_test(test_context)
