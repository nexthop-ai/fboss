test_context = {
    "filters" : [
        "*DscpMarking*",
        "*Pfc*",
        "*Qos*",
        "*Aqm*",
        "*QueuePerHost*",
    ],
}

def test_t1_agent_hw_tests_qos(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
