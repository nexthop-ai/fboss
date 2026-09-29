import pytest

pytestmark = pytest.mark.topology("fboss-standalone")

test_context = {
    "filters": [
        "*SystemScale*",
    ],
    # SystemScaleChurnMemoryBenchmark takes 3-20 min on Broadcom platforms in
    # passing runs, and the run_test.py default of 1200 s per benchmark kills
    # roughly one run in eight before it finishes.
    "test_run_timeout": 2400,
}


def test_memory_scale_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(test_context)
