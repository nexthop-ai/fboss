test_context = {
    "filters": [
        "*AgentRoute*",
        "*PortAdminState*",
        "*PortProfile*",
    ],
}


def test_t0_agent_hw_tests_sai(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
