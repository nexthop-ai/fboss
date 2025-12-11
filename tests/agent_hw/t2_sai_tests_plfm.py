from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*ParityError*",
        "*Rollback*",
        "*SplitAgentCallback*",
        "*SwitchStateReplay*",
        "*Rollback*",
        "*QPHRollback*",
    ],
}

def test_t2_sai_tests_plfm(runner):
    assert runner.run_test(test_context)
