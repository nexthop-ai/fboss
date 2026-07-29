test_context = {
    "filters": [
        "*InitAndExit*",
        "-*Voq*",
        "*Fabric*",
    ],
}


def test_init_exit_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
