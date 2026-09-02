from tests.libs.test_runner import LinkTestRunner

# Split per variant so the runner can require the media on both ends of a pair for
# TCVR_L-to-TCVR_L but only one end for ASIC-to-TCVR_S.
_PRBS_FILTERS = [f"*Prbs_TCVR_L*{media}*" for media in LinkTestRunner._MEDIA_INTERFACE_TOKENS] + [
    f"*Prbs_ASIC*TCVR_S*{media}*" for media in LinkTestRunner._MEDIA_INTERFACE_TOKENS
]

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

        *_PRBS_FILTERS,

        "*FabricLinkTest*linkActiveAndLoopStatus*",

        # xPhyInfoTest  # no external phy
    ],
}


def test_t1_link_hw_tests(link_test_runner):
    assert link_test_runner.run_test(test_context)
