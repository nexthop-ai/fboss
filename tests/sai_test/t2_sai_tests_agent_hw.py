test_context = {
    "filters": [
        "*Alpm*",
        "*ArsFlowlet*",
        "*ArsSpray*",
        "*PacketSendReceiveLag*",
        "*ParityError*",
        "*PortStress*",
        "*SwitchStateReplay*",
        "*Rollback*",
    ],
}


def test_t2_sai_tests_agent_hw(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
