from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*warm_boot*",
    ],
}

def test_t1_agent_hw_tests_plfm(runner):
    assert runner.run_test(test_context)
