test_context = {
    "filters": [
        "*AgentEmpty*",
    ],
}

def test_t0_agent_hw_tests_empty(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
