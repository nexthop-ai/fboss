test_context = {
    "filters": [
        "*LinkTest*qsfpColdbootAfterAgentUp*",
        "*LinkEcmpTest*ecmpShrink*",

        "*LinkSanityTestDataPlaneFlood*qsfpWarmbootIsHitLess*",

        "*OpticsTest*verifyTxRxLatches*",
        "*LinkTest*opticsTxDisableEnable*",
        "*LinkTest*opticsTxDisableRandomPorts*",
        "*LinkTest*opticsVdmPerformanceMonitoring*",

        "*LinkTest*verifyIphyFecBerCounters*",
        "*LinkTest*clearIphyInterfaceCounters*",

        "*PtpTests*enablePtpPortDown*",

        "*QsfpFsdbTest*phy*",
        "*QsfpFsdbTest*portState*",
        "*QsfpFsdbTest*tcvr*",

        "*Prbs*FR4_200G*",
        "*Prbs*FR4_400G*",

        "*FabricLinkTest*linkActiveAndLoopStatus*",

        # xPhyInfoTest  # no external phy
    ],
}


def test_t1_link_hw_tests(link_test_runner):
    assert link_test_runner.run_test(test_context)
