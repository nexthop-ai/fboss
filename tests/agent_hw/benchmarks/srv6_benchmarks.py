# Split out from route_scale so its skips stay isolated: SRv6 is unsupported on
# current platforms, so this bucket skips wholesale.
test_context = {
    "filters": [
        "*Srv6*",
    ],
}


def test_srv6_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
