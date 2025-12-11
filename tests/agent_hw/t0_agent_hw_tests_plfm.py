from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*HwTest_PROFILE*",
        "*FlextPort*",
    ],
}

def test_t0_agent_hw_tests_plfm(runner):
    assert runner.run_test(test_context)
