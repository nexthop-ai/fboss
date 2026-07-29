# Claimed first so the family-specific buckets below can exclude it: VOQ and
# fabric benchmarks are only linked for Broadcom and are unsupported on most
# platforms, where this bucket skips wholesale.
test_context = {
    "filters": [
        "*Voq*",
        "*Fabric*",
        "*Reachability*",
    ],
}


def test_voq_fabric_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
