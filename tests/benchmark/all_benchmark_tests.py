def test_all_benchmark_tests(benchmark_test_runner):
    assert benchmark_test_runner.run_test({})
