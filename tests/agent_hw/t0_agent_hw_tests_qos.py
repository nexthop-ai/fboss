from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*Copp*",
        "*RxReason*",
        "*SendPacketToQueue*",
        "*DscpQueueMapping*",
        "*PortBandwidth*",
    ],
}

def test_t0_agent_hw_tests_qos(runner):
    assert runner.run_test(test_context)
