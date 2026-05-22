test_context = {
    "filters": [
        "*Vlan*",
        "*L3*",
        "*Copp*",
        "*PacketSend*",
        "*RxReason*",
        "*PacketFlood*",
        "*SendPacketToQueue*",
        "*DscpQueueMapping*",
        "*PortBandwidth*",
        "*Prbs*",
        "*AgentEmpty*",
        # Exclusion Criteria
        "-*AgentCoppTest/0*",
        "-*AgentCoppTest/1*",
    ],
}

def test_t0_agent_hw_tests_rest(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
