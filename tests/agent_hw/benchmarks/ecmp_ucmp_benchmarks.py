test_context = {
    "filters": [
        "*Ecmp*",
        "*Ucmp*",
        "-*Voq*",
        "*Srv6*",
    ],
}


def test_ecmp_ucmp_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
