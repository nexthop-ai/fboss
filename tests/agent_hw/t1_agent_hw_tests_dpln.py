from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*Acl*",
        "*Ecmp*",
        "*LoadBalancer*",
        "*SaiNextHopGroup*",
        "*HwUdfTest*",
    ],
}

def test_t1_agent_hw_tests_dpln(runner):
    assert runner.run_test(test_context)
