# Platform hardware tests - runs all platform_hw_test gtest cases
test_context = {
    "filters": [
        "*PlatformHwTest*",
    ],
}


def test_t0_platform_hw_tests(platform_hw_test_runner):
    assert platform_hw_test_runner.run_test(test_context)
