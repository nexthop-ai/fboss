test_context = {
    "filters": [
        "*Ecmp*",
        "*LoadBalancer*",
    ],
}

def test_t1_agent_hw_tests_ecmp_ldbal(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
