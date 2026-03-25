test_context = {
    "filters" : [
        "*Copp*",
        "*RxReason*",
        "*SendPacketToQueue*",
        "*DscpQueueMapping*",
        "*PortBandwidth*",
    ],
}

def test_t0_agent_hw_tests_qos(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
