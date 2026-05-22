test_context = {
    "filters": [
        "*Acl*",
        "*Qos*",
        "*NetworkAIQos*",
        "*HwUdfTest*",
    ],
}

def test_t1_agent_hw_tests_acl(sai_agent_test_runner):
    assert sai_agent_test_runner.run_test(test_context)
