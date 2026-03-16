test_context = {
    "filters" : [
        "*Vlan*",
        "*L2ClassID*",
        "*MacLearning*",
        "*MacSwLearning*",
        "*PacketSend*",
        "*PacketFlood*",
        "*Neighbor*",
        "*L3*",
        "*HwRoute*",
        "*PRBS*",
    ],
}

def test_t0_agent_hw_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
