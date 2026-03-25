test_context = {
    "filters" : [
        "*AclStat*",
        "*RouteStat*",
        "*AclTable*",
        "*HwInPause*",
    ],
}

def test_t1_sai_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
