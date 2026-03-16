test_context = {
    "filters" : [
        "*HwTest_PROFILE*",
        "*FlextPort*",
    ],
}

def test_t0_agent_hw_tests_plfm(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
