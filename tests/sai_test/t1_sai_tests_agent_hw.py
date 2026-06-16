test_context = {
    "filters": [
        "*InPause*",
    ],
}


def test_t1_sai_tests_agent_hw(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
