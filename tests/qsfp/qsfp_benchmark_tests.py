# Runs every qsfp benchmark; platform gating lives in qsfp_bench config, not
# here. Stated explicitly because BenchmarkTestRunner now passes a filter file,
# and an empty one selects nothing.
test_context = {
    "filters": [
        "*",
    ],
}


def test_qsfp_benchmark_tests(qsfp_benchmark_test_runner):
    assert qsfp_benchmark_test_runner.run_test(test_context)
