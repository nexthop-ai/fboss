from tests.libs.hw_agent.lib_hw_agent_runner import hw_agent_test_runner as runner

test_context = {
    "filters" : [
        "*AlpmStress*",
        "*EcmpTrunk*",
        "*Hash*",
        "*LoadBalancer*",
        "*PacketSendReceiveLag*",
        "*PortStress*",
        "*PtpTc*",
        "*Sflow*",
        "*Trunk*",
        "*ArsFlowlet*",
        "*ArsSpray*",
        "*ProdInvariantsFswStrictPriority*",
        "*Trunk*",
    ],
}

def test_t2_sai_tests_dpln(runner):
    assert runner.run_test(test_context)
