test_context = {
    "filters" : [
        "*Acl*",
        "*Ecmp*",
        "*LoadBalancer*",
        "*SaiNextHopGroup*",
        "*HwUdfTest*",
    ],
}

def test_t1_agent_hw_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
