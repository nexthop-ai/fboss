test_context = {
    "filters": [
        "*Empty*",
        "*Vlan*",
        "*NextHopGroup*",
        "*HwRoute*",
        "*PortAdminState*",
    ],
}


def test_t0_sai_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
