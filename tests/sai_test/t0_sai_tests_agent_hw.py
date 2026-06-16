test_context = {
    "filters": [
        "*AgentRoute*",
        "*PortAdminState*",
        "*PortProfile*",
    ],
}


def test_t0_sai_tests_agent_hw(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
