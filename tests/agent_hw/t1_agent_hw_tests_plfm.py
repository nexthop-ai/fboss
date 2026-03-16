test_context = {
    "filters" : [
        "*warm_boot*",
    ],
}

def test_t1_agent_hw_tests_plfm(sai_test_runner):
    assert sai_test_runner.run_test(test_context)
