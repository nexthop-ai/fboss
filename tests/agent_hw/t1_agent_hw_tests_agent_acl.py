test_context = {
    "filters": [
        "*AgentAcl*",
        # Exclusion Criteria
        "-*DscpQueueMapping*",
    ],
}

def test_t1_agent_hw_tests_agent_acl(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
