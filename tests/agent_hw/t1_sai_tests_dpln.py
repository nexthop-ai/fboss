test_context = {
    "filters" : [
        "*AclStat*",
        "*RouteStat*",
        "*AclTable*",
    ],
}

def test_t1_sai_tests_dpln(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
