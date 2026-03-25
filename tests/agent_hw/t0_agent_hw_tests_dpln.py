test_context = {
    "filters" : [
        "*Vlan*",
        "*MacLearning*",
        "*MacSwLearning*",
        "*PacketSend*",
        "*PacketFlood*",
        "*Neighbor*",
        "*L3*",
        "*Prbs*",
    ],
}

def test_t0_agent_hw_tests_dpln(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
