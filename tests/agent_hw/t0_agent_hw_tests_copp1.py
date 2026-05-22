test_context = {
    "filters": [
        "*AgentCoppTest/1*",
    ],
}

def test_t0_agent_hw_tests_copp1(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
