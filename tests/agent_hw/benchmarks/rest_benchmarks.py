"""Every benchmark the sibling buckets in this directory do not claim.

Derived rather than hand-listed so a benchmark added upstream always lands in
some bucket instead of silently going unrun.
"""

import os

from tests.libs.test_runner.filter_utils import catch_all_filters


def _build_test_context():
    return {
        "filters": catch_all_filters(
            __file__, os.path.dirname(os.path.abspath(__file__))
        )
    }


def test_rest_benchmarks(benchmark_test_runner):
    assert benchmark_test_runner.run_test(_build_test_context())
