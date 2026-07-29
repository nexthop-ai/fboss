test_context = {
    "filters": [
        "*SystemScale*",
    ],
}


def test_memory_scale_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
