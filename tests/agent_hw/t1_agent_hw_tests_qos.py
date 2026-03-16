test_context = {
    "filters" : [
        "*DscpMarking*",
        "*HwInPause*",
        "*Pfc*",
        "*Qos*",
        "*Aqm*",
        "*QueuePerHost*",
    ],
}

def test_t1_agent_hw_tests_qos(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
