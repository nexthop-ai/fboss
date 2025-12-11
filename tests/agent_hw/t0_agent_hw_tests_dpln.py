from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

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

def test_t0_agent_hw_tests_dpln(runner):
    assert runner.run_test(test_context)
