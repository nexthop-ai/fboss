test_context = {
    "filters": [
        "*Sflow*",
        "*Mirror*",
    ],
}

def test_t2_agent_hw_tests_sflw_mirr(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
