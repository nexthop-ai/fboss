test_context = {
    "filters" : [
        "*IngressBuffer*",
    ],
}

def test_t1_agent_hw_tests_plfm(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
