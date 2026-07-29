test_context = {
    "filters": [
        "*StatsCollection*",
        "*ClearInterfacePhyCounters*",
        "-*Voq*",
    ],
}


def test_stats_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
