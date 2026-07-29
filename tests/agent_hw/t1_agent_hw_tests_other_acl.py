test_context = {
    "filters": [
        "*Acl*",
        "*Qos*",
        "*NetworkAIQos*",
        "*HwUdfTest*",
        # Exclusion Criteria
        "-*AgentAcl*",
        "*AgentHwAcl*",
        "*L3*",
        "*Neighbor*",
        "*Copp*",
        "*DscpQueueMapping*",
    ],
}

def test_t1_agent_hw_tests_other_acl(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
