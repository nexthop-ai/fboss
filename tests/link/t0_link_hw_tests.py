# copied from fboss/fboss/oss/hw_sanity_tests/t0_ensemble_link_tests.conf
test_context = {
    "filters": [
        "*EmptyLinkTest*CheckInit*",
        "*LinkTest*trafficRxTx*",
        "*LinkTest*asicLinkFlap*",
        "*LinkTest*getTransceivers*",
        "*LinkTest*iPhyInfoTest*",
        "*LinkSanityTestDataPlaneFlood*warmbootIsHitLess*",
    ],
}


def test_t0_link_hw_tests(link_test_runner):
    assert link_test_runner.run_test(test_context)
