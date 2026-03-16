test_context = {
    "filters" : [
        "*ParityError*",
        "*Rollback*",
        "*SplitAgentCallback*",
        "*SwitchStateReplay*",
        "*Rollback*",
        "*QPHRollback*",
    ],
}

def test_t2_sai_tests_plfm(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
