test_context = {
    "filters" : [
        "*PROFILE*",
    ],
}

def test_t0_sai_tests_plfm(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
