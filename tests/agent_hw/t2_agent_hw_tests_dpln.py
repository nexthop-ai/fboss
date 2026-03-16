test_context = {
    "filters" : [
        "*HashPolarization*",
        "*Trunk*",
        "*Sflow*",
        "*Mirror*",
        "*Ptp*",
        "*HwIngressBufferTest*",
        "*MmuTuning*",
        "*ResourceStats*",
    ],
}

def test_t2_agent_hw_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
