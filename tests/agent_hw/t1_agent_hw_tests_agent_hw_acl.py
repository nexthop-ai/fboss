test_context = {
    "filters": [
        "*AgentHwAcl*",
        # Exclusion Criteria
        "-*Neighbor*",
        "*Vlan*",
    ],
}

def test_t1_agent_hw_tests_agent_hw_acl(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
