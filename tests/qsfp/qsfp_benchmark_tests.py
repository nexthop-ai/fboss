def test_qsfp_benchmark_tests(qsfp_benchmark_test_runner):
    assert qsfp_benchmark_test_runner.run_test({})
