test_context = {
    "filters": [
        "*Trunk*",
        "*Ptp*",
        "*MmuTuning*",
        "*ResourceStats*",
        "*EgressForwardingDiscard*",
        "*InNullRouteDiscard*",
        "*InTrapDiscard*",
    ],
}

def test_t2_agent_hw_tests_rest(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
