test_context = {
    "filters": [
        "*DscpMarking*",
        "*Pfc*",
        "*Aqm*",
        "*QueuePerHost*",
        "*IngressBuffer*",
    ],
}

def test_t1_agent_hw_tests_rest(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
