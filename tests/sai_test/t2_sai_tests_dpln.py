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
    ],
}

def test_t2_sai_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
