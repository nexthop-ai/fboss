test_context = {
    "filters": [
        "*SlowPath*",
    ],
}


def test_slow_path_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
