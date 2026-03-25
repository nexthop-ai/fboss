test_context = {
    "filters" : [
        "*Trunk*",
        "*Sflow*",
        "*Mirror*",
        "*Ptp*",
        "*MmuTuning*",
        "*ResourceStats*",
    ],
}

def test_t2_agent_hw_tests_dpln(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
