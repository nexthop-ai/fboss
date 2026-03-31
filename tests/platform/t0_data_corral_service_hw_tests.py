# Data corral service hardware tests
test_context = {
    "filters": [
        "*DataCorralServiceHwTest*",
    ],
}


def test_t0_data_corral_service_hw_tests(data_corral_service_hw_test_runner):
    assert data_corral_service_hw_test_runner.run_test(test_context)
