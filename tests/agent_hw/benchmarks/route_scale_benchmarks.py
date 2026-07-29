test_context = {
    "filters": [
        "*ScaleRoute*",
        "-*Voq*",
        "*Srv6*",
        "*Fabric*",
    ],
}


def test_route_scale_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
