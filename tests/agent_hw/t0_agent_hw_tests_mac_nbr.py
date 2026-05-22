test_context = {
    "filters": [
        "*MacLearning*",
        "*MacSwLearning*",
        "*Neighbor*",
    ],
}

def test_t0_agent_hw_tests_mac_nbr(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
